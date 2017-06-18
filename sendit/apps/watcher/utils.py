'''
utilities for the watcher

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

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from sendit.logger import bot
from django.contrib import messages

from django.core.management.base import (
    CommandError
)

from sendit.settings import (
    BASE_DIR,
    MEDIA_ROOT
)
from django.conf import settings
import os

media_dir = os.path.join(BASE_DIR,MEDIA_ROOT)


def get_level():
    '''get level will return the python version for
    the user, corresponding to the watcher level
    '''
    import six
    if  six.PY3:
        return 0
    else:
        return -1

def get_daemon_kwargs():
    '''returns the stderr and stdout log file locations
    for the daemon based on the user configuration settings'''
    daemon_kwargs = {}
    try:
        daemon_kwargs['stdout'] = settings.INOTIFIER_DAEMON_STDOUT
    except AttributeError:
        pass

    try:
        daemon_kwargs['stderr'] = settings.INOTIFIER_DAEMON_STDERR
    except AttributeError:
        pass
    return daemon_kwargs
 

def is_watching():
    '''get_status turns the status of the watcher based on
    the active process read in from the pid file.
    '''
    pid_file = get_pid_file(quiet=True)
    if os.path.exists(pid_file):
        pid = int(open(pid_file).read())
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    else:
        return False    


def get_pid_file(quiet=False):
    '''get_pid_file will return a path to write the pid file,
    based on the configuration (user settings)
    '''
    try:
        pid_file = os.path.join(settings.BASE_DIR, 'watcher.pid')
    except AttributeError:
        pid_file = os.path.join("/tmp", "watcher.pid")
    if not quiet:
        if os.path.exists(pid_file):
            bot.debug("pid file is at %s" %(pid_file))
        else:
            bot.debug("pid file set to %s" %(pid_file))

    return pid_file


def get_notifier():
    '''get notifier will return a basic pyinotify watch manager
    based on the user's inotify watch paths in settings.
    if there is an error, returns None.
    '''
 
    try:
        import pyinotify
    except ImportError as e:
        bot.error("pyinotify is not installed.")
        return None

    level = get_level()
    wm = pyinotify.WatchManager()
    for path, mask, processor_cls in settings.INOTIFIER_WATCH_PATHS:
        cls_path = '.'.join(processor_cls.split('.')[0:-1])
        cls = processor_cls.split('.')[-1]
        mod = __import__(cls_path, globals(), locals(), [cls], level)
        Processor = getattr(mod, cls)
        wm.add_watch(path, mask, proc_fun=Processor())
        bot.debug("Adding watch on %s, processed by %s" %(path, processor_cls))

    notifier = pyinotify.Notifier(wm)
    return notifier

def verify_monitor_paths(return_message=False):
    '''verify monitor paths will check for monitor paths. If return_message is
    True, it returns the error message for another process to call/deal with, and None
    if all is good. If return message is False (default) it triggers the error.
    '''
    level = get_level()

    # Verify monitor_paths exists and processor classes can be imported
    for monitor, m, processor_cls in settings.INOTIFIER_WATCH_PATHS:
        if not os.path.exists(monitor):
            message="%s does not exist or you have insufficient permission" % monitor
            if return_message:
                return message
            return watcher_error(message=message,as_command=True)

        path = '.'.join(processor_cls.split('.')[0:-1])
        cls = processor_cls.split('.')[-1]
        try:
            mod = __import__(path, globals(), locals(), [cls], level)
            getattr(mod, cls)
        except ImportError as e:
            message='Cannot import event processor module: %s\n\n%s' %(path,e)
            if return_message:
                return message
            return watcher_error(message=message,as_command=True)

        except AttributeError:
            message='Cannot import event processor module: %s\n\n%s' %(path,e)
            if return_message:
                return message
            return watcher_error(message=message,as_command=True)

    return None


def watcher_error(message,as_command,request=None):
    '''watcher_error will take the setting as_command (True means the call is from the command line,
    false means it is from a web application view) and a request (from a web view) and either issue
    a command error, or return None response, optionally with a message, to the calling function
    '''
    if as_command:
        raise CommandError(message)
    else:
        watcher_message(message,request=None)
        return None


def watcher_message(message,request=None):
    '''if request is defined, a message is added.```
    '''
    if request is not None:
        messages.info(request,message) 
    else:
        bot.debug(message)
