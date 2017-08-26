# Application
This application lives in a docker-compose orchestration of images running on `STRIDE-HL71`. This application has the following components (each a Docker image):

 - **uwsgi**: is the main python application with Django (python)
 - **nginx**: is a web server to make a status web interface for Research IT
 - **worker**: is the same image as uwsgi, but configured to run a distributed job queue called [celery](http://www.celeryproject.org/). 
 - **redis**: is the database used by the worker, with serialization in json.

## Job Queue
The job queue generally works by processing tasks when the server has available resources. There will be likely 5 workers for a single application deployment. The worker will do the following:

 1. First receive a job from the queue to run the [import dicom](import_dicom.md) task when a finished folder is detected by the [watcher](watcher.md)
 2. When import is done, hand to the next task to [anonymize](anomymize.md) images. If the user doesn't want to do this based on [settings](../sendit/settings/config.py), a task is fired off to send to storage. If they do, the request is made to the DASHER endpoint, and the identifiers saved.
     a. In the case of anonymization, the next job will do the data strubbing with the identifiers, and then trigger sending to storage.
 3. Sending to storage can be enabled to work with any or none of OrthanC and Google Cloud storage. If no storage is taken, then the application works as a static storage.

**Important note**: for this first testing when we are starting with many pre-existing folders, we are using instead a continuous worker queue with 16 threads (over 16 cores). 

## Status
In order to track status of images, we have status states for images and batches. 


```
IMAGE_STATUS = (('NEW', 'The image was just added to the application.'),
               ('PROCESSING', 'The image is currently being processed, and has not been sent.'),
               ('DONEPROCESSING','The image is done processing, but has not been sent.'),
               ('SENT','The image has been sent, and verified received.'),
               ('DONE','The image has been received, and is ready for cleanup.'))

BATCH_STATUS = (('NEW', 'The batch was just added to the application.'),
               ('PROCESSING', 'The batch currently being processed.'),
               ('EMPTY', 'No images passed filters'),
               ('DONE','The batch is done, and images are ready for cleanup.'))
```

You can use the command line manage.py to export a table of processing times and status:

```
python manage.py export_metrics
sendit-process-time-2017-08-26.tsv
```

### Image Status
Image statuses are updated at each appropriate timepoint, for example:

 - All new images by default are given `NEW`
 - When an image starts any anonymization, but before any request to send to storage, it will have status `PROCESSING`. This means that if an image is not to be processed, it will immediately be flagged with `DONEPROCESSING`
 - As soon as the image is done processing, or if it is intended to go right to storage, it gets status `DONEPROCESSING`.
 - After being send to storage, the image gets status `SENT`, and only when it is ready for cleanup is gets status `DONE`. Note that this means that if a user has no requests to send to storage, the image will remain with the application (and not be deleted.)

### Batch Status
A batch status is less granular, but more informative for alerting the user about possible errors.

 - All new batches by default are given `NEW`.
 - `PROCESSING` is added to a batch as soon as the job to anonymize is triggered.
 - `DONEPROCESSING` is added when the batch finished anonimization, or if it skips and is intended to go to storage.
 - `DONE` is added after all images are sent to storage, and are ready for cleanup.


## Errors
The most likely error would be an inability to read a dicom file, which could happen for any number of reasons. This, and generally any errors that are triggered during the lifecycle of a batch, will flag the batch as having an error. The variable `has_error` is a boolean that belongs to a batch, and a matching JSONField `errors` will hold a list of errors for the user. This error flag will be most relevant during cleanup.

For server errors, the application is configured to be set up with Opbeat. @vsoch has an account that can handle Stanford deployed applications, and all others should follow instructions for setup [on the website](opbeat.com/researchapps). It comes down to adding a few lines to the [main settings](sendit/settings/main.py). Opbeat (or a similar service) is essential for being notified immediately when any server error is triggered.


## Cleanup
Upon completion, we will want some level of cleanup of both the database, and the corresponding files. It is already the case that the application moves the input files from `/data` into its own media folder (`images`), and cleanup might look like any of the following:

 - In the most ideal case, there are no errors, no flags for the batch, and the original data folder was removed by the `dicom_import` task, and the database and media files removed after successful upload to storage. This application is not intended as some kind of archive for data, but a node that filters and passes along.
 - Given an error to `dicom_import`, a file will be left in the original folder, and the batch `has_error` will be true. In this case, we don't delete files, and we rename the original folder to have extension `.err`

If any further logging is needed (beyond the watcher) we should discuss (see questions below)


Now let's [start the application](start.md)!
