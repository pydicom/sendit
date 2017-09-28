from django.core.management.base import BaseCommand
from sendit.apps.main.utils import upload_finished

class Command(BaseCommand):
    help = '''upload finished will find batches with status DONE_PROCESSING
              and submit an async job to send to storage.
           '''
    def handle(self,*args, **options):
        upload_finished()
