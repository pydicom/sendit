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
from sendit.settings import DATA_SUBFOLDER
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
    base = "/data"
    if DATA_SUBFOLDER is not None:
        base = "%s/%s" %(base, DATA_SUBFOLDER.strip('/'))
    return base


def ls_fullpath(dirname,ext=None):
    '''get full path of all files in a directory'''
    if ext is not None:
        return [os.path.join(dirname, f) for f in os.listdir(dirname) if f.endswith(ext)]
    return [os.path.join(dirname, f) for f in os.listdir(dirname)]





#### WORKER ##########################################################

def start_tasks(count=1, base=None):
    '''
    submit some count of tasks based on those that aren't present
    as batches

    Parameters
    ==========
    count: the number to submit. Default is 1
    base: the base data folder, defaults to /data
    '''
    from random import choice
    from sendit.apps.main.tasks import import_dicomdir
    start_time = time.time()

    if base is None:
        base = get_database()

    current = [x.uid for x in Batch.objects.all()]
    contenders = get_contenders(base=base,current=current)

    # We can't return more contenders than are available
    if count > len(contenders):
       count = len(contenders) - 1

    chosen = [choice(contenders) for x in range(count)]
    seen = []
    started = 0

    while len(chosen) > 0:
        contender = chosen.pop(0)
        if contender not in seen:
            seen.append(contender)
            # Make the batches immediately so we don't double process 
            # not seen folders in queue
            dicom_dir = "%s/%s" %(base,contender)
            dcm_folder = os.path.basename(dicom_dir)
            batch,created = Batch.objects.get_or_create(uid=dcm_folder)
            # Let's be conservative - don't process if it's created
            if created is True:
                batch.save()
                import_dicomdir.apply_async(kwargs={"dicom_dir":dicom_dir})
                started+=1
            else:
                additional = contenders.pop()
                chosen.append(additional)
        else:
            additional = contenders.pop()
            chosen.append(additional)

    end_time = time.time()
    elapsed_time = (end_time - start_time)/60
    bot.debug("Started deid pipeline for %s folders, search took %s minutes" %(started,
                                                                               elapsed_time))


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
