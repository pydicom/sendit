# De-identify
# If True, we will have the images first go to a task to retrieve fields to deidentify
DEIDENTIFY_RESTFUL=True

#####################################################
# STORAGE
#####################################################

# Orthanc Storage
SEND_TO_ORTHANC=True
ORTHANC_IPADDRESS="127.0.0.1"
ORTHAC_PORT=4747

# Google Storage
# Should we send to Google at all?
SEND_TO_GOOGLE=False

# Google Cloud Storage and Datastore
GOOGLE_CLOUD_STORAGE='som-pacs'