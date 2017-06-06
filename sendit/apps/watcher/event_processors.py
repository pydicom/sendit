'''
Based on https://github.com/jwineinger/django-inotifier, added Celery usage

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

import pyinotify
from sendit.logger import bot
from sendit.apps.watcher import signals
from sendit.apps.main.tasks import import_dicomdir
import os

class DicomCelery(pyinotify.ProcessEvent):
    '''class which submits a celery job when a dicom directory is finished
    creation. This is determined based on not having any tmp extension
    '''
    def is_finished(self,path):
        extsep = os.path.extsep
        if os.path.isdir(path):
            ext = os.path.splitext(path)[1].strip(extsep)
            if ext.startswith('tmp'):
                return False
            return True
        else:
            return False    

    def process_IN_CREATE(self, event):
        '''Create should be called when the path is created (or modified)
        NOTE: if this isn't the case, use modify instead.
        '''
        if self.is_finished(event.pathname):
            bot.log("FINISHED: %s" %(event.pathname))

            # Here is the celery task to use
            import_dicomdir.apply_async(kwargs={"dicom_dir":event.pathname})
        else:
            bot.log("CREATED: %s" %(event.pathname))



class AllEventsPrinter(pyinotify.ProcessEvent):
    '''A class to print every event. 
       If logging is true, uses application logger
    '''
    def print_logger(self,message):
        bot.info(message)

    def println(self,message,logger=False):
        if logger is False:
            print(message)
        else:
            self.print_logger(message)

    def process_IN_ACCESS(self, event, logger=False):
        message = "IN ACCESS: %s" % event.pathname
        self.println(message,logger)

    def process_IN_ATTRIB(self, event, logger=False):
        message = "IN ATTRIB: %s" % event.pathname

    def process_IN_CLOSE_NOWRITE(self, event):
        message = "IN CLOSE NOWRITE: %s" % event.pathname
        self.println(message,logger)

    def process_IN_CLOSE_WRITE(self, event, logger=False):
        message = "IN CLOSE WRITE: %s" % event.pathname
        self.println(message,logger)

    def process_IN_CREATE(self, event, logger=False):
        message = "IN CREATE: %s" % event.pathname
        self.println(message,logger)

    def process_IN_DELETE(self, event, logger=False):
        message = "IN DELETE: %s" % event.pathname
        self.println(message,logger)

    def process_IN_DELETE_SELF(self, event, logger=False):
        message = "IN DELETE SELF: %s" % event.pathname
        self.println(message,logger)

    def process_IN_IGNORED(self, event, logger=False):
        message = "IN IGNORED: %s" % event.pathname
        self.println(message,logger)

    def process_IN_MODIFY(self, event, logger=False):
        message = "IN MODIFY: %s" % event.pathname
        self.println(message,logger)

    def process_IN_MOVE_SELF(self, event, logger=False):
        self.println(message,logger)
        message = "IN MOVE SELF: %s" % event.pathname

    def process_IN_MOVED_FROM(self, event, logger=False):
        message = "IN MOVED FROM: %s" % event.pathname
        self.println(message,logger)

    def process_IN_MOVED_TO(self, event, logger=False):
        message = "IN MOVED TO: %s" % event.pathname
        self.println(message,logger)

    def process_IN_OPEN(self, event, logger=False):
        message = "IN OPEN: %s" % event.pathname
        self.println(message,logger)

    def process_IN_Q_OVERFLOW(self, event, logger=False):
        message = "IN Q OVERFLOW: %s" % event.pathname
        self.println(message,logger)

    def process_IN_UNMOUNT(self, event, logger=False):
        message = "IN UNMOUNT: %s" % event.pathname
        self.println(message,logger)

# Below is from https://github.com/jwineinger/django-inotifier, added Celery usage

class AllEventsSignaler(pyinotify.ProcessEvent):
    '''Example class to signal on every event.
    '''
    def process_IN_ACCESS(self, event):
        signals.in_access.send(sender=self, event=event)

    def process_IN_ATTRIB(self, event):
        signals.in_attrib.send(sender=self, event=event)

    def process_IN_CLOSE_NOWRITE(self, event):
        signals.in_close_nowrite.send(sender=self, event=event)

    def process_IN_CLOSE_WRITE(self, event):
        signals.in_close_write.send(sender=self, event=event)

    def process_IN_CREATE(self, event):
        signals.in_create.send(sender=self, event=event)

    def process_IN_DELETE(self, event):
        signals.in_delete.send(sender=self, event=event)

    def process_IN_DELETE_SELF(self, event):
        signals.in_delete_self.send(sender=self, event=event)

    def process_IN_IGNORED(self, event):
        signals.in_ignored.send(sender=self, event=event)

    def process_IN_MODIFY(self, event):
        signals.in_modify.send(sender=self, event=event)

    def process_IN_MOVE_SELF(self, event):
        signals.in_move_self.send(sender=self, event=event)

    def process_IN_MOVED_FROM(self, event):
        signals.in_moved_from.send(sender=self, event=event)

    def process_IN_MOVED_TO(self, event):
        signals.in_moved_to.send(sender=self, event=event)

    def process_IN_OPEN(self, event):
        signals.in_open.send(sender=self, event=event)

    def process_IN_Q_OVERFLOW(self, event):
        signals.in_q_overflow.send(sender=self, event=event)

    def process_IN_UNMOUNT(self, event):
        signals.in_unmount.send(sender=self, event=event)


class CreateSignaler(pyinotify.ProcessEvent):
    '''Example class which only signals on create events.
    '''
    def process_IN_CREATE(self, event):
        signals.in_create.send(sender=self, event=event)




class CreateViaChunksSignaler(pyinotify.ProcessEvent):
    """
    A class which will signal the in_create event after a specific set of
    events has occurred for a file.  A file transfer agent may write partial
    chunks of a file to disk, and then move/rename that partial file to the
    final filename once all chunks are written. For this use, we cannot watch
    only the IN_CREATE event.  Observe the following event history:

    IN CREATE: /path/to/file/filename.part
    IN OPEN: /path/to/file/filename.part
    IN MODIFY: /path/to/file/filename.part
    IN MODIFY: /path/to/file/filename.part
    ...
    IN MODIFY: /path/to/file/filename.part
    IN CLOSE WRITE: /path/to/file/filename.part
    IN MOVED FROM: /path/to/file/filename.part
    IN MOVED TO: /path/to/file/filename

    Since we only want to signal when a new file is created, not just when
    a file is moved/renamed, we will use a state-machine to watch the stream
    of events, and only signal when the proper flow has been observed.
    Watching only the IN_MOVED_TO event would be insufficient because that
    could be triggered by someone manually renaming a file in the directory.

    To accomplish what we want, we will watch the IN_CREATE, IN_MOVED_FROM,
    and IN_MOVED_TO events. In the special case of moving a file when both the
    source and destination directories are being watched, the IN_MOVED_TO event
    will also have a src_pathname attribute to tell what the original filename
    was. Since we are only concerned with files created and moved within our
    watched directories, this allows us to track the state from the creation
    of the temporary .part file all the way through moving it to the final
    filename.
    """
    def my_init(self):
        """
        Setup a dict we can track .part files in.

        Also define the max_allowable_age for an entry in the tracking dict.
        """
        self.temp_files = {}

        from datetime import timedelta
        self.max_allowed_age = timedelta(hours=6)

    def sleepshop(self):
        """
        Remove values from the temp_files instance variable when they
        have reached an unacceptable age.
        """
        from datetime import datetime
        now = datetime.now()
        for filename, timestamp in dict(self.temp_files).iteritems():
            if now - timestamp > self.max_allowed_age:
                del self.temp_files[filename]

    def process_IN_CREATE(self, event):
        """
        The IN_CREATE event will be the creation of the .part temporary file.

        So instead of sending the in_create signal now, we merely start to
        track the state of this temporary file. We store a current timestamp
        in the tracking dict so we can cull any values which have been around
        too long.
        """
        self.sleepshop()

        if event.pathname.endswith('.part'):
            import datetime
            self.temp_files[event.pathname] = datetime.datetime.now()

    def process_IN_MOVED_TO(self, event):
        """
        If both the source and destination directories are being watched by
        pyinotify, then this event will have a value in src_pathname. This
        value will be the .part filename and event.pathname will be the final
        filename.

        Note: IN_MOVED_FROM must be watched as well for src_pathname to be
        set.
        """
        if event.src_pathname and event.src_pathname in self.temp_files:
            del self.temp_files[event.src_pathname]
            signals.in_create.send(sender=self, event=event)

        self.sleepshop()
