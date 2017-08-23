from sendit.logger import bot
from django.core.management.base import BaseCommand
from sendit.apps.main.utils import start_tasks
import sys
import os

class Command(BaseCommand):
    help = '''move the queue, or run batch jobs that aren't done yet'''

    def add_arguments(self, parser):
        parser.add_argument('--number', dest='number', default=1, type=int)
        parser.add_argument('--base', dest='base', default='/data', type=str)

    def handle(self,*args, **options):
        
        number = options['number']
        base = options['base']
        start_tasks(count=number, base=base)
