import os

#####################################################
# RESTFUL API
#####################################################

# De-identify
# If True, we will have the images first go to a task to retrieve fields to deidentify
DEIDENTIFY_RESTFUL=True

# These credentials are required for the DASHER endpoint
STANFORD_APPLICATION_CREDENTIALS='/code/.stanford'
os.environ['STANFORD_CLIENT_SECRETS'] = STANFORD_APPLICATION_CREDENTIALS

# If True, scrub pixel data for images identified by header "Burned in Annotation" = "NO"
DEIDENTIFY_PIXELS=False # currently not supported 

# The default study to use
SOM_STUDY="test"

# PatientID and SOPInstanceUID:
# These are default for deid, but we can change that here
ENTITY_ID="PatientID"
ITEM_ID="SOPInstanceUID"


#####################################################
# STORAGE
#####################################################

# Orthanc Storage
SEND_TO_ORTHANC=True
ORTHANC_IPADDRESS="127.0.0.1"
ORTHANC_PORT=4747

# Google Storage
# Should we send to Google at all?
SEND_TO_GOOGLE=False

# These credentials are required for Google
GOOGLE_APPLICATION_CREDENTIALS='/code/.google'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS

# Google Cloud Storage Bucket (must be created)
GOOGLE_CLOUD_STORAGE='radiology'
GOOGLE_STORAGE_COLLECTION=None # define here or in your secrets
