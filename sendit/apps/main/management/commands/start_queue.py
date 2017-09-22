from sendit.logger import bot
from django.core.management.base import BaseCommand
from sendit.apps.main.utils import start_queue

import sys
import os

class Command(BaseCommand):
    help = '''start queue will parse over:

              1. First preference: a list of subfolders DATA_INPUT_FOLDERS
              2. Second preference,  a single subfolder at the base (eg /data/<subfolder>) 
              3. The data base alone (/data)

           and submit async jobs to the queue for all new findings. We run this once,
           with the same process, to prevent race conditions if different workers
           were looking for new folders at the same time.
           '''

    def add_arguments(self, parser):
        parser.add_argument('--number', dest='number', default=1, type=int)
        parser.add_argument('--subfolder', dest='base', default='/data', type=str)

    def handle(self,*args, **options):
        number = options['number']
        base = options['base']
        start_queue(max_count=number, subfolder=base)
