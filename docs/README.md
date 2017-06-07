# SendIt Documentation

## Overview
The Sendit application is intended to be a modular application that includes the following:

 - a data folder that is watched for complete DICOM datasets.
 - an (optional) pipeline for de-identification, meaning removing/replacing fields in the header and image data.
 - (optionally) sending data to storage, meaning an Orthanc server, and/or Google Cloud Storage/Datastore

Reasonable updates would be:

 - to add a DICOM receiver directly to the application using `pynetdicom3`, so instead of listening for datasets on the filesystem, we can receive them directly.


## Module-specific Documentation

 - [Management](manager.md): an overview of controlling the application with [manage.py](../manage.py)
 - [Logging](logging.md): overview of the logger provided in the application
 - [Watcher](watcher.md): configuration and use of the watcher daemon to detect new DICOM datasets


## Steps in Pipeline
 1. [Dicom Import](dicom_import.md): The logic for when a session directory is detected as finished by the Watcher.
 2. [Deidentify](): the defaults (and configuration) for the de-identification step of the pipeline (under development)
