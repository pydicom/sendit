# Watcher
The watcher is implemented as a [pyinotify daemon](https://github.com/seb-m/pyinotify/wiki) that is controlled via the [manage.py](../manage.py). If you are more interested about how this module works, it uses [inotify](https://pypi.python.org/pypi/inotify) that comes from the linux Kernel. Specifically, this means that you can start and stop the daemon with the following commands (from inside the Docker image):

```
python manage.py start_watcher
python manage.py stop_watcher

```

The functions are stored in the [management/commands](../sendit/apps/watcher/management/commands) folder within the watcher app. This organization is standard for adding a command to `manage.py`, and is done by way of instantiating Django's [BaseCommand](https://docs.djangoproject.com/en/1.11/howto/custom-management-commands/#django.core.management.BaseCommand):

```
from django.core.management.base import (
    BaseCommand, 
    CommandError
)
```

For better understanding, you can look at the code itself, for each of [watcher_start.py](../sendit/apps/watcher/management/commands/watcher_start.py) and [watcher_stop.py](../sendit/apps/watcher/management/commands/watcher_stop.py).
 
## Basic Workflow
The basic workflow of the watcher is the following:

1. The user starts the daemon.
2. The process id is stored at `watcher.pid` in the application base folder at `/code`. Generally, we always check for this file first to stop a running process, stop an old process, or write a new pid.
3. Logs for error (watcher.err) and output (watcher.out) are written under [logs](../logs). We likely (might?) want to clear / update these every so often, in case they get really big.
4. The daemon responds to all events within the `/data` folder of the application. When this happens, we trigger a function that:
   - checks for a complete series folder
   - if complete, adds to database and starts processing

