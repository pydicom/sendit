# Logging
The application has a simple logger, defined at [../sendit/logger.py](logger.py). To use it, you import as follows:

```
from sendit.logger import bot
```

and then issue messages at whatever level is suitable for the message:

```
bot.abort("This is an abort message")
bot.error("This is a debug message")
bot.warning("This is a warning message")
bot.log("This is a log message")

bot.log("This is a debug message")
bot.info("This is an info message")
bot.verbose("This is regular verbose")
bot.verbose2("This is level 2 verbose")
bot.verbose3("This is level 3 verbose")
bot.debug("This is a debug message")
```

All logger commands will print the level by default, except for info, which looks like a message to the console (usually for the user), and except for quiet, which isn't a level that is used in code, but a level the user can specify to not print anything, ever.


## Settings
By default, the logger will have `debug` mode, which coincides with a level of `5`. You can customize this level at any point by setting the environment variable `SENDIT_MESSAGELEVEL`. In your `secrets.py` this might look like this:


```
import os
os.environ['SENDIT_MESSAGELEVEL'] = 2
```

The levels supported include the following:

 - ABRT = -4
 - ERROR = -3
 - WARNING = -2
 - LOG = -1
 - QUIET = 0
 - INFO = 1
 - VERBOSE  = 2
 - VERBOSE2 = 3
 - VERBOSE3 = 4
 - DEBUG = 5


The logger can write it's output to file, or do something else, but isn't configured to do anything other than the above currently.
