# Sendit

This is a dummy server for testing sending and receiving of data from an endpoint. The main job of the server will be to "sniff" for receiving a complete dicom series folder in a mapped data folder, and then to do the following:


   - Add query with images as objects to the database. 
   - A folder, the result of a query, is represented as a "Batch"
   - A single Dicom image is represented as an "Image"

Images will be moved around and processed on the level of a Batch, which is typically associated with a single accession number, series, and study, however there might be exceptions to this case. For high level overview, continue reading. For module and modality specific docs, see our [docs](docs) folder. If anything is missing documentation please [open an issue](https://www.github.com/pydicom/sendit)


## Download
Before you start, you should make sure that you have Docker and docker-compose installed, and a complete script for setting up the dependencies for any instance [is provided](scripts/setup_instance.sh). You should then clone the repo, and we recommend a location like `/opt`.

```
cd /opt
git clone https://www.github.com/pydicom/sendit
cd sendit
```

This will mean your application base is located at `/opt/sendit` and we recommend that your data folder (where your system process will add files) be maintained at `/opt/sendit/data`. You don't have to do this, but if you don't, you need to change the folder in the [docker-compose.yml](docker-compose.yml) to where you want it to be. For example, right now we map `data` in the application's directory to `/data` in the container, and it looks like this:

```
uwsgi:
  restart: always
  image: vanessa/sendit
  volumes:
    - ./data:/data
```

to change that to `/tmp/dcm` you would change that line to:

```
uwsgi:
  restart: always
  image: vanessa/sendit
  volumes:
    - /tmp/dcm:/data
```

Instructions for starting and interacting with the instance will follow Configuration, or the editing of local files, which must be done first.


## Configuration
The configuration for the application consists of the files in the [sendit/settings](sendit/settings) folder. The files that need attention are `secrets.py` and [config.py](sendit/settings/config.py).  First make your secrets.py like this:

```
cp sendit/settings/bogus_secrets.py sendit/settings/secrets.py
vim sendit/settings/secrets.py
```

Once you have your `secrets.py`, it needs the following added:

 - `SECRET_KEY`: Django will not run without one! You can generate one [here](http://www.miniwebtool.com/django-secret-key-generator/)
 - `DEBUG`: Make sure to set this to `False` for production.


For [config.py](sendit/settings/config.py) you should first configure settings for the restful API:

```
# If True, we will have the images first go to a task to retrieve fields to deidentify
DEIDENTIFY_RESTFUL=True

# The default study to use
SOM_STUDY="test"
```

If `DEIDENTIFY_RESTFUL` is False, we skip this task, and the batch is sent to the next task (or tasks) to send to different storage. If True, the batch is first put in the queue to be de-identified, and then upon receival of the identifiers, the batch is put into the same queues to be sent to storage. The `SOM_STUDY` is part of the Stanford DASHER API to specify a study, and the default should be set before you start the application. If the study needs to vary between calls, please [post an issue](https://www.github.com/pydicom/sendit) and it can be added to be done at runtime. These functions can be modified to use different endpoints, or do different replacements in the data. For more details about the deidentify functions, see [docs/deidentify.md](docs/deidentify.md)

The next set of variables are specific to [storage](docs/storage.md), which is the final step in the pipeline.

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

Importantly, for the above, there must be a `GOOGLE_APPLICATION_CREDENTIALS` filepath exported in the environment, or it should be run on a Google Cloud Instance (unlikely).

## Authentication
If you look in [sendit/settings/auth.py](sendit/settings/auth.py) you will see something called `lockdown` and that it is turned on:

```
# Django Lockdown
LOCKDOWN_ENABLED=True
```

This basically means that the entire site is locked down, or protected for use (from a web browser) with a password. It's just a little extra layer of security. You can set the password by defining it in your [sendit/settings/secrets.py](sendit/settings/secrets.py):

```
LOCKDOWN_PASSWORDS = ('mysecretpassword',)
```

Note that here we will need to add notes about securing the server (https), etc. For now, I'll just mention that it will come down to changing the [nginx.conf](nginx.conf) and [docker-compose.yml](docker-compose.yml) to those provided in the folder [https](https).


## Application
This application lives in a docker-compose orchestration of images running on `STRIDE-HL71`. This application has the following components (each a Docker image):

 - **uwsgi**: is the main python application with Django (python)
 - **nginx**: is a web server to make a status web interface for Research IT
 - **worker**: is the same image as uwsgi, but configured to run a distributed job queue called [celery](http://www.celeryproject.org/). 
 - **redis**: is the database used by the worker, with serialization in json.

The job queue generally works by processing tasks when the server has available resources. There will be likely 5 workers for a single application deployment. The worker will do the following:

 1. First receive a job from the queue to run the [import dicom](docs/import_dicom.md) task when a finished folder is detected by the [watcher](docs/watcher.md)
 2. When import is done, hand to the next task to [de-identify](docs/deidentify.md) images. If the user doesn't want to do this based on [settings](sendit/settings/config.py), a task is fired off to send to storage. If they do, the request is made to the DASHER endpoint, and the identifiers saved.
     a. In the case of de-identification, the next job will do the data strubbing with the identifiers, and then trigger sending to storage.
 3. Sending to storage can be enabled to work with any or none of OrthanC and Google Cloud storage. If no storage is taken, then the application works as a static storage.


### Status
In order to track status of images, we have status states for images and batches. 


```
IMAGE_STATUS = (('NEW', 'The image was just added to the application.'),
               ('PROCESSING', 'The image is currently being processed, and has not been sent.'),
               ('DONEPROCESSING','The image is done processing, but has not been sent.'),
               ('SENT','The image has been sent, and verified received.'),
               ('DONE','The image has been received, and is ready for cleanup.'))

BATCH_STATUS = (('NEW', 'The batch was just added to the application.'),
               ('PROCESSING', 'The batch currently being processed.'),
               ('DONEPROCESSING', 'The batch is done processing'),
               ('DONE','The batch is done, and images are ready for cleanup.'))
```

#### Image Status
Image statuses are updated at each appropriate timepoint, for example:

 - All new images by default are given `NEW`
 - When an image starts any de-identification, but before any request to send to storage, it will have status `PROCESSING`. This means that if an image is not to be processed, it will immediately be flagged with `DONEPROCESSING`
 - As soon as the image is done processing, or if it is intended to go right to storage, it gets status `DONEPROCESSING`.
 - After being send to storage, the image gets status `SENT`, and only when it is ready for cleanup is gets status `DONE`. Note that this means that if a user has no requests to send to storage, the image will remain with the application (and not be deleted.)

#### Batch Status
A batch status is less granular, but more informative for alerting the user about possible errors.

 - All new batches by default are given `NEW`.
 - `PROCESSING` is added to a batch as soon as the job to deidentify is triggered.
 - `DONEPROCESSING` is added when the batch finished de-identification, or if it skips and is intended to go to storage.
 - `DONE` is added after all images are sent to storage, and are ready for cleanup.


### Errors
The most likely error would be an inability to read a dicom file, which could happen for any number of reasons. This, and generally any errors that are triggered during the lifecycle of a batch, will flag the batch as having an error. The variable `has_error` is a boolean that belongs to a batch, and a matching JSONField `errors` will hold a list of errors for the user. This error flag will be most relevant during cleanup.

For server errors, the application is configured to be set up with Opbeat. @vsoch has an account that can handle Stanford deployed applications, and all others should follow instructions for setup [on the website](opbeat.com/researchapps). It comes down to adding a few lines to the [main settings](sendit/settings/main.py). Opbeat (or a similar service) is essential for being notified immediately when any server error is triggered.


### Cleanup
Upon completion, we will want some level of cleanup of both the database, and the corresponding files. It is already the case that the application moves the input files from `/data` into its own media folder (`images`), and cleanup might look like any of the following:

 - In the most ideal case, there are no errors, no flags for the batch, and the original data folder was removed by the `dicom_import` task, and the database and media files removed after successful upload to storage. This application is not intended as some kind of archive for data, but a node that filters and passes along.
 - Given an error to `dicom_import`, a file will be left in the original folder, and the batch `has_error` will be true. In this case, we don't delete files, and we rename the original folder to have extension `.err`

If any further logging is needed (beyond the watcher) we should discuss (see questions below)


## Deployment
After configuration is done and you have a good understanding of how things work, you are ready to turn it on! First, let's learn about how to start and stop the watcher, and the kind of datasets and location that the watcher is expecting. It is up to you to plop these dataset folders into the application's folder being watched.


### 1. Running the Watcher
This initial setup is stupid in that it's going to be checking an input folder to find new images. We do this using the [watcher](sendit/apps/watcher) application, which is started and stopped with a manage.py command:

```
python manage.py watcher_start
python manage.py watcher_stop
```

And the default is to watch for files added to [data](data), which is mapped to '/data' in the container. This means that `STRIDE-HL71` will receive DICOM from somewhere. It should use an atomic download strategy, but with folders, into the application data input folder. This will mean that when it starts, the folder (inside the container) might look like:
 
 
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

A directory is considered "finished" and ready for processing when it does **not** have an entension that starts with "tmp". For more details about the watcher daemon, you can look at [his docs](docs/watcher.md). While many examples are provided, for this application we use the celery task `import_dicomdir` in [main/tasks.py](sendit/apps/main/tasks.py) to read in a finished dicom directory from the directory being watched, and this uses the class `DicomCelery` in the [event_processors](sendit/apps/watcher/event_processors.py) file. Other examples are provided, in the case that you want to change or extend the watcher daemon. For complete details about the import of dicom files, see [docs/dicom_import.md](docs/dicom_import.md)


### 2. Database Models
The Dockerized application is constantly monitoring the folder to look for folders that are not in the process of being populated. When a folder is found:

 - A new object in the database is created to represent the "Batch"
 - Each "Image" is represented by an equivalent object
 - Each "Image" is linked to its "Batch"
 - Currently, all uids for each must be unique.

Generally, the query of interest will retrieve a set of images with an associated accession number, and the input folder will be named by the accession number. Since there is variance in the data with regard to `AccessionNumber` and different series identifiers, for our batches we give them ids based on the folder name.


# Questions
 - Given no errors for a batch, we will be cleaning up the database and the media files, which means complete deletion. Is there any desire for a log to be maintained somewhere, and if so, where? Right now, the logs that we have are for the watcher, that logs the name of the folders and when they are complete. If we want more logging, for what actions, under what circumstances?
