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
    add_batch_warning,
    change_status,
    chunks,
    save_image_dicom
)

from deid.dicom import (
    get_identifiers as get_ids,
    has_burned_pixels_single as has_burned_pixels
)
from retrying import retry

from som.api.identifiers.dicom import (
    prepare_identifiers_request
)

from .update import replace_identifiers
from .finish import upload_storage

from som.api.identifiers import Client

from sendit.settings import (
    ANONYMIZE_PIXELS,
    ANONYMIZE_RESTFUL,
    SOM_STUDY,
    STUDY_DEID
)

from django.conf import settings
from sendit.apps.main.utils import ls_fullpath
import time
import os

from pydicom import read_file
from pydicom.errors import InvalidDicomError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# IMPORT ########################################################################


@shared_task
def import_dicomdir(dicom_dir, run_get_identifiers=True):
    '''import dicom directory manages importing a valid dicom set into 
    the application, and is a celery job triggered by the watcher. 
    Here we also flag (and disclude) images that have a header value 
    that indicates pixel identifiers.
    '''
    start_time = time.time()

    if os.path.exists(dicom_dir):
        try:
            dicom_files = ls_fullpath(dicom_dir)
        except NotADirectoryError:
            bot.error('%s is not a directory, skipping.' %dicom_dir)
            return
            
        bot.debug("Importing %s, found %s .dcm files" %(dicom_dir,len(dicom_files)))        

        # The batch --> the folder with a set of dicoms tied to one request
        dcm_folder = os.path.basename(dicom_dir)   
        batch,created = Batch.objects.get_or_create(uid=dcm_folder)
        batch.logs['STARTING_IMAGE_COUNT'] = len(dicom_files)

        # Data quality check: keep a record of study dates
        study_dates = dict()
        series = {}
        all_series = []
        size_bytes = sum(os.path.getsize(f) for f in dicom_files)
        messages = [] # print all unique messages / warnings at end

        # Add in each dicom file to the series
        for dcm_file in dicom_files:
            try:

                # The dicom folder will be named based on the accession#
                dcm = read_file(dcm_file,force=True)
                dicom_uid = os.path.basename(dcm_file)

                # Keep track of studyDate
                study_date = dcm.get('StudyDate')
                series_id = dcm.get('SeriesNumber')
                if series_id not in all_series:
                    all_series.append(series_id)
                if study_date not in study_dates:
                    study_dates[study_date] = 0
                study_dates[study_date] += 1
                flag, flag_group, reason = has_burned_pixels(dicom_file=dcm_file,
                                                             quiet=True,
                                                             deid=STUDY_DEID)

                # If the image is flagged, we don't include and move on
                continue_processing = True
                if flag is True:
                    if flag_group not in ["whitelist"]:
                        continue_processing = False
                        message = "%s is flagged in %s: %s, skipping" %(dicom_uid, 
                                                                        flag_group,
                                                                        reason)
                        batch = add_batch_warning(message,batch,quiet=True)
                        message = "BurnedInAnnotation found for batch %s" %batch.uid
                        if message not in messages:
                            messages.append(message)

                if continue_processing is True:
                    # Create the Image object in the database
                    # A dicom instance number must be unique for its batch
                    dicom = Image.objects.create(batch=batch,
                                                 uid=dicom_uid)

                    # Series Number and count of slices (images)
                    if series_id is not None and series_id not in series:
                        series[series_id] = {'SeriesNumber': series_id,
                                             'Images':1 }
                        # Series Description
                        description = dcm.get('SeriesDescription')
                        if dcm.get('SeriesDescription') is not None:
                            series[series_id]['SeriesDescription'] = description
                    else:
                        series[series_id]['Images'] +=1

                    # Save the dicom file to storage
                    # basename = "%s/%s" %(batch.id,os.path.basename(dcm_file))
                    dicom = save_image_dicom(dicom=dicom,
                                             dicom_file=dcm_file) # Also saves

                    # Generate image name based on [SUID] added later
                    # accessionnumberSUID.seriesnumber.imagenumber,  
                    name = "%s_%s.dcm" %(dcm.get('SeriesNumber'),
                                         dcm.get('InstanceNumber'))
                    dicom.name = name
                    dicom.save()
                    # Only remove files successfully imported
                    #os.remove(dcm_file)

            # Note that on error we don't remove files
            except InvalidDicomError:
                message = "InvalidDicomError: %s skipping." %(dcm_file)
                batch = add_batch_error(message,batch)
            except KeyError:
                message = "KeyError: %s is possibly invalid, skipping." %(dcm_file)
                batch = add_batch_error(message,batch)
            except Exception as e:
                message = "Exception: %s, for %s, skipping." %(e, dcm_file)

        # Print summary messages all at once
        for message in messages:
            bot.warning(message)

        if len(study_dates) > 1:
            message = "% study dates found for %s" %(len(study_dates),
                                                     dcm_file)
            batch = add_batch_error(message,batch)

        # Which series aren't represented with data?
        removed_series = [x for x in all_series if x not in list(series.keys())]

        # Save batch thus far
        batch.qa['NumberOfSeries'] = len(series)
        batch.qa['FlaggedSeries'] = removed_series
        batch.qa['Series'] = series
        batch.qa['StudyDate'] = study_dates
        batch.qa['StartTime'] = start_time
        batch.qa['SizeBytes'] = size_bytes
        batch.save()
         
        # If there were no errors on import, we should remove the directory
        #if not batch.has_error:
            
            # Should only be called given no error, and should trigger error if not empty
            #os.rmdir(dicom_dir)

        # At the end, submit the dicoms to be anonymized as a batch 
        count = batch.image_set.count()
        if count > 0:
            if ANONYMIZE_PIXELS is True:
                bot.warning("Anonimization of pixels is not yet implemented. Images were skipped.")
                # When this is implemented, the function will be modified to add these images
                # to the batch, which will then be first sent through a function to
                # scrub pixels before header data is looked at.
                # scrub_pixels(bid=batch.id)
            #else:
            if run_get_identifiers is True:
                bot.debug("get_identifiers submit batch %s with %s dicoms." %(batch.uid,count))
                return get_identifiers(bid=batch.id)
            else:
                bot.debug("Finished batch %s with %s dicoms" %(batch.uid,count))
                return batch
        else:
            # No images for further processing
            batch.status = "EMPTY"
            batch.qa['FinishTime'] = time.time()
            message = "%s is flagged EMPTY, no images pass filter" %(batch.id)
            batch = add_batch_warning(message,batch)
            batch.save()
            return

    else:
        bot.warning('Cannot find %s' %dicom_dir)


# EXTRACT #######################################################################


@shared_task
def get_identifiers(bid,study=None,run_replace_identifiers=True):
    '''get identifiers is the celery task to get identifiers for 
    all images in a batch. A batch is a set of dicom files that may include
    more than one series/study. This is done by way of sending one restful call
    to the DASHER endpoint. If ANONYMIZE_RESTFUL is False
    under settings, this function doesn't run
    '''
    batch = Batch.objects.get(id=bid)

    if study is None:
        study = SOM_STUDY

    if ANONYMIZE_RESTFUL is True:    

        images = batch.image_set.all()

        # Process all dicoms at once, one call to the API
        dicom_files = batch.get_image_paths()
        batch.status = "PROCESSING"
        batch.save()

        try:
            ids = get_ids(dicom_files=dicom_files,
                          expand_sequences=False)  # we are uploading a zip, doesn't make sense
                                                   # to preserve image level metadata
        except FileNotFoundError:
            batch.status = "ERROR"
            message = "batch %s is missing dicom files and should be reprocessed" %(batch.id)
            batch = add_batch_warning(message,batch)
            batch.save()

        # Prepare identifiers with only minimal required
        # This function expects many items for one entity, returns 
        # request['identifiers'] --> [ entity-with-study-item ]
        request = prepare_identifiers_request(ids) # force: True

        bot.debug("som.client making request to anonymize batch %s" %(bid))

        # Run with retrying, in case issue with token refresh
        result = None
        try:
            result = run_client(study,request)
        except:
            # But any error, don't continue, don't launch new job
            message = "error with client, stopping job."
            batch = add_batch_error(message,batch)
            batch.status = "ERROR"
            batch.qa['FinishTime'] = time.time()
            batch.save()

        # Create a batch for all results
        if result is not None:
            if "results" in result:
                batch_ids,created = BatchIdentifiers.objects.get_or_create(batch=batch)
                batch_ids.response = result['results']
                batch_ids.ids = ids
                batch_ids.save()
                if run_replace_identifiers is True:
                    return replace_identifiers(bid=bid)
                else:
                    return batch_ids
            else:
                message = "'results' field not found in response: %s" %result
                batch = add_batch_error(message,batch)

    else:
        bot.debug("Restful de-identification skipped [ANONYMIZE_RESTFUL is False]")
        change_status(batch,"DONEPROCESSING")
        change_status(batch.image_set.all(),"DONEPROCESSING")
        return upload_storage(bid=bid)



@retry(stop_max_attempt_number=3)
def run_client(study,request):
    cli = Client(study=study)
    return cli.deidentify(ids=request, study=study)
