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

from celery.decorators import periodic_task
from celery import (
    shared_task, 
    Celery
)

from celery.schedules import crontab
from sendit.logger import bot
from sendit.apps.main.models import (
    Series,
    SeriesIdentifiers,
    Image
)

from sendit.settings import (
    DEIDENTIFY_RESTFUL,
    SEND_TO_ORTHANC,
    ORTHANC_IPADDRESS,
    ORTHANC_PORT,
    SEND_TO_GOOGLE,
    GOOGLE_CLOUD_STORAGE
)

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sendit.settings')
app = Celery('sendit')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task
def import_dicomdir(dicom_dir):
    bot.debug("Importing %s" %(dicom_dir))
    bot.warning('Vanessa write me!!')

# A directory that is `FINISHED` and changed will have the series already found in the database, and will not be processed again.

@shared_task
def get_identifiers(sid):
    '''get identifiers is the celery task to get identifiers for 
    all images in a series, done by way of sending one restful call
    to the DASHER endpoint. If DEIDENTIFY_RESTFUL is False
    under settings, this function doesn't run
    '''
    if DEIDENTIFY_RESTFUL is True:    
        try:         
            series = Series.objects.get(id=sid)
        except Series.DoesNotExist:
            bot.error("In get_identifiers: Series %s does not exist." %(sid))
            return None
 
        bot.debug("Getting identifiers for %s" %(series))
        bot.warning('Vanessa write me!!')
        # Send off task here to replace identifiers, which will send to storage
    else:
        bot.debug("Vanessa write me!")
        # Otherwise, just fire off function to send to storage as is.


@shared_task
def replace_identifiers(sid):
    '''replace identifiers is called from get_identifiers, given that the user
    has asked to deidentify_restful. This function will do the replacement,
    and then trigger the function to send to storage
    '''
    try:         
        series = Series.objects.get(id=sid)
        series_identifiers = SeriesIdentifiers.get(series=series)
    except:
        bot.error("In replace_identifiers: Series %s or identifiers does not exist." %(sid))
        return None

    bot.debug("Importing %s" %(dicom_dir))
    bot.warning('Vanessa write me!!')

    # Do replacement of identifiers 
    # trigger storage function


@shared_task
def upload_storage(sid):
    '''upload storage will send data to OrthanC and/or Google Storage, depending on the
    user preference.
    '''
    try:         
        series = Series.objects.get(id=sid)
    except:
        bot.error("In upload_storage: Series %s does not exist." %(sid))
        return None

    if SEND_TO_ORTHANC is True:
        bot.log("Sending %s to %s:%s" %(series,ORTHANC_IPADDRESS,ORTHANC_PORT))
        # do the send here!

    if SEND_TO_GOOGLE is True and GOOGLE_CLOUD_STORAGE not in [None,""]:
        bot.log("Uploading to Google Storage %s" %(GOOGLE_CLOUD_STORAGE))
        # GOOGLE_CLOUD_STORAGE
    bot.warning('Vanessa write me!!')


