# SendIt Documentation

## Overview
The Sendit application is intended to be a modular application that includes the following:

 - a data folder that is watched for complete DICOM datasets.
 - an (optional) pipeline for de-identification, meaning removing/replacing fields in the header and image data.
 - (optionally) sending data to storage, meaning an Orthanc server, and/or Google Cloud Storage/Datastore

Reasonable updates would be:

 - to add a DICOM receiver directly to the application using `pynetdicom3`, so instead of listening for datasets on the filesystem, we can receive them directly.

## Deployment

 - [Setup](setup.md): Basic setup (download and install) of a new application for a server.
 - [Configuration](config.md): How to configure the application before starting it up.
 - [Application](application.md): Details about the application infrastructure.
 - [Start](start.md): Start it up!

## Module-specific Documentation

 - [Management](manager.md): an overview of controlling the application with [manage.py](../manage.py)
 - [Logging](logging.md): overview of the logger provided in the application
 - [Watcher](watcher.md): configuration and use of the watcher daemon to detect new DICOM datasets


## Steps in Pipeline
 1. [Dicom Import](dicom_import.md): The logic for when a session directory is detected as finished by the Watcher.
 2. [Deidentify](deidentify.md): the defaults (and configuration) for the de-identification step of the pipeline. This currently includes just header fields, and we expect to add pixel anonymization.
 3. [Storage](storage.md): Is the final step to move the de-identified dicom files to OrthanCP and/or Google Cloud Storage.
