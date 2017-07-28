'''

Copyright (c) 2017 Vanessa Sochat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''

from sendit.logger import bot
from celery.decorators import periodic_task
from celery import (
    shared_task, 
    Celery
)

from celery.schedules import crontab
from sendit.logger import bot
from sendit.apps.main.models import (
    Batch,
    BatchIdentifiers,
    Image
)

from sendit.apps.main.utils import (
    add_batch_error,
    change_status,
    chunks,
    save_image_dicom,
)

from som.api.identifiers.dicom import (
    get_identifiers as get_ids,
    replace_identifiers as replace_ids,
    prepare_identifiers
)

from som.api.identifiers import Client

from sendit.settings import (
    GOOGLE_PROJECT_ID_HEADER,
    DEIDENTIFY_RESTFUL,
    DEIDENTIFY_PIXELS,
    SEND_TO_ORTHANC,
    SOM_STUDY,
    ORTHANC_IPADDRESS,
    ORTHANC_PORT,
    ENTITY_ID,
    ITEM_ID,
    SEND_TO_GOOGLE,
    GOOGLE_CLOUD_STORAGE,
    GOOGLE_STORAGE_COLLECTION
)

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from sendit.apps.main.utils import (
    ls_fullpath
)
import os

from pydicom import read_file
from pydicom.errors import InvalidDicomError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task
def import_dicomdir(dicom_dir):
    '''import dicom directory manages importing a valid dicom set into the application,
    and is a celery job triggered by the watcher. Here we also flag (and disclude)
    images that have a header value that indicates pixel identifiers.
    '''
    if os.path.exists(dicom_dir):
        dicom_files = ls_fullpath(dicom_dir)
        bot.debug("Importing %s, found %s .dcm files" %(dicom_dir,len(dicom_files)))        
        
        # The batch --> the folder with a set of dicoms tied to one request
        dcm_folder = os.path.basename(dicom_dir)   
        batch,created = Batch.objects.get_or_create(uid=dcm_folder)
        patient_ids = []

        # Add in each dicom file to the series
        for dcm_file in dicom_files:
            try:
                # The dicom folder will be named based on the accession#
                dcm = read_file(dcm_file,force=True)
                dicom_uid = os.path.basename(dcm_file)

                # If the image has pixel identifiers, we don't include 
                if dcm.get("BurnedInAnnotation") is not None:
                    message = "%s has burned pixel annotation, skipping" %dicom_uid
                    batch = add_batch_error(message,batch)
                else:
                    # Create the Image object in the database
                    # A dicom instance number must be unique for its batch
                    dicom = Image.objects.create(batch=batch,
                                                 uid=dicom_uid)

                    # Save the dicom file to storage
                    dicom = save_image_dicom(dicom=dicom,
                                             dicom_file=dcm_file) # Also saves

                    # Only remove files successfully imported
                    if dcm.PatientID not in patient_ids:
                        patient_ids.append(dcm.PatientID)
                    #os.remove(dcm_file)

                # Do check for different patient ids
                if len(set(patient_ids)) > 1:                
                    message = "Batch %s has > 1 PatientID" %(batch)
                    batch = add_batch_error(message,batch)

            # Note that on error we don't remove files
            except InvalidDicomError:
                message = "InvalidDicomError: %s skipping." %(dcm_file)
                batch = add_batch_error(message,batch)

            except KeyError:
                message = "KeyError: %s is possibly invalid, skipping." %(dcm_file)
                batch = add_batch_error(message,batch)

            except Exception as e:
                message = "Exception: %s, for %s, skipping." %(e, dcm_file)


        # Save batch thus far
        batch.save()
         
        # If there were no errors on import, we should remove the directory
        #if not batch.has_error:
            
            # Should only be called given no error, and should trigger error if not empty
            #os.rmdir(dicom_dir)

        # At the end, submit the dicoms to be deidentified as a batch 
        count = batch.image_set.count()
        if count > 0:
            bot.debug("Submitting task to get_identifiers for batch %s with %s dicoms." %(batch.uid,
                                                                                          count))
            if DEIDENTIFY_PIXELS is True:
                bot.warning("Deidentify pixels is not yet implemented. Images were skipped.")
                # When this is implemented, the function will be modified to add these images
                # to the batch, which will then be first sent through a function to
                # scrub pixels before header data is looked at.
                # scrub_pixels.apply_async(kwargs={"bid":batch.id})
            #else:
            get_identifiers.apply_async(kwargs={"bid":batch.id})

    else:
        bot.warning('Cannot find %s' %dicom_dir)


@shared_task
def scrub_pixels(bid):
    '''scrub pixels (not currently triggered) will be run to scrub pixel data
    before identifiers are extracted from the header.
    '''
    batch = Batch.objects.get(id=bid)
    images = batch.image_set.all()
    batch.change_images_status('PROCESSING')

    # from deid.dicom import scrub_pixels

    for dcm in images:

        dcm_file = dcm.image.path
        dicom_uid = os.path.basename(dcm_file)
        dicom = dcm.load_dicom()

        if dicom.get("BurnedInAnnotation") is not None:

            # We shouldn't be in this function if False, but we will check again anyway
            if DEIDENTIFY_PIXELS is True:
                print("De-identification will be done here.")
            else:
                message = "%s has pixel identifiers, deidentify pixels is off, but added to batch. Removing!" %dcm_file
                dicom.delete() # if django-cleanup not in apps, will not delete image file
                batch = add_batch_error(message,batch)

    # At the end, move on to processing headers    
    get_identifiers.apply_async(kwargs={"bid":batch.id})
 


@shared_task
def get_identifiers(bid,study=None):
    '''get identifiers is the celery task to get identifiers for 
    all images in a batch. A batch is a set of dicom files that may include
    more than one series/study. This is done by way of sending one restful call
    to the DASHER endpoint. If DEIDENTIFY_RESTFUL is False
    under settings, this function doesn't run
    '''
    batch = Batch.objects.get(id=bid)

    if study is None:
        study = SOM_STUDY

    if DEIDENTIFY_RESTFUL is True:    

        images = batch.image_set.all()

        # Create an som client
        cli = Client()

        # Process all dicoms at once, one call to the API
        dicom_files = batch.get_image_paths()
        batch.change_images_status('PROCESSING')
 
        # Returns dictionary with {"identifiers": [ E1,E2 ]}
        ids = get_ids(dicom_files=dicom_files)

        bot.debug("som.client making request to deidentify batch %s" %(bid))

        # API can't handle a post of size ~few thosand, break into pieces
        results = []

        for entity in ids['identifiers']:
            entity_parsed = None
            template = entity.copy()
            items_response = []

            for itemset in chunks(entity['items'],1000):
                template['items'] = itemset
                request = {'identifiers': [template] }             
                result = cli.deidentify(ids=request, study=study)  # should return dict with "results"

                if "results" in result:
                    for entity_parsed in result['results']:                        
                        if 'items' in entity_parsed:
                            items_response += entity_parsed['items']
                    if 'items' in result['results']:
                        print("Adding %s items" %len(result['results']['items']))
                        items_response += result['results']['items']
                else:
                    message = "Error calling som uid endpoint: %s" %result
                    batch = add_batch_error(message,batch)

            # For last entity, compile items with entity response
            entity_parsed['items'] = items_response
            results.append(entity_parsed)

        # Create a batch for all results
        batch_ids = BatchIdentifiers.objects.create(batch=batch,response=results)
        batch_ids.save()        
        replace_identifiers.apply_async(kwargs={"bid":bid})


    else:
        bot.debug("Restful de-identification skipped [DEIDENTIFY_RESTFUL is False]")
        change_status(batch,"DONEPROCESSING")
        change_status(batch.image_set.all(),"DONEPROCESSING")
        upload_storage.apply_async(kwargs={"bid":bid})


@shared_task
def replace_identifiers(bid):
    '''replace identifiers is called from get_identifiers, given that the user
    has asked to deidentify_restful. This function will do the replacement,
    and then trigger the function to send to storage
    '''
    try:         
        batch = Batch.objects.get(id=bid)
        batch_ids = BatchIdentifiers.get(batch=batch)        

        # replace ids to update the dicom_files (same paths)
        dicom_files = batch.get_image_paths()

        # Prepare the identifiers - not this isn't necessary, but we do it
        # so we can rename the images before upload
        ids = prepare_identifiers(response=batch_ids.response,
                                  dicom_files=dicom_files)

        # Save the identifers for adding as metadata to image files later
        batch_ids.ids = ids
        batch_ids.save()

        # Now we have a lookup with ids[entity_id][field]
        for dcm in batch.image_set.all():
            dicom = dcm.load_dicom()
            output_folder = os.path.dirname(dcm.image.file.name)
            eid = dicom.get(ENTITY_ID)
            iid = dicom.get(ITEM_ID)
            # Rename the dicom based on suid
            if eid is not None and iid is not None:
                item_suid = ids[eid][iid]['item_id']
                dicom = dcm.rename("%s.dcm" %item_suid)

        # Get renamed files
        dicom_files = batch.get_image_paths()
        updated_files = replace_ids(dicom_files=dicom_files,
                                    response=batch_ids.response,
                                    overwrite=True,
                                    output_folder=output_folder)  

        DEIDENTIFY_PIXELS=False

        change_status(batch,"DONEPROCESSING")
        batch.change_images_status('DONEPROCESSING')
        

    except:
        bot.error("In replace_identifiers: Batch %s or identifiers does not exist." %(bid))
        return None

    # We don't get here if the call above failed
    upload_storage.apply_async(kwargs={"bid":bid})


@shared_task
def upload_storage(bid):
    '''upload storage will send data to OrthanC and/or Google Storage, depending on the
    user preference.
    '''
    try:         
        batch = Batch.objects.get(id=bid)
    except:
        bot.error("In upload_storage: Series %s does not exist." %(sid))
        return None

    if SEND_TO_ORTHANC is True:
        bot.log("Sending %s to %s:%s" %(batch,ORTHANC_IPADDRESS,ORTHANC_PORT))
        # do the send here!

    if SEND_TO_GOOGLE is True and GOOGLE_CLOUD_STORAGE not in [None,""]:

        if GOOGLE_STORAGE_COLLECTION is not None:
            from som.api.google.storage import Client
            bot.log("Uploading to Google Storage %s" %(GOOGLE_CLOUD_STORAGE))

            # Question: what fields to include as metadata?
            # all in header (this includes image dimensions)
            # study
          
            if GOOGLE_PROJECT_ID_HEADER is not None:
                client.add_headers({"x-goog-project-id": GOOGLE_PROJECT_ID_HEADER})

            # PREPARE FILES HERE
            # updated files...

            client = Client(bucket_name=GOOGLE_CLOUD_STORAGE)
            collection = client.create_collection(uid=SOM_STUDY)

            # Upload the dataset
            client.upload_dataset(images=updated_files,
                                  collection=collection,
                                  uid=metadata['id'],
                                  entity_metadata=metadata)
 
        else:
            message = "batch %s send to Google skipped, no storage collection defined." %batch
            batch = add_batch_error(message,batch)

        batch.change_images_status('SENT')


    change_status(batch,"DONE")
    clean_up.apply_async(kwargs={"bid":bid})



@shared_task
def clean_up(bid):
    '''clean up will check a batch for errors, and if none exist, clear the entries
    from the database. If no errors occurred, the original folder would have been deleted
    after dicom import.
    '''
    try:         
        batch = Batch.objects.get(id=bid)
    except:
        bot.error("In clean_up: Series %s does not exist." %(sid))
        return None

    if not batch.has_error:
        images = batch.image_set.all()
        [x.image.delete() for x in images] # deletes image files
        [x.delete() for x in images] # deletes objects
        batch.delete() #django-cleanup will delete files on delete
    else:
        bot.warning("Batch %s has error, will not be cleaned up.")
