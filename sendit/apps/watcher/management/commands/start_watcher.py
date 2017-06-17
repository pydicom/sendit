from sendit.apps.watcher.commands import start_watcher
from django.core.management.base import (
    BaseCommand
)

class Command(BaseCommand):
    help = '''Starts monitoring the instance /data folder for file events,
              specifically for the addition of complete DICOM series datasets'''


    def handle(self, *args, **options):
        start_watcher(as_command=True)
