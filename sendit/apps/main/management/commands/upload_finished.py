from django.core.management.base import BaseCommand
from sendit.apps.main.tasks.finish import upload_storage
from sendit.apps.main.models import Batch
from sendit.apps.main.tasks.utils import chunks
from sendit.logger import bot

class Command(BaseCommand):
    help = '''upload finished will find batches with status DONE_PROCESSING
              and submit an async job to send to storage.
           '''
    def handle(self,*args, **options):

        # Break into groups of 16
        batches = Batch.objects.filter(status="DONEPROCESSING")
        batch_size = int(len(batches) / 16)
        
        start = 0
        while start < len(batches):
            end = start + batch_size
            batch_set = batches[start:end]            
            start = end
            bot.info("Adding to Queue batch upload with %s batches" %len(batch_set))
            batch_ids = [b.id for b in batch_set]       
            upload_storage.apply_async(kwargs = {'batch_ids': batch_ids})

