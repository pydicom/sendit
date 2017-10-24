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

from .utils import (
    add_batch_error,
    add_batch_warning,
    change_status,
    chunks,
    prepare_entity_metadata,
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
from random import choice
from time import sleep
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task
def upload_storage(batch_ids=None):
    '''upload storage will as a batch, send all batches with DONEPROCESSING status
    to google cloud storage.
    '''
    from sendit.settings import (GOOGLE_CLOUD_STORAGE,
                                 SEND_TO_GOOGLE,
                                 GOOGLE_PROJECT_NAME,
                                 GOOGLE_PROJECT_ID_HEADER,
                                 GOOGLE_STORAGE_COLLECTION)

    if batch_ids is None:
        batches = Batch.objects.filter(status="DONEPROCESSING")
    else:
        batches = Batch.objects.filter(status="DONEPROCESSING", id__in=batch_ids)

    # All variables must be defined for sending!
    if GOOGLE_CLOUD_STORAGE in [None,""]:
        SEND_TO_GOOGLE = False

    if GOOGLE_PROJECT_NAME in [None,""]:
        SEND_TO_GOOGLE = False

    if GOOGLE_STORAGE_COLLECTION in [None,""]:
        SEND_TO_GOOGLE = False

    if SEND_TO_GOOGLE is True:
        from deid.identifiers import get_timestamp

        # I'm not sure we need this
        #if GOOGLE_PROJECT_ID_HEADER is not None:
        #    client.headers["x-goog-project-id"] = GOOGLE_PROJECT_ID_HEADER
        try:
            client = get_client(bucket_name=GOOGLE_CLOUD_STORAGE,
                                project_name=GOOGLE_PROJECT_NAME)
        # Client is unreachable, usually network is being stressed
 
        except: #OSError and ServiceUnavailable
            bot.error("Cannot connect to client.")
            return

        collection = client.create_collection(uid=GOOGLE_STORAGE_COLLECTION)
        for batch in batches:
            valid = True
            batch_ids = BatchIdentifiers.objects.get(batch=batch)

            # Retrieve only images that aren't in PHI folder
            images = batch.get_finished()

            # Stop if no images pass filters
            if len(images) == 0:        
                change_status(batch,"EMPTY")
                message = "batch %s has no images for processing, stopping upload" %(batch.id)
                batch = add_batch_warning(message,batch)
                batch.save()
                continue

            # IR0001fa6_20160525_IR661B54.tar.gz
            # (coded MRN?)_jittereddate_studycode
            required_fields = ['AccessionNumber', 'PatientID']
            for required_field in required_fields:
                if required_field not in batch_ids.shared:
                    change_status(batch,"ERROR")
                    message = "batch ids %s do not have shared PatientID or AccessionNumber, stopping upload" %(bid)
                    batch = add_batch_warning(message,batch)
                    batch.save()
                    valid = False
                if valid is False:
                    continue

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
                valid = False
                continue

            # We prepare shared metadata for one item
            batch_ids.shared['IMAGE_COUNT'] = len(images)
            batch.logs['IMAGE_COUNT'] = len(images)
            batch_ids.save()
            batch.save()
            if valid is True:
                items_metadata = batch_ids.shared
                items = { compressed_file: items_metadata }
                cleaned = deepcopy(batch_ids.cleaned)
                metadata = prepare_entity_metadata(cleaned_ids=cleaned)
                bot.log("Uploading %s with %s images to Google Storage %s" %(os.path.basename(compressed_file),
                                                                         len(images),
                                                                         GOOGLE_CLOUD_STORAGE))
                # We only expect to have one entity per batch
                uid = list(metadata.keys())[0]
                kwargs = {"images":[compressed_file],
                          "collection":collection,
                          "uid":uid,
                          "entity_metadata": metadata[uid],
                          "images_metadata":items}

                # Batch metadata    
                upload_dataset(client=client, k=kwargs)

                # Clean up compressed file
                if os.path.exists(compressed_file):
                    os.remove(compressed_file)

                # Finish and record time elapsed
                change_status(batch,"DONE")

            batch.qa['FinishTime'] = time.time()
            total_time = batch.qa['FinishTime'] - batch.qa['StartTime']
            bot.info("Total time for %s: %s images is %f min" %(batch.uid,
                                                                batch.image_set.count(),
                                                                total_time/60))
            batch.qa['ElapsedTime'] = total_time
            batch.save()


@shared_task
def clean_up(bid, remove_batch=False):
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
        if remove_batch is True:
            batch.delete() #django-cleanup will delete files on delete
    else:
        bot.warning("Batch %s has error, will not be cleaned up." %batch.id)


# We need to make this a function, so we can apply retrying to it
@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000,stop_max_attempt_number=3)

def upload_dataset(client, k):
    #upload_delay = choice([2,4,6,8,10,12,14,16])
    #sleep(upload_delay)
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


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000,stop_max_attempt_number=3)
def get_client(bucket_name, project_name):
    from som.api.google.storage import Client
    return Client(bucket_name=bucket_name,
                  project_name=project_name)
