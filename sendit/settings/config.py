
#####################################################
# RESTFUL API
#####################################################

# De-identify
# If True, we will have the images first go to a task to retrieve fields to deidentify
DEIDENTIFY_RESTFUL=True

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

# Google Cloud Storage and Datastore
GOOGLE_CLOUD_STORAGE='som-pacs'
