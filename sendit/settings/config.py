import os

#####################################################
# RESTFUL API
#####################################################

# Anonynize
# If True, we will have the images first go to a task to retrieve fields to anonymize
ANONYMIZE_RESTFUL=True

# These credentials are required for the DASHER endpoint
STANFORD_APPLICATION_CREDENTIALS='/code/.stanford'
os.environ['STANFORD_CLIENT_SECRETS'] = STANFORD_APPLICATION_CREDENTIALS

# If True, scrub pixel data for images identified by header "Burned in Annotation" = "NO"
ANONYMIZE_PIXELS=False # currently not supported 

# An additional specification for white, black, and greylisting data
# If None, only the default (for burned pixel filtering) is used
# Currently, these live with the deid software, eg:
# https://github.com/pydicom/deid/blob/development/deid/data/deid.dicom.xray.chest
# would be referenced with STUDY_DEID="dicom.xray.chest"
STUDY_DEID=None

# PatientID and SOPInstanceUID:
# These are default for deid, but we can change that here
ENTITY_ID="PatientID"
ITEM_ID="AccessionNumber"

#####################################################
# WORKER
#####################################################

# Optionally, parse a subfolder under /data, or set to None
DATA_BASE = "/data"
DATA_SUBFOLDER=None  # ignored if DATA_INPUT_FOLDERS is set
DATA_INPUT_FOLDERS=None

#####################################################
# STORAGE
#####################################################

# Google Storage
# Should we send to Google at all?
SEND_TO_GOOGLE=True

# These credentials are required for Google
GOOGLE_APPLICATION_CREDENTIALS='/code/.google'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS

# Google Cloud Storage Bucket (must be created)
GOOGLE_CLOUD_STORAGE='radiology'
GOOGLE_STORAGE_COLLECTION=''  # must be defined before SOM_STUDY
GOOGLE_PROJECT_NAME=None
