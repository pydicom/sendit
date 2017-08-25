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
    add_batch_warning,
    change_status,
    chunks,
    prepare_entity_metadata,
    prepare_items_metadata,
    generate_compressed_file,
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
    from sendit.apps.main.utils import start_tasks
    from sendit.settings import (GOOGLE_CLOUD_STORAGE,
                                 SEND_TO_GOOGLE,
                                 GOOGLE_PROJECT_NAME,
                                 GOOGLE_PROJECT_ID_HEADER,
                                 GOOGLE_STORAGE_COLLECTION)
    try:         
        batch = Batch.objects.get(id=bid)
        batch_ids = BatchIdentifiers.objects.get(batch=batch)
    except:
        bot.error("In upload_storage: Batch %s does not exist." %(bid))
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
        from deid.identifiers import get_timestamp

        # Retrieve only images that aren't in PHI folder
        images = batch.get_finished()

        # Stop if no images pass filters
        if len(images) == 0:        
            change_status(batch,"EMPTY")
            message = "batch %s has no images for processing, stopping upload" %(bid)
            batch = add_batch_warning(message,batch)
            batch.save()
            if do_clean_up is True:
                clean_up.apply_async(kwargs={"bid":bid})
            return start_tasks(count=1)

        # IR0001fa6_20160525_IR661B54.tar.gz
        # (coded MRN?)_jittereddate_studycode

        studycode = batch_ids.shared['AccessionNumber']
        coded_mrn = batch_ids.shared['PatientID']
        timestamp = get_timestamp(batch_ids.shared['StudyDate'],
                                  format = "%Y%m%d")            

        compressed_filename = "%s/%s_%s_%s.tar.gz" %(batch.get_path(),
                                                     coded_mrn,
                                                     timestamp,
                                                     studycode)

        compressed_file = generate_compressed_file(files=images, # mode="w:gz"
                                                   filename=compressed_filename) 

        # File will be None if no files added
        if compressed_file is None:        
            change_status(batch,"ERROR")
            message = "batch %s problem compressing file, stopping upload" %(bid)
            batch = add_batch_error(message,batch)
            batch.save()

            if do_clean_up is True:
                clean_up.apply_async(kwargs={"bid":bid})
            return start_tasks(count=1)


        # We prepare shared metadata for one item
        items = { compressed_file: batch_ids.shared }
        cleaned = deepcopy(batch_ids.cleaned)
        metadata = prepare_entity_metadata(cleaned_ids=cleaned)


        bot.log("Uploading %s with %s images to Google Storage %s" %(os.path.basename(compressed_file),
                                                                     len(images),
                                                                     GOOGLE_CLOUD_STORAGE))
        client = Client(bucket_name=GOOGLE_CLOUD_STORAGE,
                        project_name=GOOGLE_PROJECT_NAME)

        # I'm not sure we need this
        #if GOOGLE_PROJECT_ID_HEADER is not None:
        #    client.headers["x-goog-project-id"] = GOOGLE_PROJECT_ID_HEADER

        collection = client.create_collection(uid=GOOGLE_STORAGE_COLLECTION)

        # We only expect to have one entity per batch
        uid = list(metadata.keys())[0]
        kwargs = {"images":[compressed_file],
                  "collection":collection,
                  "uid":uid,
                  "entity_metadata": metadata[uid],
                  "images_metadata":items}

        # Batch metadata    
        # we could add additional here
        upload_dataset(client=client, k=kwargs)

        # Clean up compressed file
        if os.path.exists(compressed_file):
            os.remove(compressed_file)

    else:
        do_clean_up = False
        batch.change_images_status('SENT')

    # Finish and record time elapsed
    change_status(batch,"DONE")
    batch.qa['FinishTime'] = time.time()
    total_time = batch.qa['FinishTime'] - batch.qa['StartTime']
    bot.info("Total time for %s: %s images is %f min" %(batch.uid,
                                                        batch.image_set.count(),
                                                        total_time/60))
    batch.qa['ElapsedTime'] = total_time
    batch.save()

    if do_clean_up is True:
        clean_up.apply_async(kwargs={"bid":bid})

    # Start a new task
    start_tasks(count=1)


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

    # force clean up for now, we don't have much server space
    has_error = batch.has_error
    has_error = False

    if not has_error:
        images = batch.image_set.all()
        [x.image.delete() for x in images] # deletes image files
        [x.delete() for x in images] # deletes objects
        # batch.delete() #django-cleanup will delete files on delete
    else:
        bot.warning("Batch %s has error, will not be cleaned up." %batch.id)


# We need to make this a function, so we can apply retrying to it
@retry(stop_max_attempt_number=3)
def upload_dataset(client, k):
    client.upload_dataset(images=k['images'],
                          collection=k["collection"],
                          uid=k['uid'],
                          images_mimetype="application/gzip",
                          images_metadata=k["images_metadata"],
                          entity_metadata=k['entity_metadata'],
                          permission="projectPrivate")


def batch_upload(client,d):
    '''batch upload images, to not stress the datastore api
       not in use, we are uploading a single compressed image.
    '''
    images = d['images']
    # Run the storage/datastore upload in chunks
    for imageset in chunks(d['images'], 500):
        upload_dataset(images=imageset,
                       client=client,
                       k=d)
