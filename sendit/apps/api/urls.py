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

from django.views.generic.base import TemplateView
from django.conf.urls import url, include

from rest_framework import routers
from rest_framework.authtoken import views as rest_views
from rest_framework_swagger.views import get_swagger_view

import sendit.apps.api.views as api_views
from sendit.settings import API_VERSION

swagger_view = get_swagger_view(title='sendit API', url='')
router = routers.DefaultRouter()
router.register(r'^images', api_views.ImageViewSet)
router.register(r'^batches', api_views.BatchViewSet)


urlpatterns = [

    url(r'^$', swagger_view),
    url(r'^metrics$', api_views.metrics_view, name='metrics_view'),
    url(r'^metrics/gb/(?P<days>\d+)/$', api_views.gb_day, name="gb_day"),
    url(r'^metrics/gb$', api_views.gb_day, name="gb_day"),
    url(r'^docs$', api_views.api_view, name="api"),
]
