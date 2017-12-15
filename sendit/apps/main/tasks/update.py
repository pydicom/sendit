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

from deid.dicom import (
    replace_identifiers as replace_ids,
    get_shared_identifiers
)

from deid.identifiers import clean_identifiers
from som.api.identifiers.dicom import prepare_identifiers
from sendit.apps.main.tasks.finish import upload_storage

from sendit.settings import (
    ANONYMIZE_PIXELS,
    ANONYMIZE_RESTFUL,
    SOM_STUDY,
    STUDY_DEID,
    ENTITY_ID,
    ITEM_ID
)

from django.conf import settings
import os
import time
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
            if ANONYMIZE_PIXELS is True:
                print("Anonymization will be done here.")
            else:
                message = "%s has pixel identifiers, anonymize pixels is off, but added to batch. Removing!" %dcm_file
                dicom.delete() # if django-cleanup not in apps, will not delete image file
                batch = add_batch_error(message,batch)

    # At the end, move on to processing headers    
    return get_identifiers(bid=batch.id) 


@shared_task
def replace_identifiers(bid, run_upload_storage=False):
    '''replace identifiers is called from get_identifiers, given that the user
    has asked to anonymize_restful. This function will do the replacement,
    and then trigger the function to send to storage
    '''

    batch = Batch.objects.get(id=bid)
    batch.qa['ProcessStartTime'] = time.time()
    batch_ids = BatchIdentifiers.objects.get(batch=batch)                  

    # 1) use response from API to generate new fields
    working = deepcopy(batch_ids.ids)
    prepared = prepare_identifiers(response=batch_ids.response,
                                   ids=working)
    updated = deepcopy(prepared)
    # 3) use response from API to anonymize all fields in batch.ids
    # clean_identifiers(ids, deid=None, image_type=None, default=None)
    # deid as None will use default "deid.dicom" provided in application
    # specifying a custom file/tag will use this filter first (in addition)
    deid = STUDY_DEID
    cleaned = clean_identifiers(ids=updated,
                                default="KEEP",
                                deid=deid)
    # Save progress
    batch_ids.cleaned = cleaned 
    batch_ids.updated = updated
    batch_ids.save()

    # Get updated files
    dicom_files = batch.get_image_paths()
    output_folder = batch.get_path()
    updated_files = replace_ids(dicom_files=dicom_files,
                                deid=deid,
                                ids=updated,            # ids[item] lookup
                                overwrite=True,         # overwrites copied files
                                output_folder=output_folder,
                                strip_sequences=True,
                                remove_private=True)  # force = True
                                                      # save = True,
    # Get shared information
    aggregate = ["BodyPartExamined", "Modality", "StudyDescription"]
    shared_ids = get_shared_identifiers(dicom_files=updated_files, 
                                        aggregate=aggregate)
    batch_ids.shared = shared_ids
    batch_ids.save()

    # Rename
    for dcm in batch.image_set.all():
        try:
            dicom = dcm.load_dicom()
            item_id = os.path.basename(dcm.image.path)
            # S6M0<MRN-SUID>_<JITTERED-REPORT-DATE>_<ACCESSIONNUMBER-SUID>
            # Rename the dicom based on suid
            if item_id in updated:
                item_suid = updated[item_id]['item_id']
                dcm = dcm.rename(item_suid) # added to [prefix][dcm.name] 
                dcm.save()
            # If we don't have the id, don't risk uploading
            else:
                message = "%s for Image Id %s file read error: skipping." %(item_id, dcm.id)
                batch = add_batch_error(message,batch)                
                dcm.delete()
        except:
            message = "%s for Image Id %s not found in lookup: skipping." %(item_id, dcm.id)
            batch = add_batch_error(message,batch)                
            dcm.delete()

    batch.qa['ProcessFinishTime'] = time.time()

    # We don't get here if the call above failed
    change_status(batch,"DONEPROCESSING")
    batch.save()

    if run_upload_storage is True:
        return upload_storage(batch_ids=[bid])
    else:
        updated_files = batch.get_image_paths()
        return updated_files
