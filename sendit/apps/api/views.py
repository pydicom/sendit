'''
Copyright (c) 2017 Vanessa Sochat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''


from django.http import (
    Http404, 
    JsonResponse, 
    HttpResponse
)

from django.template import RequestContext
from django.shortcuts import render, render_to_response
from django.http import JsonResponse
import hashlib

from sendit.settings import API_VERSION as APIVERSION
from sendit.apps.api.utils import get_size
from sendit.apps.main.utils import get_database
from sendit.apps.main.models import (
    Batch,
    Image
)

from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from sendit.apps.api.serializers import (
    BatchSerializer,
    ImageSerializer
)

from django.contrib.auth.models import User
from datetime import datetime
from glob import glob

#########################################################################
# GET
# requests for information about reports and collections
#########################################################################

def api_view(request,api_version=None):
    if api_version == None:
        api_version = APIVERSION
    context = {"api_version":api_version,
               "active":"api"}
    return render(request, 'routes/api.html', context)


class BatchViewSet(viewsets.ReadOnlyModelViewSet):
    '''A batch is a collection of images to be processed.
    '''
    queryset = Batch.objects.all().order_by('uid')
    serializer_class = BatchSerializer


class ImageViewSet(viewsets.ReadOnlyModelViewSet):
    '''An image is one dicom image (beloning to a batch) to process
    '''
    queryset = Image.objects.all().order_by('uid')
    serializer_class = ImageSerializer


def metrics_view(request):
    '''simple metrics to expose for local user'''

    base = get_database()
    timestamp = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')

    batchlog = {'SEEN': Batch.objects.count(),
                'SENT': Batch.objects.filter(status="DONE").count(),
                'EMPTY':Batch.objects.filter(status="EMPTY").count(),
                'QUEUE':Batch.objects.filter(status="QUEUE").count()}

    response = {"timestamp":timestamp,
                "data_base": base,
                "data_total": len(glob("%s/*" %(base))),
                "batches": batchlog}

    return JsonResponse(response)



def gb_day(request, days=1):
    '''show gb per N days for user. (Default is 1)'''

    days_ago = datetime.today() - timedelta(days=options['days'])
    total_gb = 0
    for batch in Batch.objects.all():
        if batch.status == "DONE":
            if "FinishTime" in batch.qa:
                finish_time = datetime.fromtimestamp(batch.qa['FinishTime'])
                if finish_time > days_ago:
                    size=get_size(batch)
                    total_gb += size

    gb_per_day = total_gb/options['days']

    response = {"timestamp":timestamp,
                "gb_per_day": gb_per_day,
                "days": days}

    return JsonResponse(response)
