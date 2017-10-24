# SendIt Documentation

## Overview
The Sendit application is intended to be a modular application that includes the following:

 - a data folder that is watched for complete DICOM datasets.
 - an (optional) pipeline for anonymization, meaning removing/replacing fields in the header and image data.
 - (optionally) sending data to storage, meaning an Orthanc server, and/or Google Cloud Storage/Datastore

Reasonable updates would be:

 - to add a DICOM receiver directly to the application using `pynetdicom3`, so instead of listening for datasets on the filesystem, we can receive them directly.

## Preparation
The base of the image is distributed via [sendit-base](scripts/docker/README.md). This image has all dependencies for the base so we can easily bring the image up and down.

## Deployment

 - [Setup](setup.md): Basic setup (download and install) of a new application for a server.
 - [Configuration](config.md): How to configure the application before starting it up.
 - [Application](application.md): Details about the application infrastructure.
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
