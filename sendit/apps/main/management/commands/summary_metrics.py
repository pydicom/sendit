from sendit.logger import bot
from sendit.apps.main.models import Batch
from django.core.management.base import (
    BaseCommand
)

from sendit.apps.main.models import Batch
from sendit.apps.api.views import gb_day

import sys
import os
import pandas

  

    
class Command(BaseCommand):
    help = '''export metrics about size and times to file for past N days'''

    def add_arguments(self, parser):
        parser.add_argument('--days', dest='days', default=7, type=int)
        
    def handle(self,*args, **options):
        days = options['days']
        gb_per_day = gb_day(days=days)

        print(gb_per_day)
