from sendit.apps.watcher.commands import stop_watcher
from django.core.management.base import (
    BaseCommand
)

class Command(BaseCommand):
    help = 'Stops monitoring the /data directory'

    def handle(self, *args, **options):
        stop_watcher(as_command=True)
