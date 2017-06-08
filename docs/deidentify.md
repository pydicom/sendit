# De-id Request

Deidentification is a celery task defined in [main/tasks.py](../sendit/apps/main/tasks.py) that is triggered by the first task that adds a complete set of dicom files (beloning to a dataset with one accession number) to the database. In this task, we do the following:

## 1. Datastructure Generated
The post to DASHER will like something like the following:

```javascript
{
  "identifiers": [
    [
      {
        "id": 12345678,
        "id_source": "Stanford MRN",
        "id_timestamp": {},
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
            "id_timestamp": {},
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

A list of identifiers is given, and we can think of each thing in the list being an Entity, or corresponding to one Patient/Session. Each in this list has a set of id_* fields, and a list of items associated. This matches to our dicom import model, as the identifiers will be associated with one Accession Number, and the items the corresponding dicom files for the series.

**Important** A dicom file that doesn't have an Entity (`AccessionNumber`) OR `InstanceNumber` Item id will be skipped, as these fields are required.

While it is assumed that one folder of files, corresponding to one accession number, will truly have that be the case, given that the headers present different information (eg, different series/study) we will post a call to the API for each separate Entity represented in the dataset.

### Identifiers
We can only get so much information about an individual from a dicom image, so most of these will be default, or empty. `id`: will correspond to the `PatientID`. The `id_source`, since it is not provided in the data, will always (for now) default to `Stanford MRN`. The `id_timestamp` will be blank, because it's not clear to me how we could derive when the id was generated. Fields that are specific to the patient will be put into `custom_fields` for the patient, so it might look something like the following:

```
        "id": 12345678,
        "id_source": "Stanford MRN",
        "id_timestamp": {},
        "custom_fields": [
          {
            "key": "OtherPatientIDs","value": "value"
          },
          {
            "key": "OtherPatientNames","value": "value"
          },
          {
            "key": "OtherPatientIDsSequence","value": "value"
          },
          {
            "key": "PatientAddress", "value": "value"
          },
          {
            "key": "PatientBirthDate","value": "value"
          },
          {
            "key": "PatientBirthName","value": "value"
          },
          {
            "key": "PatientMotherBirthName","value": "value"
          },
          {
            "key": "PatientName","value": "value"
          },
          {
            "key": "PatientTelephoneNumbers","value": "value"
          }

```

## Items
A list of items is associated with each Entity (the example above). The id for the item will correspond to the InstanceNumber, and the `id_source` will correspond to the `InstanceCreatorUID`. The timestamp must be derived from `InstanceCreationDate` and `InstanceCreationTime`.

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


To be explicitly clear, here are a set of tables to describe **1** the dicom identifier, **2** if relevent, how it is mapped to a field for the DASHER API, **3**, if the data is removed (meaning left as an empty string) before going into the cloud, meaning that it is considered in the HIPAA list above. Not all dicoms have all of these fields, and if the field is not found, no action is taken.

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
        "id_source": "Stanford MRN",
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

**MORE TO COME** not done yet :)
