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
from celery import (
    shared_task, 
    Celery
)

from sendit.logger import bot
from sendit.apps.main.models import (
    Batch,
    BatchIdentifiers,
    Image
)

from sendit.apps.main.tasks.utils import (
    add_batch_error,
    change_status
)

from deid.data import get_deid
from deid.dicom import replace_identifiers as replace_ids
from deid.identifiers import clean_identifiers
from som.api.identifiers.dicom import prepare_identifiers
from sendit.apps.main.tasks.finish import upload_storage

from sendit.settings import (
    DEIDENTIFY_PIXELS,
    SOM_STUDY,
    ENTITY_ID,
    ITEM_ID
)

from django.conf import settings
import os
from copy import deepcopy

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task
def scrub_pixels(bid):
    '''scrub pixels (not currently triggered) will be run to scrub pixel data
    before identifiers are extracted from the header.
    '''
    from .get import get_identifiers
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
def replace_identifiers(bid):
        '''replace identifiers is called from get_identifiers, given that the user
        has asked to deidentify_restful. This function will do the replacement,
        and then trigger the function to send to storage
        '''
    #try:         
        batch = Batch.objects.get(id=bid)
        batch_ids = BatchIdentifiers.objects.get(batch=batch)                  

        # 1) use response from API to generate new fields
        prepared = prepare_identifiers(response=batch_ids.response)
        updated = deepcopy(prepared)

        # 3) use response from API to deidentify all fields in batch.ids
        # clean_identifiers(ids, deid=None, image_type=None, default=None)
        deid = get_deid('dicom.blacklist')
        cleaned = clean_identifiers(ids=updated,
                                    default="KEEP",
                                    deid=deid)

        # Save progress
        batch_ids.cleaned = cleaned 
        batch_ids.updated = updated
        batch_ids.save()
                                  
        # Get updated files
        dicom_files = batch.get_image_paths()
        updated_files = replace_ids(dicom_files=dicom_files,
                                    deid=deid,
                                    ids=updated,            # ids[item] lookup
                                    overwrite=True,         # overwrites copied files
                                    default_action="KEEP",  # don't blank fields
                                    strip_sequences=True,
                                    remove_private=True,
                                    output_folder=output_folder)  # force = True
                                                                  # save = True,
                                                                  # config=None, use deid

        # Rename
        for dcm in batch.image_set.all():
            dicom = dcm.load_dicom()
            output_folder = os.path.dirname(dcm.image.file.name)
            item_id = os.path.basename(dcm.image.path)
            # S6M0<MRN-SUID>_<JITTERED-REPORT-DATE>_<ACCESSIONNUMBER-SUID>
            # Rename the dicom based on suid
            if item_id in updated:
                item_suid = updated[item_id]['item_id']
                dicom = dcm.rename(item_suid) # added to [prefix][dcm.name] 
                # accessionnumberSUID.seriesnumber.imagenumber,  
            dcm.save()


        # 3) save newly de-identified ids for storage upload
        DEIDENTIFY_PIXELS=False
        change_status(batch,"DONEPROCESSING")
        batch.change_images_status('DONEPROCESSING')
        

    #except:
    #    bot.error("In replace_identifiers: Batch %s or identifiers does not exist." %(bid))
    #    return None

    # We don't get here if the call above failed
    #upload_storage.apply_async(kwargs={"bid":bid})