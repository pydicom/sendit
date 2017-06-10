# De-id Request
De-identification happens by way of a series of celery tasks defined in [main/tasks.py](../sendit/apps/main/tasks.py) that are triggered by the first task that adds a complete set of dicom files (beloning to a dataset with one accession number) to the database. The tasks include the following:

 - The first task `get_identifiers` under [main/tasks.py](sendit/apps/main/tasks.py) takes in a batch ID, and uses that batch to look up images, and send a RESTful call to some API point to return fields to replace in the data. The JSON response should be saved to an `BatchIdentifiers` object along with a pointer to the `Batch`.
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

While it is assumed that one folder of files, corresponding to one accession number, will truly have that be the case, given that the headers present different information (eg, different series/study) we will post a call to the API for each separate Entity represented in the dataset.


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
We will be removing all PHI from the datasets before moving into the cloud, as specified per HIPAA. This means we will remove the following HIPAA identifiers:

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


To be explicitly clear, here are a set of tables to describe **1** the dicom identifier, **2** if relevent, how it is mapped to a field for the DASHER API, **3**, if the data is removed (meaning left as an empty string) before going into the cloud, meaning that it is considered in the HIPAA list above. Not all dicoms have all of these fields, and if the field is not found, no action is taken. This is a broad overview - to get exact actions you should look at the [config.json](https://github.com/vsoch/som/blob/master/som/api/identifiers/dicom/config.json).

### PHI Identifiers
For each of the below, a field under `DASHER` is assumed to be given with an Entity, one of which makes up a list of identifiers, for a `POST`.  Removed does not mean that the field is deleted, but that it is made empty. If replacement is defined, the field from the `DASHER` response is subbed instead of a ''. For most of the below, we give the PHI data as a `custom_field` (to be stored with `DASHER`) and put an empty string in its spot for the data uploaded to Storage.


| Dicom Header Field     | DASHER        |  Removed?   | Replacement            |
| -----------------------|:-------------:| ------------:| ----------------------:
| AccessionNumber        |`custom_fields`| Yes          | ``                    |
| ContentDate            |`custom_fields`| Yes          | ``                    |
| ImageComments          |`custom_fields`| Yes          | ``                    |
| InstanceCreationDate   |`custom_fields`| Yes          | `jittered_timestamp`  |
| InstanceCreationTime   |`custom_fields`| Yes          | ``                    |
| InstanceCreatorUID     |`custom_fields`| Yes          | ``                    |
| MedicalRecordLocator   |`custom_fields`| Yes          | ``                    |
| OtherPatientIDs        |`custom_fields`| Yes          | ``                    |
| OtherPatientNames      |`custom_fields`| Yes          | ``                    |
| OtherPatientIDsSequence|`custom_fields`| Yes          | ``                    |
| PatientAddress         |`custom_fields`| Yes          | ``                    |
| PatientBirthDate       |`custom_fields`| Yes          | ``                    |
| PatientBirthName       |`custom_fields`| Yes          | ``                    |
| PatientID              | `id` (Entity) | Yes          | `suid`                |
| PatientMotherBirthName |`custom_fields`| Yes          | ``                    |
| PatientName            |`custom_fields`| Yes          | ``                    |
| PatientTelephoneNumbers|`custom_fields`| Yes          | ``                    |
| ReferringPhysicianName |`custom_fields`| Yes          | ``                    |
| SeriesDate             |`custom_fields`| Yes          | ``                    |
| SeriesInstanceUID      |`custom_fields`| Yes          | ``                    |
| SeriesNumber           |`custom_fields`| Yes          | ``                    |
| SOPClassUID            |`custom_fields`| Yes          | ``                    |
| SOPInstanceUID         |`custom_fields`| Yes          | ``                    |
| SpecimenAccessionNumber|`custom_fields`| Yes          | ``                    |
| StudyDate              |`custom_fields`| Yes          | ``                    |
| StudyID                |`custom_fields`| Yes          | ``                    |
| StudyInstanceUID       |`custom_fields`| Yes          | ``                    |
| StudyTime              |`custom_fields`| Yes          | ``                    |


The following fields are not considered PHI. For example, the InstanceNumber is not enough to uniquely identify an image - it could be the number '1', and this information is essential for researchers to have to reconstruct sequences. Thus, we don't need to remove / replace it, and we don't need to provide it in `custom_fields` for `DASHER`. We will, however, send it as metadata about the images to be searchable in Google Datastore.


| Dicom Header Field                  |
| ------------------------------------|
| BitsAllocated                       |
| BitsStored                          |
| Columns                             |
| ConversionType                      |
| DataSetTrailingPadding              |
| DateOfSecondaryCapture              |
| HighBit                             |      
| InstanceNumber                      |
| Manufacturer                        |  
| Modality                            |      
| NumberOfFrames                      |
| PatientOrientation                  |
| PatientSex                          |      
| PhotometricInterpretation           |
| PixelData                           |      
| PixelRepresentation                 |
| Rows                                |    
| SamplesPerPixel                     |  
| SecondaryCaptureDeviceManufacturer  | 
| TimezoneOffsetFromUTC               |      



# De-id Response
The response might look like the following:

```

{
  "results": [
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
  ]
}
```
