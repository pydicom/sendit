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

from sendit.logger import bot
from sendit.apps.main.models import (
    Batch,
    BatchIdentifiers,
    Image
)

from .utils import (
    add_batch_error,
    change_status,
    chunks,
    prepare_entity_metadata,
    prepare_items_metadata,
    extract_study_ids,
    get_entity_images,
    save_image_dicom
)

from sendit.settings import (
    SEND_TO_ORTHANC,
    SEND_TO_GOOGLE,
    SOM_STUDY,
    ORTHANC_IPADDRESS,
    ORTHANC_PORT
)

from retrying import retry
from copy import deepcopy
from django.conf import settings
import time
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task
def upload_storage(bid, do_clean_up=True):
    '''upload storage will send data to OrthanC and/or Google Storage, depending on the
    user preference.
    '''
    from sendit.settings import (GOOGLE_CLOUD_STORAGE,
                                 SEND_TO_GOOGLE,
                                 GOOGLE_PROJECT_NAME,
                                 GOOGLE_PROJECT_ID_HEADER,
                                 GOOGLE_STORAGE_COLLECTION)
    try:         
        batch = Batch.objects.get(id=bid)
        batch_ids = BatchIdentifiers.objects.get(batch=batch)
    except:
        bot.error("In upload_storage: Batch %s does not exist." %(sid))
        return None

    if SEND_TO_ORTHANC is True:
        bot.log("Sending %s to %s:%s" %(batch,ORTHANC_IPADDRESS,ORTHANC_PORT))
        bot.log("Beep boop, not configured yet!")
        # do the send here!

    # All variables must be defined for sending!
    if GOOGLE_CLOUD_STORAGE in [None,""]:
        SEND_TO_GOOGLE = False

    if GOOGLE_PROJECT_NAME in [None,""]:
        SEND_TO_GOOGLE = False

    if GOOGLE_STORAGE_COLLECTION in [None,""]:
        SEND_TO_GOOGLE = False

    if SEND_TO_GOOGLE is True:

        from som.api.google.storage import Client

        # Retrieve only images that aren't in PHI folder
        images = batch.get_finished()
        cleaned = deepcopy(batch_ids.cleaned)
        items = prepare_items_metadata(batch)

        bot.log("Uploading %s finished to Google Storage %s" %(len(images),
                                                               GOOGLE_CLOUD_STORAGE))
        client = Client(bucket_name=GOOGLE_CLOUD_STORAGE,
                        project_name=GOOGLE_PROJECT_NAME)

        # I'm not sure we need this
        #if GOOGLE_PROJECT_ID_HEADER is not None:
        #    client.headers["x-goog-project-id"] = GOOGLE_PROJECT_ID_HEADER

        collection = client.create_collection(uid=GOOGLE_STORAGE_COLLECTION)
        metadata = prepare_entity_metadata(cleaned_ids=cleaned,
                                           image_count=len(images))

        # Batch metadata    
        # we could add additional here
 
        # We need to make this a function, so we can apply retrying to it
        @retry(wait_exponential_multiplier=1000, wait_exponential_max=10000,stop_max_attempt_number=5)
        def upload_dataset(k):
            for uid, meta in k["metadata"].items(): # This should only be one
                study_ids = extract_study_ids(k["cleaned"],uid)
                entity_images = get_entity_images(k["images"],study_ids)
                client.upload_dataset(images=entity_images,
                                      collection=k["collection"],
                                      uid=uid,
                                      images_mimetype="application/dicom",
                                      images_metadata=k["images_metadata"],
                                      entity_metadata=meta,
                                      permission="projectPrivate")
 
        kwargs = {"client":client,
                  "metadata": metadata,
                  "cleaned":cleaned,
                  "images":images,
                  "collection":collection,
                  "images_metadata":items,
                  "permission":"projectPrivate"}

        upload_dataset(kwargs)



    else:
        message = "batch %s send to Google skipped, storage variables missing." %batch
        batch = add_batch_error(message,batch)
        do_clean_up = False
        batch.change_images_status('SENT')

    # Finish and record time elapsed
    change_status(batch,"DONE")
    batch.qa['FinishTime'] = time.time()
    total_time = batch.qa['FinishTime'] - batch.qa['StartTime']
    bot.debug("Total time for %s: %s images is %s" %(batch.uid,
                                                     batch.image_set.count(),
                                                     total_time))
    batch.qa['ElapsedTime'] = total_time
    batch.save()

    if do_clean_up is True:
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
        bot.error("In clean_up: Batch %s does not exist." %(bid))
        return None

    if not batch.has_error:
        images = batch.image_set.all()
        [x.image.delete() for x in images] # deletes image files
        [x.delete() for x in images] # deletes objects
        # batch.delete() #django-cleanup will delete files on delete
    else:
        bot.warning("Batch %s has error, will not be cleaned up." %batch.id)
