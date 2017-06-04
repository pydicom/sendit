# Sendit

**under development**

This is a dummy server for testing sending and receiving of data from an endpoint. The main job of the server will be to "sniff" for receiving a complete dicom series folder in a mapped data folder, and then to do the following:


 - Add series as objects to the database. 
   - A single Dicom image is represented as an "Image"
   - A "Series" is a set of dicom images
   - A "Study" is a collection of series


Although we have groupings on the level of study, images will be generally moved around and processed on the level of Series.


## Configuration
The configuration for the application consists of the files in the [sendit/settings](sendit/settings) folder. The files that need attention are `secrets.py` and [config.py](sendit/settings/config.py).  First make your secrets.py like this:

```
cp sendit/settings/bogus_secrets.py sendit/settings/secrets.py
vim sendit/settings/secrets.py
```

Once you have your `secrets.py`, it needs the following added:

 - `SECRET_KEY`: Django will not run without one! You can generate one [here](http://www.miniwebtool.com/django-secret-key-generator/)
 - `DEBUG`: Make sure to set this to `False` for production.


For [config.py](sendit/settings/config.py) you should configure the following:

```
# If True, we will have the images first go to a task to retrieve fields to deidentify
DEIDENTIFY_RESTFUL=True
```

If this variable is False, we skip this task, and images are instead sent to the next task (or tasks) to send them to different storage. If True, the images are first put in the queue to be de-identified, and then upon receival of the identifiers, then they are put into the same queues to be sent to storage. These functions can be modified to use different endpoints, or do different replacements in the data:

 - The function `get_identifiers` under [images/tasks.py](sendit/apps/images/tasks.py) should take in a series ID, and use that series to look up images, and send a RESTful call to some API point to return fields to replace in the data. The JSON response should be saved to an `SeriesIdentifiers` object along with a pointer to the Series.
 - The function `replace_identifers` also under [images/tasks.py](sendit/apps/images/tasks.py) should then load this object, do whatever work is necessary for the data, and then put the data in the queue for storage.

You might want to tweak both of the above functions depending on your call endpoint, the response format (should be json as it goes into a jsonfield), and then how it is used to deidentify the data.


```
# We can turn on/off send to Orthanc. If turned off, the images would just be processed
SEND_TO_ORTHANC=True

# The ipaddress of the Orthanc server to send the finished dicoms (cloud PACS)
ORTHANC_IPADDRESS="127.0.0.1"

# The port of the same machine (by default they map it to 4747
ORTHAC_PORT=4747
```

Since the Orthanc is a server itself, if we are ever in need of a way to quickly deploy and bring down these intances as needed, we could do that too, and the application would retrieve the ipaddress programatically.

And I would (like) to eventually add the following, meaning that we also send datasets to Google Cloud Storage and Datastore, ideally in compressed nifti instead of dicom, and with some subset of fields. These functions are by default turned off.

```
# Should we send to Google at all?
SEND_TO_GOOGLE=False

# Google Cloud Storage and Datastore
GOOGLE_CLOUD_STORAGE='som-pacs'
```

Importantly, for the above, there must be a `GOOGLE_APPLICATION_CREDENTIALS` filepath exported in the environment, or it should be run on a Google Cloud Instance (unlikely)

## Basic Pipeline
This application lives in a docker-compose application running on `STRIDE-HL71`.


### 1. Data Input
This initial setup is stupid in that it's going to be checking an input folder at some frequency to find new images. `STRIDE-HL71` will receive DICOM from somewhere. It should use an atomic download strategy, but with folders, into the application data input folder. This will mean that when it starts, the folder might look like:
 
 
```bash
/data
     ST-000001.tmp2343
         image1.dcm 
         image2.dcm 
         image3.dcm 

```
Only when all of the dicom files are finished copying will the driving function rename it to be like this:


```bash
/data
     ST-000001
         image1.dcm 
         image2.dcm 
         image3.dcm 

```

### 2. Database Models
The Dockerized application will check the folder at some frequency (once a minute perhaps) and look for folders that are not in the process of being populated. When a folder is found:

 - A new object in the database is created to represent the "Series"
 - Each "Image" is represented by an equivalent object
 - Each "Image" is linked to its "Series", and if relevant, the "Series" is linked to a "Study."
 - Currently, all uids for each must be unique.


### 3. Retrive Identifiers
After these objects are created, we will generate a single call to a Restful service to get back a response that will have fields that need to be substituted in the data. For Stanford, we will use the DASHER API to get identifiers for the study. The call will be made, the response received, and the response itself saved to the database as a "SeriesIdentifiers" object. This object links to the Series it is intended for. The Series id will be put into a job queue for the final processing. This step will not be performed if 


### 3. Replacement of identifiers
The job queue will process datasets when the server has available resources. There will be likely 5 workers for a single application deployment. The worker will do the following:

 - receive a job from the queue with a series id
 - use the series ID to look up the identifiers, and all dicom images
 - for each image, prepare a new dataset that has been de-identified (this will happen in a temporary folder)
 - send the dataset to the cloud Orthanc, and (maybe also?) Datastore and Storage

Upon completion, we will want some level of cleanup of both the database, and the corresponding files. This application is not intended as some kind of archive for data, but a node that filters and passes along.


# Status States
In order to track status of images, we should have different status states. I've so far created a set for images, which also give information about the status of the series they belong to:

```
IMAGE_STATUS = (('NEW', 'The image was just added to the application.'),
               ('PROCESSING', 'The image is currently being processed, and has not been sent.'),
               ('DONEPROCESSING','The image is done processing, but has not been sent.'),
               ('SENT','The image has been sent, and verified received.'),
               ('DONE','The image has been received, and is ready for cleanup.'))
```

These can be tweaked as needed, and likely I will do this as I develop the application. I will want to add more / make things simpler. I'm not entirely sure where I want these to come in, but they will.


# Questions

1. Given that a study is a set of studies, and a study is a collection of images, what level of uniqueness is maintained? For example, can we assume that all study IDs are unique, but could we see duplicate series IDs across different studies? Image ids? I am currently assuming uniqueness of all different model types, however I can put different assertions to do checks for uniqueness in the database.

2. What fields in the DICOM should be:
  - replaced
  - completely stripped

3. And of those fields, which ones would be ok to put in Google Cloud as metadata for researchers to search?
