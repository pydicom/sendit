'''
Images models. 

  Study: one or more series belonging to a patient (not modeled)
  Series: a collection of images, one acquisition
  Image: one dicom image associated with a series
  SeriesIdentifiers: identifiers to be used to de-identify images

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
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/

'''


from taggit.managers import TaggableManager
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.urlresolvers import reverse
from django.db.models.signals import m2m_changed
from django.db.models import Q, DO_NOTHING
from django.db import models

import collections
import operator
import os


#######################################################################################################
# Supporting Functions and Variables ##################################################################
#######################################################################################################


def get_upload_folder(instance,filename):
    '''get_upload_folder will return the folder for an image associated with the ImageSet id.
    instance: the Image instance to upload to the ImageCollection
    filename: the filename of the image
    '''
    series_id = instance.series.id
    study_id = instance.series.study.id

    # This is relative to MEDIA_ROOT
    # /[ MEDIAROOT ] / [ STUDY ] / [ SERIES ] / [ FILENAME ]

    return os.path.join(str(study_id),str(series_id),filename)



IMAGE_STATUS = (('NEW', 'The image was just added to the application.'),
               ('PROCESSING', 'The image is currently being processed, and has not been sent.'),
               ('DONEPROCESSING','The image is done processing, but has not been sent.'),
               ('SENT','The image has been sent, and verified received.'),
               ('DONE','The image has been received, and is ready for cleanup.'))



#################################################################################################
# Study #########################################################################################
#################################################################################################


class Study(models.Model):
    '''A study has one or more series for some patient
    '''
    # Report Collection Descriptors
    uid = models.CharField(max_length=200, null=False, unique=True)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    
    def get_absolute_url(self):
        return reverse('study_details', args=[str(self.id)])

    def __str__(self):
        return "<study-%s-%s>" %(self.id,self.uid)

    def __unicode__(self):
        return "<study-%s-%s>" %(self.id,self.uid)

    def get_label(self):
        return "study"

    class Meta:
        ordering = ["name"]
        app_label = 'images'



class Series(models.Model):
    '''A series is a grouping or collection of images in a study
    '''
    uid = models.CharField(max_length=250, null=False, blank=False, unique=True)
    study = models.ForeignKey(Study,null=False,blank=False)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    tags = TaggableManager()
    
    def __str__(self):
        return "<series-%s-%s>" %(self.id,self.uid)

    def __unicode__(self):
        return "<series-%s-%s>" %(self.id,self.uid)
 
    def get_label(self):
        return "series"

    class Meta:
        ordering = ['series_id']
        app_label = 'images'
 

    def get_absolute_url(self):
        return reverse('series_details', args=[str(self.id)])


class Image(models.Model):
    '''An image maps to one dicom file, usually in a series
    '''
    uid = models.CharField(max_length=250, null=False, blank=False, unique=True)
    image = models.FileField(upload_to=get_upload_folder,null=True,blank=False)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    series = models.ForeignKey(Series,null=False,blank=False)

    def __str__(self):
        return "<image-%s-%s>" %(self.id,self.uid)

    def __unicode__(self):
        return "<image-%s-%s>" %(self.id,self.uid)

    def get_label(self):
        return "image"

    class Meta:
        ordering = ['uid']
        app_label = 'images'
 
    # Get the url for a report collection
    def get_absolute_url(self):
        return reverse('image_details', args=[str(self.id)])


#################################################################################################
# Identifiers ###################################################################################
#################################################################################################


class SeriesIdentifiers(models.Model):
    '''A series identifiers group is used to store a DASHER response
    '''
    series = models.ForeignKey(Series,null=False,blank=False)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    response = JSONField(default=dict())

    def __str__(self):
        return "<series-identifier-%s>" %self.id

    def __unicode__(self):
        return "<series-identifier-%s>" %self.id
 
    def get_label(self):
        return "series"

    class Meta:
        app_label = 'images'
from taggit.managers import TaggableManager
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.urlresolvers import reverse
from django.db.models.signals import m2m_changed
from django.db.models import Q, DO_NOTHING
from django.db import models

import collections
import operator
import os


#######################################################################################################
# Supporting Functions and Variables ##################################################################
#######################################################################################################


def get_upload_folder(instance,filename):
    '''get_upload_folder will return the folder for an image associated with the ImageSet id.
    instance: the Image instance to upload to the ImageCollection
    filename: the filename of the image
    '''
    series_id = instance.series.id
    study_id = instance.series.study.id

    # This is relative to MEDIA_ROOT
    # /[ MEDIAROOT ] / [ STUDY ] / [ SERIES ] / [ FILENAME ]

    return os.path.join(str(study_id),str(series_id),filename)



IMAGE_STATUS = (('NEW', 'The image was just added to the application.'),
               ('PROCESSING', 'The image is currently being processed, and has not been sent.'),
               ('DONEPROCESSING','The image is done processing, but has not been sent.'),
               ('SENT','The image has been sent, and verified received.'),
               ('DONE','The image has been received, and is ready for cleanup.'))



#################################################################################################
# Study #########################################################################################
#################################################################################################


class Study(models.Model):
    '''A study has one or more series for some patient
    '''
    # Report Collection Descriptors
    uid = models.CharField(max_length=200, null=False, unique=True)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    
    def get_absolute_url(self):
        return reverse('study_details', args=[str(self.id)])

    def __str__(self):
        return "<study-%s-%s>" %(self.id,self.uid)

    def __unicode__(self):
        return "<study-%s-%s>" %(self.id,self.uid)

    def get_label(self):
        return "study"

    class Meta:
        ordering = ["name"]
        app_label = 'images'



class Series(models.Model):
    '''A series is a grouping or collection of images in a study
    '''
    uid = models.CharField(max_length=250, null=False, blank=False, unique=True)
    study = models.ForeignKey(Study,null=False,blank=False)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    tags = TaggableManager()
    
    def __str__(self):
        return "<series-%s-%s>" %(self.id,self.uid)

    def __unicode__(self):
        return "<series-%s-%s>" %(self.id,self.uid)
 
    def get_label(self):
        return "series"

    class Meta:
        ordering = ['series_id']
        app_label = 'images'
 

    def get_absolute_url(self):
        return reverse('series_details', args=[str(self.id)])


class Image(models.Model):
    '''An image maps to one dicom file, usually in a series
    '''
    uid = models.CharField(max_length=250, null=False, blank=False, unique=True)
    image = models.FileField(upload_to=get_upload_folder,null=True,blank=False)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    series = models.ForeignKey(Series,null=False,blank=False)

    def __str__(self):
        return "<image-%s-%s>" %(self.id,self.uid)

    def __unicode__(self):
        return "<image-%s-%s>" %(self.id,self.uid)

    def get_label(self):
        return "image"

    class Meta:
        ordering = ['uid']
        app_label = 'images'
 
    # Get the url for a report collection
    def get_absolute_url(self):
        return reverse('image_details', args=[str(self.id)])


#################################################################################################
# Identifiers ###################################################################################
#################################################################################################


class SeriesIdentifiers(models.Model):
    '''A series identifiers group is used to store a DASHER response
    '''
    series = models.ForeignKey(Series,null=False,blank=False)
    add_date = models.DateTimeField('date added', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    response = JSONField(default=dict())

    def __str__(self):
        return "<series-identifier-%s>" %self.id

    def __unicode__(self):
        return "<series-identifier-%s>" %self.id
 
    def get_label(self):
        return "series"

    class Meta:
        app_label = 'images'
