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

Importantly, for the above, there must be a `GOOGLE_APPLICATION_CREDENTIALS` filepath exported in the environment, or it should be run on a Google Cloud Instance (unlikely).

**under development**
