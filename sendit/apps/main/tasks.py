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
    save_image_dicom,
)

from som.api.identifiers.dicom import get_identifiers

from sendit.settings import (
    DEIDENTIFY_RESTFUL,
    SEND_TO_ORTHANC,
    ORTHANC_IPADDRESS,
    ORTHANC_PORT,
    SEND_TO_GOOGLE,
    GOOGLE_CLOUD_STORAGE
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
    if os.path.exists(dicom_dir):
        dicom_files = ls_fullpath(dicom_dir)
        bot.debug("Importing %s, found %s .dcm files" %(dicom_dir,len(dicom_files)))        
        
        # The batch --> the folder with a set of dicoms tied to one request
        dcm_folder = os.path.basename(dicom_dir)   
        batch,created = Batch.objects.get_or_create(uid=dcm_folder)

        # Add in each dicom file to the series
        for dcm_file in dicom_files:

            try:
                # The dicom folder will be named based on the accession#
                dcm = read_file(dcm_file,force=True)
                dicom_uid = os.path.basename(dcm_file)

                # Create the Image object in the database
                # A dicom instance number must be unique for its batch
                dicom = Image.objects.create(batch=batch,
                                             uid=dicom_uid)

                # Save the dicom file to storage
                dicom = save_image_dicom(dicom=dicom,
                                         dicom_file=dcm_file) # Also saves
                os.remove(dcm_file)

            # Note that on error we don't remove files
            except InvalidDicomError:
                message = "InvalidDicomError: %s skipping." %(dcm_file)
                batch = add_batch_error(message,batch)
               
            except KeyError:
                message = "KeyError: %s is possibly invalid, skipping." %(dcm_file)
                batch = add_batch_error(message,batch)


        # If there were no errors on import, we should remove the directory
        if not batch.has_error:

            # Should trigger error if not empty
            os.rmdir(dicom_dir)

        # At the end, submit the dicoms to be deidentified as a batch 
        count = batch.image_set.count()
        if count > 0:
            bot.debug("Submitting task to get_identifiers for batch %s with %s dicoms." %(batch.uid,
                                                                                          count))
            get_identifiers.apply_async(kwargs={"bid":batch.id})

    else:
        bot.warning('Cannot find %s' %dicom_dir)


@shared_task
def get_identifiers(bid):
    '''get identifiers is the celery task to get identifiers for 
    all images in a batch. A batch is a set of dicom files that may include
    more than one series/study. This is done by way of sending one restful call
    to the DASHER endpoint. If DEIDENTIFY_RESTFUL is False
    under settings, this function doesn't run
    '''
    batch = Batch.objects.get(id=bid)

    if DEIDENTIFY_RESTFUL is True:    

        identifiers = dict()
        images = batch.image_set.all()
        for dcm in images:
 
            # Returns dictionary with {"id": {"identifiers"...}}
            dcm = change_status(dcm,"PROCESSING")
            ids = get_identifiers(dicom_file=dcm.image.path)

            for uid,identifiers in ids.items():

                # STOPPED HERE - I'm not sure why we need to keep
                # study given that we represent things as batches of dicom
                # It might be more suitable to model as a Batch,
                # where a batch is a grouping of dicoms (that might actually
                # be more than one series. Then we would store as Batch,
                # and use the batch ID to pass around and get the images.
                # Stopping here for tonight.
                # Will need to test this out:
                replacements = SeriesIdentifiers.objects.create(series=)

            
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
        batch_identifiers = BatchIdentifiers.get(batch=batch)
    except:
        bot.error("In replace_identifiers: Batch %s or identifiers does not exist." %(bid))
        return None


        for image in batch.image_set.all():

            # Do deidentify replcement here
            change_status(image,"DONEPROCESSING")


    # trigger storage function
    change_status(batch,"DONEPROCESSING")
    change_status(batch.image_set.all(),"DONEPROCESSING")
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
        bot.log("Uploading to Google Storage %s" %(GOOGLE_CLOUD_STORAGE))
        # GOOGLE_CLOUD_STORAGE

        change_status(dcm,"SENT")


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
        [x.delete() for x in images]
        batch.delete() #django-cleanup will delete files on delete
    else:
        bot.warning("Batch %s has error, will not be cleaned up.")
