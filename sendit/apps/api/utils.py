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

from sendit.apps.main.utils import ls_fullpath
import os

def get_size(batch):
    '''get the size of a batch, in gb
    '''
    do_calculation = False
    if batch.status == "DONE":
        if "SizeBytes" in batch.qa:
            if batch.qa['SizeBytes'] == 0:
               do_calculation=True        
        else:
            do_calculation = True
    if do_calculation is True: 
        batch_folder = "/data/%s" %(batch.uid)
        dicom_files = ls_fullpath(batch_folder)
        batch.qa['SizeBytes'] = sum(os.path.getsize(f) for f in dicom_files)
        batch.save()
    return batch.qa['SizeBytes']/(1024*1024*1024.0)  # bytes to GB
