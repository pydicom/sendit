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
from django.http.response import Http404
from sendit.settings import (
    DATA_BASE,
    DATA_SUBFOLDER,
    DATA_INPUT_FOLDERS
)
from sendit.apps.main.models import (
    Image,
    Batch
)

import time
from sendit.logger import bot
import sys
import os


#### GETS #############################################################

def get_batch(sid):
    '''get a single report, or return 404'''
    keyargs = {'id':sid}
    try:
        batch = Batch.objects.get(**keyargs)
    except Batch.DoesNotExist:
        raise Http404
    else:
        return batch


def get_image(sid):
    '''get a single report, or return 404'''
    keyargs = {'id':sid}
    try:
        image = Image.objects.get(**keyargs)
    except Image.DoesNotExist:
        raise Http404
    else:
        return image


def get_database():
    ''' get the base directory for parsing images,
    if DATA_SUBFOLDER in settings is None, returns /data
    if set, returns /data/<subfolder>
    '''
    from sendit.settings import DATA_SUBFOLDER
    base = DATA_BASE
    if DATA_SUBFOLDER is not None:
        base = "%s/%s" %(base, DATA_SUBFOLDER.strip('/'))
    return base


def ls_fullpath(dirname,ext=None):
    '''get full path of all files in a directory'''
    if ext is not None:
        return [os.path.join(dirname, f) for f in os.listdir(dirname) if f.endswith(ext)]
    return [os.path.join(dirname, f) for f in os.listdir(dirname)]





#### WORKER ##########################################################

def update_cached(subfolder=None):
    '''
    update the queue (batch object with status QUEUE), intended to be
    run when there are new folders to find and queue.
    First preference goes to a folder supplied to the function, then
    to application defaults. We return None if the result is None.
    '''
    CHECK_FOLDERS = None    

    # First preference goes to variable given at runtime
    if subfolder is not None:
        CHECK_FOLDERS = subfolder

    # Second preference goes to DATA_INPUT_FOLDERS
    if DATA_INPUT_FOLDERS not in ['',None]:
        CHECK_FOLDERS = DATA_INPUT_FOLDERS

    # Final preference goes to data subfolder. We don't parse root.
    # The base of data has directories that need to be organized
    if CHECK_FOLDERS is None:            
        if DATA_SUBFOLDER is not None:
            CHECK_FOLDERS = "%s/%s" %(DATA_BASE,DATA_SUBFOLDER)
        else:
            bot.error("Specify DATA_INPUT_FOLDERS in settings for cached jobs.")
            return

    if not isinstance(CHECK_FOLDERS,list):
        CHECK_FOLDERS = [CHECK_FOLDERS]

    count = 0
    current = [x.uid for x in Batch.objects.all()]
    for base in CHECK_FOLDERS:
        print('Checking base %s' %base)
        if os.path.exists(base):
            contenders = get_contenders(base=base,current=current)
            for contender in contenders:
                dicom_dir = "%s/%s" %(base,contender)
                dcm_folder = os.path.basename(dicom_dir)
                batch,created = Batch.objects.get_or_create(uid=dcm_folder)
                if created is True:
                    batch.status = "QUEUE"
                    batch.logs['DICOM_DIR'] = dicom_dir
                    count+=1
                batch.save()

    print("Added %s contenders for processing queue." %count)


def start_queue(subfolder=None, max_count=None):
    '''
    start queue will be used to move new Batches (jobs) from the QUEUE to be
    run with celery tasks. The status is changed from QUEUE to NEW when this is done.
    If the QUEUE is empty, we parse the filesystem (and queue new jobs) again.
    This job submission is done all at once to ensure that we don't have race
    conditions of multiple workers trying to grab a job at the same time.
    '''
    from sendit.apps.main.tasks import import_dicomdir
    contenders = Batch.objects.filter(status="QUEUE")
    if len(contenders) == 0:
        update_cached(subfolder)
        contenders = Batch.objects.filter(status="QUEUE")

    started = 0    
    for batch in contenders:
        # not seen folders in queue
        dicom_dir = batch.logs.get('DICOM_DIR')
        if dicom_dir is not None:
            import_dicomdir.apply_async(kwargs={"dicom_dir":dicom_dir})
            # If user supplies a count, only start first N
            started +=1
        if max_count is not None:
            if started >= max_count:
                break

    print("Added %s tasks to the active queue." %started)



def get_contenders(base,current=None, filters=None):
    ''' get contenders will return a full set of contender folders from
    a base directory, taking account a list of currently known (current) 
    and filtering to not include folder names ending with the list
    specified by filters
    '''
    if filters is None:
        filters = ['tmp','part']
    contenders = [x for x in os.listdir(base) if not os.path.isfile(x)]
    for ending in filters:
        contenders = [x for x in contenders if not x.endswith(ending)]

    if current is not None:
        contenders = [x for x in contenders if x not in current]
    return contenders
