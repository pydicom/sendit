from sendit.logger import bot
from sendit.apps.main.models import Batch
from django.core.management.base import (
    BaseCommand
)

from sendit.apps.main.models import Batch
from datetime import datetime, timedelta

import sys
import os
import datetime
import pandas


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
    return batch.qa['SizeBytes']/(1024*1024*1024.0)  # bytes to GB
  

    
class Command(BaseCommand):
    help = '''export metrics about size and times to file for past N days'''

    def add_arguments(self, parser):
        parser.add_argument('--days', dest='days', default=7, type=int)

    def handle(self,*args, **options):
        days_ago = datetime.today() - timedelta(days=options['days'])
        total_gb = 0
        for batch in Batch.objects.all():
            if batch.status == "DONE":
                if "FinishTime" in batch.qa:
                    finish_time = datetime.fromtimestamp(batch.qa['FinishTime'])
                    if finish_time > days_ago:
                        size=get_size(batch)
                        total_gb += size

        print(total_gb/options['days'])
