import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
LOG_DIR = os.path.join(BASE_DIR,'logs')

def generate_watch_paths():
    '''Don't import pyinotify directly into settings
    '''
    import pyinotify
    return (
       (  os.path.join('/data'),
          pyinotify.ALL_EVENTS,
         'sendit.apps.watcher.event_processors.DicomCelery',
       ),
    )

# Logging
INOTIFIER_WATCH_PATHS = generate_watch_paths()
INOTIFIER_DAEMON_STDOUT = os.path.join(LOG_DIR,'watcher.out')
INOTIFIER_DAEMON_STDERR = os.path.join(LOG_DIR,'watcher.err')
