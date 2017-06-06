# Django's Management
Django is primarily controlled via `manage.py`, the file sitting in the base of the repo. You will see it's use in several scripts such as [run_uwsgi.sh](../run_uwsgi.sh) to do things like `makemigrations` and `migrate`. These commands in particular are used to update the database (given any changes in a `models.py` files that define the tables. Generally, you can run commands to control user generation, database updates and dumps, and even your own custom. The commands that I use most often are `shell` and (sometimes) `dbshell` to immediately get an interactive shell for the python application (shell) or the postgres database (dbshell). With `--help` we can see everything that `manage.py` can do:

```bash
[auth]
    changepassword
    createsuperuser

[contenttypes]
    remove_stale_contenttypes

[django]
    check
    compilemessages
    createcachetable
    dbshell
    diffsettings
    dumpdata
    flush
    inspectdb
    loaddata
    makemessages
    makemigrations
    migrate
    opbeat
    sendtestemail
    shell
    showmigrations
    sqlflush
    sqlmigrate
    sqlsequencereset
    squashmigrations
    startapp
    startproject
    test
    testserver

[djcelery]
    celery
    celerybeat
    celerycam
    celeryd
    celeryd_detach
    celeryd_multi
    celerymon
    djcelerymon

[guardian]
    clean_orphan_obj_perms

[sessions]
    clearsessions

[sitemaps]
    ping_google

[staticfiles]
    collectstatic
    findstatic
    runserver

[watcher]
    watcher_start
    watcher_stop
```

For example, the last set of commands for the `watcher` we defined by adding a `management/commands` to our watcher application.
