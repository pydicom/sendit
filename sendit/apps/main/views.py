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

from sendit.apps.main.models import (
    Batch,
    Image,
    BatchIdentifiers
)

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from django.http import (
    HttpResponse, 
    JsonResponse
)

from django.http.response import (
    HttpResponseRedirect, 
    HttpResponseForbidden, 
    Http404
)

from django.shortcuts import (
    get_object_or_404, 
    render_to_response, 
    render, 
    redirect
)

from sendit.apps.watcher.utils import (
    is_watching
)

from sendit.settings import (
    BASE_DIR,
    MEDIA_ROOT
)
import os
media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)


def index_view(request):
    '''index view is associated with the dashboard (home) view of the
    application. It shows the user a table of current batches, and an
    overall summary.
    '''
    batches = Batch.objects.all()
    context = {"active":"dashboard",
               "batches":batches,
               "title":"Dashboard"}
    context['is_watching'] = is_watching()
    
    return render(request, 'main/index.html', context)



def settings_view(request):
    '''settings view is the portal to control turning the watcher on
    and off, as well as seeing general logs. 
    '''
    context = {"active":"settings",
               "title": "Settings"}

    # Is the watcher running?
    context['is_watching'] = is_watching()
 
    return render(request, 'main/settings.html', context)

