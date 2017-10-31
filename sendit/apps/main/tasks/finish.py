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
    SEND_TO_GOOGLE,
    SOM_STUDY,
    ENTITY_ID,
    ITEM_ID
)

from som.api.google.bigquery.schema import dicom_schema

from retrying import retry
from copy import deepcopy
from django.conf import settings
import time
from random import choice
from time import sleep
import os
import json


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

        try:
            client = get_client(bucket_name=GOOGLE_CLOUD_STORAGE,
                                project_name=GOOGLE_PROJECT_NAME)

        # Client is unreachable, usually network is being stressed
        # this is why we instantiate in batches to upload 
        except: #OSError and ServiceUnavailable
            bot.error("Cannot connect to client.")
            return

        # Create/get BigQuery dataset, collection should be IRB
        dataset = client.get_or_create_dataset(GOOGLE_STORAGE_COLLECTION)

        # Create a table based on ...
        table = client.get_or_create_table(dataset=dataset,    # All tables named dicom
                                           table_name='dicom',
                                           schema=dicom_schema)
        
        for batch in batches:
            valid = True

            batch.qa['UploadStartTime'] = time.time()
            batch_ids = BatchIdentifiers.objects.get(batch=batch)

            # Retrieve only images that aren't in PHI folder
            images = batch.get_finished()

            # Stop if no images pass filters
            if len(images) == 0:        
                change_status(batch,"EMPTY")
                message = "batch %s has no images for processing, stopping upload" %(bid)
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

            # Add additional shared metadata
            studycode = batch_ids.shared['AccessionNumber']
            coded_mrn = batch_ids.shared['PatientID']
            batch_ids.shared['CodedPatientID'] = coded_mrn
            batch_ids.shared['ContentType'] = 'application/gzip'
            batch_ids.shared['CodedAccessionNumberID'] = studycode
            batch_ids.shared['NumberOfSeries'] = batch.qa['NumberOfSeries']
            batch_ids.shared['Series'] = batch.qa['Series']
            batch_ids.shared['RemovedSeries'] = batch.qa['FlaggedSeries']

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

                metadata = deepcopy(batch_ids.shared)
                metadata['DicomHeader'] = json.dumps(metadata)
                metadata = { compressed_file: metadata }
                bot.log("Uploading %s with %s images to Google Storage %s" %(os.path.basename(compressed_file),
                                                                         len(images),
                                                                         GOOGLE_CLOUD_STORAGE))
                # We only expect to have one entity per batch
                kwargs = {"items":[compressed_file],
                          "table":table,
                          "study": SOM_STUDY,
                          "metadata": metadata,
                          "batch": False} # upload in batches at END

                # Batch metadata    
                upload_dataset(client=client, k=kwargs)

                # Clean up compressed file
                if os.path.exists(compressed_file):
                    os.remove(compressed_file)

                # Finish and record time elapsed
                change_status(batch,"DONE")

            batch.qa['UploadFinishTime'] = time.time()
            total_time = batch.qa['FinishTime'] - batch.qa['StartTime']
            bot.info("Total time for %s: %s images is %f min" %(batch.uid,
                                                                batch.image_set.count(),
                                                                total_time/60))
            batch.qa['ElapsedTime'] = total_time
            batch.save()

        # After image upload, metadata can be uploaded on one batch
        # If this isn't optimal, change "batch" in kwargs to False
        return client.batch.runInsert(table)


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
    client.upload_dataset(items=k['items'],
                          table=k['table'],
                          mimetype="application/gzip",
                          entity_key=ENTITY_ID,
                          item_key=ITEM_ID,
                          study_name=k['study'],
                          batch=k['batch'],
                          metadata=k['metadata'],
                          permission="projectPrivate") # default batch=True


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000,stop_max_attempt_number=3)
def get_client(bucket_name, project_name):
    '''get client is a wrapper for creating the BigQuery client, in the case that
       there is network error or other.
    ''' 

    # BigQuery client
    from som.api.google.bigquery import BigQueryClient as Client

    return Client(bucket_name=bucket_name,
                  project=project_name)

