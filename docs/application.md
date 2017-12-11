# Application
This application lives in a docker-compose orchestration of images running on `STRIDE-HL71`. This application has the following components (each a Docker image):

 - **uwsgi**: is the main python application with Django (python)
 - **nginx**: is a web server to make a status web interface for Research IT
 - **worker**: is the same image as uwsgi, but configured to run a distributed job queue called [celery](http://www.celeryproject.org/). 
 - **redis**: is the database used by the worker, with serialization in json.

## Job Queue

### Step 1: Start Queue
The job queue accepts a manual request to import one or more dicom directories, subfolderes under `/data`. We call it a "queue" because it is handled by the worker and redis images, where the worker is a set of threads that can process multiple (~16) batches at once, and redis is the database to manage the queue. The queue can "pile up" and the workers will process tasks when the server has available resources. Thus, to start the pipeline:

 1. You should make sure your `DATA_INPUT_FOLDERS` are defined in [sendit/settings/config.py](../sendit/settings/config.py).
 2. You should then start the queue, which means performing dicom import, get_identifiers, replace identifiers (not upload). This means that images go from having status "QUEUE" to "DONEPROCESSING"
 
```
# Start the queue
python manage.py start_queue

# The defaults are max count 1, /data folder
python manage.py start_queue --number 1 --subfolder /data

```

When you call the above, the workers will do the following:

 1. Check for any Batch objects with status "QUEUE," meaning they were added and not started yet. If there are none in the QUEUE (the default when you haven't used it yet!) then the function uses the `DATA_INPUT_FOLDERS` to find new "contenders." The contender folders each have a Batch created for them, and the Batch is given status QUEUE. We do this up to the max count provided by the "number" variable in the `start_queue` request above.
 2. Up to the max count, the workers then launch the [import dicom](import_dicom.md) task to run async. This function changes the Batch status to "PROCESSING," imports the dicom, extracts header information, prepares/sends/receives a request for [anonymized identifiers](anonymize.md) from DASHER, and then saves a BatchIdentifiers objects. The Batch then is given status "DONEPROCESSING".

It is expected that a set of folders (batches) will do these steps first, meaning that there are no Batches with status "QUEUE" and all are "DONEPROCESSING." We do this because we want to upload to storage in large batches to optimize using the client.


### Step 2: Upload to Storage
When all Batches have status "DONEPROCESSING" we launch a second request to the application to upload to storage:

```
python manage.py upload_finished
```

This task looks for Batches that are "DONEPROCESSING" and distributes the Batches equally among 10 workers. 10 is not a magic number, but I found in testing was a good balance to not trigger weird connection errors that likely come from the fact we are trying to use network resources from inside a Docker container. Sending to storage means two steps:

 1. Upload Images (compressed .tar.gz) to Google Storage, and receive back metadata about bucket locations
 2. Send image metadata + storage metadata to BigQuery

If you are more interested in reading about the storage formats, read more about [storage](storage.md).

## Status
In order to track status of images, we have status states for batches. 


```
BATCH_STATUS = (('QUEUE', 'The batch is queued and not picked up by worker.'),
               ('NEW', 'The batch was just added to the application.'),
               ('EMPTY', 'After processing, no images passed filtering.'),
               ('PROCESSING', 'The batch currently being processed.'),
               ('DONE','The batch is done, and images are ready for cleanup.'))
```

You can use the command line manage.py to export a table of processing times and status:

```
python manage.py export_metrics
sendit-process-time-2017-08-26.tsv
```

## Errors
The most likely error would be an inability to read a dicom file, which could happen for any number of reasons. This, and generally any errors that are triggered during the lifecycle of a batch, will flag the batch as having an error. The variable `has_error` is a boolean that belongs to a batch, and a matching JSONField `errors` will hold a list of errors for the user. This error flag will be most relevant during cleanup.

For server errors, the application is configured to be set up with Opbeat. @vsoch has an account that can handle Stanford deployed applications, and all others should follow instructions for setup [on the website](opbeat.com/researchapps). It comes down to adding a few lines to the [main settings](sendit/settings/main.py). Opbeat (or a similar service) is essential for being notified immediately when any server error is triggered.


## Cleanup
Upon completion, we will want some level of cleanup of both the database, and the corresponding files. It is already the case that the application moves the input files from `/data` into its own media folder (`images`), and cleanup might look like any of the following:

 - In the most ideal case, there are no errors, no flags for the batch, and the database and media files removed after successful upload to storage. Eventually we would want to delete the original files too. This application is not intended as some kind of archive for data, but a node that filters and passes along.
 - Given an error to `dicom_import`, a file will be left in the original folder, and the batch `has_error` will be true. In this case, we don't delete files, and we rename the original folder to have extension `.err`

Now let's [start the application](start.md)!
