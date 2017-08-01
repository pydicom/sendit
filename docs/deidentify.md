# De-id Request
De-identification happens by way of a series of celery tasks defined in [main/tasks.py](../sendit/apps/main/tasks.py) that are triggered by the first task that adds a complete set of dicom files (beloning to a dataset with one accession number) to the database. The tasks include the following:

## Get Identifiers
The first task `get_identifiers` under [main/tasks.py](sendit/apps/main/tasks.py) takes in a batch ID, and uses that batch to look up images, and send a RESTful call to some API point to return fields to replace in the data. A few notes:

 - we use the defaults for entity id and item id header fields (`PatientID` and `SOPInstanceUID`, respectively) and these are defined in the deid `dicom/config.json` file. If you want to change this in the sendit application, the `get_identifiers` (imported as `get_ids`) can take an optional `entity_id="CustomHeaderID"` and `item_id="CustomItemID"` fields.
 - This function only skips over returning pixel data. This means that all header fields with value not None or blank are returned. (Items in sequences are unwrapped ??) Private values are not returned.

The result of a call to `get_identifiers` is a dictionary data structure, with keys as entity ids, and items as another dictionary of key value pairs (header fields and values) for the item. This is nice for organization, but isn't what DASHER is expecting, and isn't the minimum set. Thus, we then use the function `prepare_request_identifiers` in `from som.api.identifiers.dicom`, which extracts the minimal fields needed from the `settings` module in the same folder. We use the defaults of the function with `entity_custom_fields` to true (meaning we send custom entity fields to DASHER and `item_custom_fields` to false (meaning we don't send item custom fields). An example extracted identifier might look like this:

```
{
   "items":[
      {
         "id":"x.x.x.x.x.x",
         "id_source":"SOPInstanceUID",
         "custom_fields":[

         ],
         "id_timestamp":"2000-01-11T00:00:00Z"
      }, ...

   ],
   "id":"1234567",
   "id_source":"PatientID",
   "custom_fields":[
      {
         "value":"MICKEY^MOUSE^M",
         "key":"PatientName"
      },
      {
         "value":"MICKEY^MOUSE^M",
         "key":"OtherPatientNames"
      },
      {
         "value":"MMMMMM",
         "key":"AccessionNumber"
      },
      {
         "value":"19860512",
         "key":"PatientBirthDate"
      },
      {
         "value":"Lucas^George^W MD",
         "key":"ReferringPhysicianName"
      },
      {
         "value":"11587441",
         "key":"PatientID"
      },
   ],
   "id_timestamp":"2000-01-11T00:00:00Z"
}
```

These fields are fields that absolutely must be stored within DASHER, and thus are extracted into a formatted response for the DASHER API. 

We originally were sending all of this data to the som DASHER endpoint, primarily with an entity id and timestamp, and then a huge list of `custom_fields` for each item and entity. This was a very slow process, and for purposes of searching, it puts a huge burden on DASHER for doing tasks outside of simple identity management. We have decided to try a different strategy. We send the minimum amount of data to DASHER to get back date jitters and item ids, and then the rest of the data gets put (de-identified) into Google Datastore.



The JSON response should be saved to an `BatchIdentifiers` object along with a pointer to the `Batch`.
 - The second task `replace_identifers` also under [main/tasks.py](sendit/apps/main/tasks.py) then loads this object, does whatever work is necessary for the data, and then puts the data in the queue for storage.

The entire process of starting with an image, generating a request with some specific set of variables and actions to take, and then after the response is received, using it to deidentify the data, lives outside of this application with the [stanford open modules](https://github.com/vsoch/som/tree/master/som/api/identifiers/dicom) for python with the identifiers api client. SOM is a set of open source python modules that (yes, it is purposefully done so that som also implies "School of Medicine" `:L)`) serve the client, and plugins for working with different data types. If you are interested in how this process is done, we recommend reading the [README](https://github.com/vsoch/som/blob/master/som/api/identifiers/dicom/README.md).


## Customizing De-identification
If you have a different use case, you have several options for customizing this step.

1. you can specify a different `config.json` to the get_identifiers function, in the case that you want a different set of rules applied to your de-identification.
2. you can implement a new module (for example, for a different data type) by submitting a PR to the identifiers repository.
3. If you don't use DASHER, or do something entirely different, you have complete control to not use these som provided functions at all, in which case you will want to tweak the functions in [tasks.py](../sendit/apps/main/tasks.py).

For the purposes of documentation, we will review what the de-identification provided here looks like:

## 1. Datastructure Generated
The post to DASHER will like something like the following:

```javascript
{  
   "identifiers":[  
      {  
         "id":"14953772",
         "id_source":"PatientID",
         "id_timestamp":"1961-07-27T00:00:00Z",
         "custom_fields":[  
            {  
               "key":"firstName",
               "value":"MICKEY"
            },
            {  
               "key":"lastName",
               "value":"MOUSE"
            }
         ],
         "items":[  
            {  
               "id":"MCH",
               "id_source":"Lab Result",
               "id_timestamp":"2010-02-04T11:50:00Z",
               "custom_fields":[  
                  {  
                     "key":"ordValue",
                     "value":"33.1"
                  }
               ]
            }
         ],
      }
   ]
}
```

A list of identifiers is given, and we can think of each thing in the list being an Entity, or corresponding to one Patient/Session. Each in this list has a set of id_* fields, and a list of items associated. This matches to our dicom import model, as the identifiers will be associated with one PatientID (and likely one AccessionNumber), and the items the corresponding dicom files for the series.

**Important** A dicom file that doesn't have an Entity (`PatientID`) OR `SOPInstanceUID` (Item id) will be skipped, as these fields are required.

While the API has support to handle a list of identifiers (meaning more than patient) we are taking a conservative approach that each folder is associated with one patient, and a different patient ID is likely an image that should not be included. 


### Identifiers
If you look in the [fields parsed](https://github.com/vsoch/som/blob/master/som/api/identifiers/dicom/config.json) in the conig, or even more horrifying, the [several thousand](https://gist.github.com/vsoch/77211a068f45f7255b0d97cf005db572) active DICOM header fields, rest assured that most images will not have most of these. You will notice for our default, `id` will correspond to the `PatientID`. The `id_source`, then, is `PatientID`.  The `id_timestamp`, since we are talking about a person, corresponds to the individual's birth date, and we use the date to generate a timestamp ([example here](https://gist.github.com/vsoch/23d6b313bd231cad855877dc544c98ed)). We mostly care about the fields that need to be saved (`custom_fields`) but then blanked or coded in the data that gets sent to storage. 

```
        "id": 12345678,
        "id_source": "PatientID",
        "id_timestamp": {},
        "custom_fields": [
          {
            "key": "OtherPatientIDs","value": "FIRST^LAST"
          },
          {
            "key": "PatientAddress", "value": "222 MICHEY LANE"
          },
          {
            "key": "PatientName","value": "Mickey^Mouse"
          },
          {
            "key": "PatientTelephoneNumbers","value": "111-111-1111"
          }

```

## Items
A list of items is associated with each Entity (the example above). The id for the item will correspond to the `SOPInstanceUID`, and thus the `id_source` is `SOPInstanceUID`. The timestamp must be derived from `InstanceCreationDate` and `InstanceCreationTime` using the same function linked above.

```
        "items": [
          {
            "id": "A654321",
            "id_source": "GE PACS",
            "id_timestamp": {},
            "custom_fields": [
              {
                "key": "studySiteID",
                "value": 78329
              }
            ]
          }
```

## 2. Mapping of Identifiers
We will be removing all PHI from the datasets before moving into the cloud, and coding the dataset by replacing the entity and item identifiers with an alias. This means we will remove the following identifiers:

- Name
- Geographic information smaller than state
- Dates more precise than year, and all ages greater than or equal to 90 years of age
- Telephone numbers
- Fax numbers
- Email addresses
- Social security numbers
- Medical record numbers
- Account numbers
- Certificate or license number
- Vehicle identifiers and serial numbers including license plate
- Device identifiers and serial numbers
- URLs
- IP address numbers
- Biometric identifiers
- Full face photographic images and comparable images
- Health plan beneficiary numbers
- Any other unique identifying number, characteristic, or code


To be explicitly clear, we model **1** the dicom identifiers, **2** if relevent, how it is mapped to a field for the DASHER API, and **3**, if the data is removed/blanked/coded before going into the cloud. Not all dicoms have all of these fields, and if the field is not found, then we logically can't send any data to the DASHER endpoint. If there are fields in the data not represented in our list, we take a conservative approach and blank them by default. This is a broad overview - to get exact actions you should look at the [config.json](https://github.com/vsoch/som/blob/master/som/api/identifiers/dicom/config.json).


# De-id Response
The response from the API itself might look like the following:

```

{
  "results": [
      {
        "id": 12345678,
        "id_source": "PatientID",
        "suid": "103e",
        "jittered_timestamp": {},
        "custom_fields": [
          {
            "key": "studySiteID",
            "value": 78329
          }
        ],
        "items": [
          {
            "id": "A654321",
            "id_source": "GE PACS",
            "suid": "103e",
            "jittered_timestamp": {},
            "custom_fields": [
              {
                "key": "studySiteID",
                "value": 78329
              }
            ]
          }
        ]
      }
    ]
}
```

However the client that we use returns the list under `results`, so it looks like this:

```

[
    {
      "id": 12345678,
      "id_source": "PatientID",
      "suid": "103e",
      "jittered_timestamp": {},
      "custom_fields": [
        {
          "key": "studySiteID",
          "value": 78329
        }
      ],
      "items": [
        {
          "id": "A654321",
          "id_source": "GE PACS",
          "suid": "103e",
          "jittered_timestamp": {},
          "custom_fields": [
            {
              "key": "studySiteID",
              "value": 78329
            }
          ]
        }
      ]
    }
]
```

We save this response to the database with an object associated with the batch, and hand off the task of replacing the identifiers in the data to another worker:


```
result = cli.deidentify(ids=ids,study=study)     # should return a list
batch_ids = BatchIdentifiers.objects.create(batch=batch,
                                            response=result)
batch_ids.save()        
replace_identifiers.apply_async(kwargs={"bid":bid})
```

 so another worker can then use it to replace identifiers (in the actual data) with the function `replace_identifiers`, which is provided in the [dicom module](https://github.com/vsoch/som/tree/master/som/api/identifiers/dicom) of the API client. You should read that README if you want more detail on how this is done.


## Replacing Identifiers in Data
To quickly review, we now have generated data structures to describe entities in dicom files, handed those data structures to an API client, and received a response. The next worker (fired with the last line of the code above) would now find the batch, look up the associated files, and read in the response from the API.  Note that while the API has support to return a response with a list of entity, since we do a check to make sure a batch is specific to one patient, we expect to only get one response. After this, the application needs to handle the response to de-identify the images, which would be another call to a function provided by the `identifiers.dicom` module. The call would look like this:

```
from som.api.identifiers.dicom import replace_identifiers

updated_files = replace_identifiers(dicom_files=dicom_files,
                                    response=batch_ids.response)        
```

By default, the function overwrites the current files (since they are deleted later). But if you want to change this default behavior, you can ask it to write them instead to a temporary directory:

```
updated_files = replace_identifiers(dicom_files=dicom_files,
                                    response=batch_ids.response)        
                                    overwrite=False)
```

Note that these functions also add in a field to indicate the data has been de-identified. At this point, we have finished the de-identification process (for header data, pixel anonymization is a separate thing still need to be developed) and can move on to [storage.md](storage.md)
