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

from django.core.files import File
from sendit.logger import bot
from sendit.apps.main.models import (
    Batch,
    BatchIdentifiers,
    Image
)

from sendit.settings import (
    GOOGLE_STORAGE_COLLECTION,
    ENTITY_ID,
    ITEM_ID
)

from django.conf import settings
import uuid
import tarfile
import os


def chunks(l, n):
    '''Yield successive n-sized chunks from l.'''
    for i in range(0, len(l), n):
        yield l[i:i + n]


### FILES ##############################################################

def save_image_dicom(dicom,dicom_file,basename=None):
    '''save image dicom will save a dicom file to django's media
    storage, for this application defined under /images.
    :param dicom: the main.Image instance 
    :param dicom_file: the dicom file (usually in /data) to save
    '''
    if basename is None:
        basename = os.path.basename(dicom_file)
    fullpath = "%s/%s" %(settings.MEDIA_ROOT,
                         basename)

    folder = os.path.dirname(fullpath)
    if not os.path.exists(folder):
        os.mkdir(folder)

    with open(dicom_file,'rb') as filey:
              django_file = File(filey)
              dicom.image.save(basename,
                               django_file,
                               save=True)  
    dicom.save()
    return dicom


def generate_compressed_file(files, filename=None, mode="w:gz", archive_basename=None):
    ''' generate a tar.gz file (default) including a set of files '''
    if filename is None:
        filename = "%s.tar.gz" %str(uuid.uuid4())
    bot.debug("Compressing %s files into %s" %(len(files),filename))
    tar = tarfile.open(filename, mode)
    if archive_basename is None:
        archive_basename = os.path.basename(filename).split('.')[0]
    for name in files:
        # Make the archive flat with the images
        basename = "%s/%s" %(archive_basename,
                             os.path.basename(name))
        tar.add(name, arcname=basename)
    tar.close()
    return filename


## MODELS ##############################################################

def add_batch_message(message,batch,func):
    '''add batch error or warning to log, 
    and flag the batch to have error.
    '''
    func(message)
    batch.has_error = True
    if "errors" not in batch.logs:
        batch.logs['errors'] = []
    # Only add the unique error once
    if message not in batch.logs['errors']:
        batch.logs['errors'].append(message)
    batch.save()
    return batch  

def add_batch_warning(message,batch):
    return add_batch_message(message=message,
                             batch=batch,
                             func=bot.warning)

def add_batch_error(message,batch):
    return add_batch_message(message=message,
                             batch=batch,
                             func=bot.error)


def change_status(images,status):
    '''change status will update an instance status
     to the status choice provided. This works for batch
    and images
    '''
    updated = []
    if not isinstance(images,list):
        images = [images]
    for image in images:
        image.status=status
        image.save()
        updated.append(image)
    if len(updated) == 1:
        updated = updated[0]
    return updated


# METADATA ##############################################################

def prepare_entity_metadata(cleaned_ids,image_count=None):
    '''prepare metadata for entities for Google Storage
    ''' 
    metadata = dict()
    for secret_id, item in cleaned_ids.items():
        eid = item[ENTITY_ID]
        if eid not in metadata:
            metadata[eid] = dict()
        if "PatientAge" in item:
            metadata[eid]["PatientAge"] = item['PatientAge']
        if "PatientSex" in item:
            metadata[eid]["PatientSex"] = item['PatientSex']
    for eid, items in metadata.items():
        if image_count is not None:
            metadata[eid]["IMAGE_COUNT"] = image_count
        metadata[eid]["UPLOAD_AGENT"] = "STARR:SENDITClient"
        metadata[eid]["id"] = eid
    return metadata


def prepare_items_metadata(batch):
    '''prepare metadata for items for Google Storage
    ''' 
    metadata = dict()
    cleaned = batch.batchidentifiers_set.last().cleaned
    for image in batch.image_set.all():
        secret_id = image.uid        
        if secret_id in cleaned:
            metadata[image.image.path] = cleaned[secret_id]
    return metadata


def extract_study_ids(cleaned,uid):
    '''cleaned should be a dictionary with (original item filenames) as
    lookup, and the uid as the variable defined as `ITEM_ID` in the dict
    of values under each item in cleaned. We use the uid of the entity as
    a lookup to link an item (and it's study) to the entity.'''
    studies = []
    for key,vals in cleaned.items():
        if vals[ENTITY_ID]==uid and vals[ITEM_ID] not in studies:
            studies.append(vals[ITEM_ID])
    return studies


def get_entity_images(images,study_ids):
    '''Retrieve a list of entity images based
    on finding the entity id in the study path'''
    entity_images = []
    for study_id in study_ids:
        subset = [x for x in images if study_id in x]
        entity_images = entity_images + subset
    return entity_images
