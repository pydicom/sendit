from sendit.logger import bot
from sendit.apps.main.models import Batch
from django.core.management.base import (
    BaseCommand
)

from sendit.apps.main.models import Batch
from sendit.apps.main.tasks import import_dicomdir
from sendit.apps.main.utils import ls_fullpath

import sys
import os


def get_size(batch):
    do_calculation = False
    if batch.status == "DONE":
        if "SizeBytes" in batch.qa:
            if batch.qa['SizeBytes'] == 0:
               do_calculation=True        
        else:
            do_calculation = True
    if do_calculation is True: 
        batch_folder = "/data/%s" %(batch.uid)
        dicom_files = ls_fullpath(batch_folder)
        batch.qa['SizeBytes'] = sum(os.path.getsize(f) for f in dicom_files)
        batch.save()
    return batch.qa['SizeBytes']/(1024*1024.0)  # bytes to MB
  
    

class Command(BaseCommand):
    help = '''get a quick overview of stats for running times'''

    def handle(self,*args, **options):
        
        new_batches = 0
        for batch in Batch.objects.all():
            if batch.status == "DONE":
                size = get_size(batch) # bytes
                time = batch.qa['FinishTime'] - batch.qa['StartTime']
                bot.info("Batch %s: %s MB in %s minutes" %(batch.uid,
                                                           size,
                                                           time/60))
            else:
                new_batches+=1

        bot.info("%s new batches still processing." %(new_batches))
