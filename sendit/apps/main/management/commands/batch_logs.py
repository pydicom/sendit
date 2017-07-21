from sendit.logger import bot
from sendit.apps.main.models import Batch
from django.core.management.base import (
    BaseCommand
)

import sys

class Command(BaseCommand):
    help = '''show batch logs with errors'''

    def add_arguments(self, parser):
        parser.add_argument('bid', nargs='*', type=int)

    def handle(self,*args, **options):
        
        nbids = len(options['bid'])
        if nbids > 0:
            bot.debug("Inspecting for errors for %s batch ids" %nbids)
            batches = Batch.objects.filter(id__in=options['bid'],
                                           has_error=True)
        else:
            batches = Batch.objects.filter(has_error=True)
        
        if len(batches) == 0:
            bot.info("There are no batches with error.")
            sys.exit(1)

        for batch in batches:
            bot.info("\n# %s" %batch.uid)
            errors = batch.logs['errors']
            for error in errors:
                bot.info(error)
