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
    return batch.qa['SizeBytes']/(1024*1024.0)  # bytes to MB
  
    

class Command(BaseCommand):
    help = '''export metrics about size and times to file'''

    def handle(self,*args, **options):
        
        df = pandas.DataFrame(columns=['batch_id','status','size_mb',
                                       'start_time','finish_time',
                                       'total_time_sec','total_time_min'])

        output_file = 'sendit-process-time-%s.tsv' %datetime.datetime.today().strftime('%Y-%m-%d') 
        for batch in Batch.objects.all():
            df.loc[batch.id,'batch_id'] = batch.id
            df.loc[batch.id,'status'] = batch.status
            if batch.status == "DONE":
                df.loc[batch.id,'size_mb'] = get_size(batch)
                df.loc[batch.id,'start_time'] = batch.qa['StartTime']
                df.loc[batch.id,'finish_time'] = batch.qa['FinishTime']
                time = batch.qa['FinishTime'] - batch.qa['StartTime']
                df.loc[batch.id,'total_time_sec'] = time
                df.loc[batch.id,'total_time_min'] = time/60.0

        df.sort_values(by=['status'],inplace=True)
        df.to_csv(output_file,sep='\t')
