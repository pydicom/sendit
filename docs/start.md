# Start the Application
After configuration is done and you have a good understanding of how things work, you are ready to turn it on! You have two options - using the watcher (better for on demand, streamed processing) or with a cached queue (better if many datasets are already present). For both, an important note is that each job added to the queue to do dicom import will also handle the complete processing for that job. This is so that we don't have a tasks in the queue relevant
to the same job (for example, imagine a queue of 1000, and adding the "next step" for the first
item to the end. We wouldn't process it until the other 999 are started! Our disk might run
out of space.

## Cached Queue
This approach add jobs to a queue and they are processed when workers are available. This is a slightly longer process since it needs to read the filesystem, but it's only run when the 
previous set of folders found and queued is empty (meaning no Batch objects with status `QUEUE`). 
A cached queue is NOT processed by way of the watcher, but instead the python manage.py start_queue.py script:

```
python manage.py start_queue
```

optionally you can provide the following arguments:

```
--number: a max count to add to the queue
--subfolder: optionally, a subfolder to use assumed in /data, to take preference
```

without any arguments, it goes over the bases defined as subfolders to create the cache

```
DATA_INPUT_FOLDERS=['/data/1_%s' %s for x in range(8) ]  # /data/1_0 through /data/1_7
```

The cache will not be generated until the current set is done and processed.


## Streaming with Watcher
The watcher is intended to be used for streaming data. The folders will be looked for in the  `DATA_BASE` and optionally a specific subfolder, if defined:


```
# Optionally, parse a subfolder under /data, or set to None
DATA_SUBFOLDER="1_6"
```

First, let's learn about how to start and stop the watcher, and the kind of datasets and location that the watcher is expecting. It is up to you to plop these dataset folders into the application's folder being watched.

## 1. Running the Watcher
This initial setup is stupid in that it's going to be checking an input folder to find new images. We do this using the [watcher](../sendit/apps/watcher) application, which is started and stopped with a manage.py command:

```
python manage.py start_watcher
python manage.py stop_watcher
```

And the default is to watch for files added to [data](../data), which is mapped to '/data' in the container. Remember that you can change this mapping in the [docker-compose.yml](../docker-compose.yml). In terms of the strategy for receiving the folders, this is currently up to you, but the high level idea is that the application should receive DICOM from somewhere. It should use an atomic download strategy, but with folders, into the application data input folder. This will mean that when it starts, the folder (inside the container) might look like:
 
 
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

A directory is considered "finished" and ready for processing when it does **not** have an entension that starts with "tmp". For more details about the watcher daemon, you can look at [his docs](watcher.md). While many examples are provided, for this application we use the celery task `import_dicomdir` in [main/tasks.py](../sendit/apps/main/tasks.py) to read in a finished dicom directory from the directory being watched, and this uses the class `DicomCelery` in the [event_processors](../sendit/apps/watcher/event_processors.py) file. Other examples are provided, in the case that you want to change or extend the watcher daemon. For complete details about the import of dicom files, see [dicom_import.md](dicom_import.md)


## 2. Database Models
The Dockerized application is constantly monitoring the folder to look for folders that are not in the process of being populated. When a folder is found:

 - A new object in the database is created to represent the "Batch"
 - Each "Image" is represented by an equivalent object
 - Each "Image" is linked to its "Batch"
 - Currently, all uids for each must be unique.

Generally, the query of interest will retrieve a set of images with an associated accession number, and the input folder will be named by the accession number. Since there is variance in the data with regard to `AccessionNumber` and different series identifiers, for our batches we give them ids based on the folder name.

Now that the application is started, you can learn about usage, starting with the [manager](manager.md), or check out details about the simple [interface](interface.md).
