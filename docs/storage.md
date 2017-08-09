# Storage
When we get here, we have de-identified our data, and the user can optionally choose to send it off to cloud storage. As a reminder, this is determined in the settings, under [settings.config.py](../sendit/settings.config.py):

We can first choose to send the images to an OrthanCP instance. If we turn this off, we won't, and the images will just stop after de-identification.

```
# We can turn on/off send to Orthanc. If turned off, the images would just be processed
SEND_TO_ORTHANC=True

# The ipaddress of the Orthanc server to send the finished dicoms (cloud PACS)
ORTHANC_IPADDRESS="127.0.0.1"

# The port of the same machine (by default they map it to 4747
ORTHAC_PORT=4747
```

We can also send to Google Cloud, which will allow for easier development of tools around the datasets to query, search, view, etc. These settings are in the same file:

```
# Should we send to Google at all?
SEND_TO_GOOGLE=False

# Google Cloud Storage and Datastore
GOOGLE_CLOUD_STORAGE='som-pacs'
```

Importantly, for the above, there must be `GOOGLE_APPLICATION_CREDENTIALS` filepath, a `GOOGLE_PROJECT_NAME`, and a `GOOGLE_STORAGE_COLLECTION` variables exported in the environment, or it should be run on a Google Cloud Instance (unlikely).

## Upload Process
By the time we get here, we've de-identified the images, and prepared an equivalent corresponding lookup (with old image identifier) that also has the same de-identified metadata. The difference is that the lookup has additional information from nested sequences that are easy to extract. We now proceed to use the som tools google storage API client to upload a set of images associated with an entity and metadata to Google Storage (images) and Google Datastore (metadata).

```
from som.api.google.storage import Client

# Retrieve only images that aren't in PHI folder
images = batch.get_finished()
items = prepare_items_metadata(batch)
```

The function to `get_finished` retrieves images for the batch that weren't flagged for having possible PHI in the pixels, meaning they are in the entity's PHI folder. The `items` dictionary corresponds to the `batch_ids.cleaned` dictionary, but the original image names with identifying `SOPInstanceUID` have been replaced with the image name (eg, `IR661f33_5_224.dcm`). This is the key that the Client will use to look up metadata for a file, and so it is the right index to use. Next, our client is instantiated based on the storage bucket and project name:

```
client = Client(bucket_name=GOOGLE_CLOUD_STORAGE,
               project_name=GOOGLE_CLOUD_PROJECT)
```

The `GOOGLE_APPLICATION_CREDENTIALS` are essential for this to work. If you get permissions errors, you have an issue either with finding this file, or the file (the IAM permissions) in Google Cloud not having Read/Write/Admin access to the resource.

We then create a collection. Given that it already exists, it is just retrieved:
```
collection = client.create_collection(uid=GOOGLE_STORAGE_COLLECTION)
<Key('Collection', 'IRB41449'), project=som-irlearning>
```

This collection is called an "entity" in Datastore, and each entity has a unique key (you can think of like a file path) for which any other entities that share some of that path are considered children. We next prepare our entity (one study for a particular patient id) with some basic metadata:

```
metadata = prepare_entity_metadata(cleaned_ids=batch_ids.cleaned,
                                   image_count=len(images))

```
{'IR661f32': 
    {
     'PatientSex': 'M', 'id': 'IR661f32', 
     'UPLOAD_AGENT': 'STARR:SENDITClient', 
     'IMAGE_COUNT': 2, 'PatientAge': '056Y'
    } 
}

```
The general idea here is to provide very rough, high level searchable fields that a researcher would be interested in, such as the age and gender, and the upload agent. We could add additional metadata here.

Finally, we iterate through the entity (studies) and images associated, and upload simeotaneously to storage and datastore:


```
client.upload_dataset(images=entity_images,
                      collection=collection,
                      uid=metadata['id'],
                      images_metadata=items,
                      entity_metadata=metadata,
                      permission="projectPrivate")
```
Basically, the images are first uploaded to Storage, and complete metadata about their location , etc, returned. This additional metadata, along with the item metadata in `items` is then uploaded to Datastore. This means that we have a nice strategy for searching very detailed fields (DataStore) to get direct links to items (Storage).

