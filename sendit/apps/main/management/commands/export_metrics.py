from sendit.logger import bot
from sendit.apps.main.models import Batch
from django.core.management.base import (
    BaseCommand
)

from sendit.apps.main.models import Batch
from sendit.apps.main.tasks import import_dicomdir
from sendit.apps.main.utils import ls_fullpath
from sendit.apps.api.utils import get_size

import sys
import os
import datetime
import pandas
  
    

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
                df.loc[batch.id,'size_gb'] = get_size(batch)
                df.loc[batch.id,'start_time'] = batch.qa['StartTime']
                df.loc[batch.id,'finish_time'] = batch.qa['FinishTime']
                time = batch.qa['FinishTime'] - batch.qa['StartTime']
                df.loc[batch.id,'total_time_sec'] = time
                df.loc[batch.id,'total_time_min'] = time/60.0

        df.sort_values(by=['status'],inplace=True)
        df.to_csv(output_file,sep='\t')
