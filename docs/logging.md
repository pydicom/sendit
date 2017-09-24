# Logging

## Google Sheets
Sendit has a helper script that can be run with cron to update a Google Sheet at some
frequency with GB/day. Note that this assumes the following headers:

```
pipeline  | start_date  |  end_date   | duration (days)  | G/day Getit  |  G/day Sendit
1         |  9/11/2017  |  9/18/2017  |  7               | 300          | 77.0				
```

The titles are not important, but rather, the order and indexes. If you change this standard,
you should update the script [save_google_sheets.py](../scripts/save_google_sheets.py).

### 1. Set up Authentication
You will need to generate an [OAuth2 token](https://developers.google.com/sheets/api/guides/authorizing) for sheets on the server. This should be saved
to your server somewhere, the full file path accessible via the environment variable `GOOGLE_SHEETS_CREDENTIALS`.

```
GOOGLE_SHEETS_CREDENTIALS=/path/to/client_secrets.json
export GOOGLE_SHEETS_CREDENTIALS
```

### 1. Set up Cron
Running the script comes down to adding a line to crontab. This is NOT on the server (host) but
inside the image. Remember in the Dockerfile we installed crontab as follows:

```
# Install crontab to setup job
apt-get update && apt-get install -y gnome-schedule
```

You then want to edit the script [save_google_sheets.sh](../scripts/save_google_sheets.sh) to include
the specific sheet id. We take this approach (instead of adding it to crontab) so that if we need to
change the call, we don't need to edit crontab. Then we echo the line to crontab, and this command
will ensure it happens nightly at midnight

```
echo "0 0 * * * /bin/bash /code/scripts/save_google_sheets.sh" >> /code/cronjob
crontab /code/cronjob
```

The script uses the simple sheets client [provided by som-tools](https://github.com/vsoch/som/blob/master/som/api/google/sheets/client.py#L44), and adds an extra check to make sure column headers have not changed.
If a change is found, the new row isn't added (assuming the sheet has changed).

## Internal Logging
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

## Errors
You can inspect errors via the batch view [interface](interface.md) or from the command line. To look for errors across all batches:

```
python manage.py batch_logs
There are no batches with error.
```

and to select one or more specific batches based on their id (the number associated with the url in the browser, or the `batch.id` as a variable):

```
python manage.py batch_logs 1
DEBUG Inspecting for errors for 1 batch ids
There are no batches with error.

python manage.py batch_logs 1 2
DEBUG Inspecting for errors for 2 batch ids
There are no batches with error.
```


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
