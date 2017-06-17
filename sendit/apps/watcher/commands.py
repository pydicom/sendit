'''
commands for the watcher. If submit from management, will output a CommandError
                          if running from management, set as_command=True

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

:: note
    For these functions, if as_command is
    True, we assume this is coming from the terimal (and not web interface)
    If False, errors are sent back to the calling user via messages in the 
    request. If there is an error, the status returned is None, and a message
    is returned to the user to indicate why. If successful, and call is from
    the application, the notifier is returned.

'''
from django.contrib import messages
from sendit.logger import bot
from sendit.apps.watcher.utils import (
    get_daemon_kwargs,
    get_notifier,
    get_pid_file,
    verify_monitor_paths,
    watcher_error,
    watcher_message
)

from django.conf import settings
import os
import time


def start_watcher(request=None,as_command=False):
    '''start the watcher, if the process is not started.
    '''

    # Verify INOTIFIER_WATCH_PATHS is defined and non-empty
    try:
        assert settings.INOTIFIER_WATCH_PATHS
    except (AttributeError, AssertionError):
        return watcher_error(message="Missing/empty settings/watcher.py INOTIFY_WATCH_PATHS",
                             as_command=as_command,
                             request=request)


    # Verify INOTIFIER_WATCH_PATHS is properly formatted
    try:
        length_3 = [len(tup) == 3 for tup in settings.INOTIFIER_WATCH_PATHS]
        assert all(length_3)
    except AssertionError:
        message = '''setting INOTIFIER_WATCH_PATHS should be an iterable of
                 3-tuples of the form [ ("/path1/", <pyinotify event mask>, <processor cls>), ]'''
        return watcher_error(message=message,
                             as_command=as_command,
                             request=request)


    error_message = verify_monitor_paths(return_message=True)
    if error_message is not None:
        return watcher_error(message=error_message,
                             as_command=as_command,
                             request=request)


    # Setup watches using pyinotify
    notifier = get_notifier()

    # Error with import or setup returns None
    if notifier is None:
        return watcher_error(message="Cannot import pyinotify.",
                             as_command=as_command,
                             request=request)

    pid_file = get_pid_file()

    # Daemonize, killing any existing process specified in pid file
    daemon_kwargs = get_daemon_kwargs()
    notifier.loop(daemonize=True, pid_file=pid_file, **daemon_kwargs)
    watcher_message(message="Dicom watching has been started.",request=request)



def stop_watcher(request=None,as_command=False):
    '''stop the watcher, if the process is started. Returns True
    if success.
    '''

    pid_file = get_pid_file()

    if os.path.exists(pid_file):
        pid = int(open(pid_file).read())

        import signal
        try:
            os.kill(pid, signal.SIGHUP)
        except OSError:
            os.remove(pid_file)
            return watcher_error(message="No process with id %d. Cleaned up pid file." % (pid),
                                 as_command=as_command,
                                 request=request)
        time.sleep(2)

        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

        os.remove(pid_file)
        watcher_message(message="Dicom watching has been stopped.",request=request)
    else:
        return watcher_error(message="No pid file exists. The watched is not started.",
                             as_command=as_command,
                             request=request)
    if not as_command:
        return True
