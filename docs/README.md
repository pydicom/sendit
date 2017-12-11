# SendIt Documentation

## Overview
The Sendit application is an on demand application that works in two stages to optimally anonymize and push anonymized images and metadata to Google Cloud Storage, and Google Cloud BigQuery, respectively. It works as follows:

 - the researcher starts the anonymization pipeline with an input of one or mode folders
 - each folder is added as a "Batch" with status "QUEUE" to indicate they are ready for import
 - anonymization is performed (status "PROCESSING"), meaning removing/replacing fields in the header and image data, .
 - when status "DONEPROCESSING" is achieved for all in the queue, the researcher triggers the final job to send data to storage (status "SENT")

## Preparation
The base of the image is distributed via [sendit-base](https://github.com/pydicom/sendit/tree/master/scripts/docker). This image has all dependencies for the base so we can easily bring the image up and down.

 - [Application](application.md): If you are a new developer, please read about the application flow and infrastructure first. Sendit is a skeleton that uses other python modules to handle interaction with Stanford and Google APIs, along with anonymization of datasets.

## Deployment

 - [Setup](setup.md): Basic setup (download and install) of a new application for a server.
 - [Configuration](config.md): How to configure the application before starting it up.
 - [Start](start.md): Start it up!
 - [Interface](interface.md): A simple web interface for monitoring batches.

## Module-specific Documentation

 - [Management](manager.md): an overview of controlling the application with [manage.py](../manage.py)
 - [Logging](logging.md): overview of the logger provided in the application
 - [Watcher](watcher.md): configuration and use of the watcher daemon to detect new DICOM datasets


## Steps in Pipeline
 1. [Dicom Import](dicom_import.md): The logic for when a session directory is detected as finished by the Watcher.
 2. [Anonymize](anonymize.md): the defaults (and configuration) for the anonymization step of the pipeline. This currently includes just header fields, and we expect to add pixel anonymization.
 3. [Storage](storage.md): Is the final step to move the anonymized dicom files to OrthanCP and/or Google Cloud Storage.
 4. [Error Handling](errors.md): an overview of how the application managers server, API, and other potential issues.
