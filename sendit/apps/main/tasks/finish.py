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
    save_image_dicom
)

from sendit.settings import (
    GOOGLE_APPLICATION_CREDENTIALS,
    GOOGLE_PROJECT_ID_HEADER,
    SEND_TO_ORTHANC,
    SOM_STUDY,
    ORTHANC_IPADDRESS,
    ORTHANC_PORT,
    SEND_TO_GOOGLE,
    GOOGLE_CLOUD_STORAGE,
    GOOGLE_STORAGE_COLLECTION
)

from django.conf import settings
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


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
        bot.log("Beep boop, not configured yet!")
        # do the send here!

    if SEND_TO_GOOGLE is True and GOOGLE_CLOUD_STORAGE not in [None,""]:

        if GOOGLE_STORAGE_COLLECTION is not None:
            from som.api.google.storage import Client
            bot.log("Uploading to Google Storage %s" %(GOOGLE_CLOUD_STORAGE))
            client = Client(bucket_name=GOOGLE_CLOUD_STORAGE)

            if GOOGLE_PROJECT_ID_HEADER is not None:
                client.headers["x-goog-project-id"] = GOOGLE_PROJECT_ID_HEADER

            # Question: what fields to include as metadata?
            # all in header (this includes image dimensions)
            # study
          

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
