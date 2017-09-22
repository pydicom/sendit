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

## 1. Adding Models to Database
Each dicom file is read, and during reading, added as an `Image` object to the database. The study and session are also extracted from the header, and these are added as `Study` and `Session` objects, respectively. The Series and Study Ids are extracted from these fields in the dicom header, for each file separately:

```
StudyID
SeriesInstanceUID
```

If we run into some case where the fields are not defined, I have put a check that will use the folder name instead, prefixed with `series_` or `study_`. For example, a folder `ST-1234` with a dicom missing header information would have study and session `series_ST-1234` and study `study_ST-1234`. 


## 2. Saving Dicoms
All files in the folder are assumed to be dicom, as it is the case the extensions may vary. If a file is attempted to be read as dicom fails, a warning is issued and the file skipped, but the process continued. The file is not removed, in case inspection is warranted later (is this how we want it?) (some notification?)

The dicom file itself, when saved to the model, is saved with the application's media at `/images`. 

## 3. Finishing Batch
All the images found in a folder are considered to be a "batch," and when all files for a batch have been added, the function fires off the list to be anonymized. If there were no files in the batch, the function is not fired.
