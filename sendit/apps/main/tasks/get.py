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
    change_status,
    chunks,
    save_image_dicom
)

from deid.dicom import get_identifiers as get_ids

from som.api.identifiers.dicom import (
    prepare_identifiers_request
)

from .update import replace_identifiers
from .finish import upload_storage

from som.api.identifiers import Client

from sendit.settings import (
    DEIDENTIFY_RESTFUL,
    DEIDENTIFY_PIXELS,
    SOM_STUDY
)

from django.conf import settings
from sendit.apps.main.utils import ls_fullpath
import os

from pydicom import read_file
from pydicom.errors import InvalidDicomError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# IMPORT ########################################################################


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

        # Data quality check: keep a record of study dates
        study_dates = dict()

        # Add in each dicom file to the series
        for dcm_file in dicom_files:

            try:
                # The dicom folder will be named based on the accession#
                dcm = read_file(dcm_file,force=True)
                dicom_uid = os.path.basename(dcm_file)

                # Keep track of studyDate
                study_date = dcm.get('StudyDate')
                if study_date not in study_dates:
                    study_dates[study_date] = 0
                study_dates[study_date] += 1

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

        if len(study_dates) > 1:
            message = "% study dates found for %s" %(len(study_dates),
                                                     dcm_file)
            batch = add_batch_error(message,batch)

        # Save batch thus far
        batch.qa['StudyDate'] = study_dates
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


# EXTRACT #######################################################################


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

        # Process all dicoms at once, one call to the API
        dicom_files = batch.get_image_paths()
        batch.change_images_status('PROCESSING')
        batch.save() # redundant

        # deid get_identifiers: returns ids[entity][item] = {"field":"value"}
        ids = get_ids(dicom_files=dicom_files,
                      expand_sequences=True)  # expand sequences to flat structure

        # Prepare identifiers with only minimal required
        request = prepare_identifiers_request(ids) # force: True

        bot.debug("som.client making request to deidentify batch %s" %(bid))

        # We need to break into items of size 1000 max, 900 to be safe
        cli = Client(study=study)
        result = cli.deidentify(ids=request, study=study)

        # Create a batch for all results
        if "results" in result:
            batch_ids,created = BatchIdentifiers.objects.get_or_create(batch=batch)
            batch_ids.response = result['results']
            batch_ids.ids = ids
            batch_ids.save()        
            replace_identifiers.apply_async(kwargs={"bid":bid})
        else:
            message = "'results' field not found in response: %s" %result
            batch = add_batch_error(message,batch)

    else:
        bot.debug("Restful de-identification skipped [DEIDENTIFY_RESTFUL is False]")
        change_status(batch,"DONEPROCESSING")
        change_status(batch.image_set.all(),"DONEPROCESSING")
        upload_storage.apply_async(kwargs={"bid":bid})


@shared_task
def batch_deidentify(ids,bid,study=None):
    '''batch deidentify will send requests to the API in batches of 1000
    items per, and reassemble into one response.
    '''
    batch = Batch.objects.get(id=bid)
    results = []
    if study is None:
        study = SOM_STUDY

    # Create an som client
    cli = Client(study=study)

    for entity in ids['identifiers']:
        entity_parsed = None
        template = entity.copy()
        items_response = []
        for itemset in chunks(entity['items'], 950):
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
    return results
