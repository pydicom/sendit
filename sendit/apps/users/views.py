'''
Django settings for sendit project.

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

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    render_to_response, 
    redirect, 
    render
)

from django.template.context import RequestContext
import os

from django.contrib.auth.decorators import login_required



##################################################################################
# AUTHENTICATION VIEWS ###########################################################
##################################################################################

def login(request):
    #context = {'request': request, 'user': request.user}
    #context = RequestContext(request,context)
    #return render_to_response('social/login.html', context_instance=context)
    return render(request, 'social/login.html')


@login_required(login_url='/')
def home(request):
    return render_to_response('social/home.html')

def logout(request):
    '''log out of the social authentication backend'''
    auth_logout(request)
    return redirect('/')



# Python social auth extensions
def redirect_if_no_refresh_token(backend, response, social, *args, **kwargs):
    '''http://python-social-auth.readthedocs.io/en/latest/use_cases.html
       #re-prompt-google-oauth2-users-to-refresh-the-refresh-token
    '''
    if backend.name == 'google-oauth2' and social and response.get('refresh_token') is None and social.extra_data.get('refresh_token') is None:
        return redirect('/login/google-oauth2?approval_prompt=force')


# A User should not be allowed to associate a Github (or other) account with a different
# gmail, etc.
def social_user(backend, uid, user=None, *args, **kwargs):
    '''OVERRIDED: It will give the user an error message if the
    account is already associated with a username.'''
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)
    if social:
        if user and social.user != user:
            msg = 'This {0} account is already in use.'.format(provider)
            return login(request=backend.strategy.request,
                         message=msg)
            #raise AuthAlreadyAssociated(backend, msg)
        elif not user:
            user = social.user

    return {'social': social,
            'user': user,
            'is_new': user is None,
            'new_association': social is None}
