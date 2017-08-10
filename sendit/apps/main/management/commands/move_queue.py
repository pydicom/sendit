from sendit.logger import bot
from sendit.apps.main.models import Batch
from django.core.management.base import (
    BaseCommand
)

from sendit.apps.main.models import Batch
from sendit.apps.main.tasks import import_dicomdir

import sys
import os


def get_contenders(base,current=None):
    contenders = [x for x in os.listdir(base) if not os.path.isdir(x)]
    contenders = [x for x in contenders if not x.endswith('tmp')]
    if current is not None:
        contenders = [x for x in contenders if x not in current]
    return contenders


class Command(BaseCommand):
    help = '''move the queue, or run batch jobs that aren't done yet'''

    def add_arguments(self, parser):
        parser.add_argument('--number', dest='number', default=None, type=str)
        parser.add_argument('--base', dest='base', default='/data', type=str)

    def handle(self,*args, **options):
        
        number = options['number']
        base = options['base']

        current = [x.uid for x in Batch.objects.all()]
        contenders = get_contenders(base=base,current=current)

        if number is not None:
            number = int(number)
            if number > len(contenders):
                number = len(contenders) - 1
            contenders = contenders[0:number]

        bot.debug("Starting deid pipeline for %s folders" %len(contenders))

        for contender in contenders:
            dicom_dir = "%s/%s" %(base,contender)
            import_dicomdir.apply_async(kwargs={"dicom_dir":dicom_dir})
