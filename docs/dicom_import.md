# Pre Dicom Import
There is a process running on the server that uses based `dcm4che` command line tools to issue a `C-MOVE` command to download datasets to the application `/data` folder. The script that runs might look something like this:

```bash
#!/bin/bash

CALLINGAE=calling-ae-title
PORT=111.11.111.11
TARGETAE=ONION@22.222.22.22:4444
NUM=L123456
BASE=/opt/sendit/data

mkdir $BASE/$NUM.tmp
dcmqr -L$CALLINGAE@$PORT $TARGETAE -qAccessionNumber=$NUM -cmove $CALLINGAE -cstoredest=$BASE/$NUM.tmp
mv $BASE/$NUM.tmp $BASE/$NUM
```

In the above, we see that `dcmqr` is used to call `C-MOVE` to dump a bunch of dicoms into a folder named based on a number, which is likely an accession number as it is a common query. The last line of the script renames the `*.tmp` folder by removing the extension, which then notifies the watcher that the folder is done.

# Dicom Import
When the [watcher](watcher.md) detects a `FINISHED` session directory in the folder being watched (`/data` in the container, mapping to `data` in the application base folder on the host), the process of importing the images into the database is started. This means the following steps:

 - although the name of the folder for the series must by default be unique compared to others around it, the series id itself is extracted from the dicom files. Thus, for the actual metadata, the folder name is irrelevant
 - all files in the folder are assumed to be dicom, as it is the case the extensions may vary. If a file is attempted to be read as dicom fails, a warning is issued and the file skipped, but the process continued.
 - each dicom file is read, and during reading, added as an `Image` object to the database. The study and session are also extracted from the header, and these are added as `Study` and `Session` objects, respectively.
 - adding a file to the database means replicating it in the database (media) storage. This isn't completely necessary, but it allows for deletion of the folder in `/data` so a human observer can more easily see processing occurring on the filesystem.
 - all the images found in a folder are considered to be a "batch," and when all files for a batch have been added, the function fires off the list to be deidentified.
