# Error Handling
We will discuss errors on four levels:

 - [Application Server Errors](#1-application-server-errors)
 - [Expected Errors](#2-expected-errors)
 - [Host Server Errors](#3-host-errors)
 - [Endpoint Errors](#4-endpoint-error)

all in the context of the application `sendit`. Specifically we will review:

 - the kind of error
 - what it produces
 - how it is handled / logged
 - how it should be / is fixed

and finish with [Specific Error Handling](#specific-error-handling) to discuss how the application deals with errors at each step of the pipeline.

## 1. Application Server Errors

### What kind of error is this?
A server error is typically a problem or bug in the code itself (e.g., an indentation error, a missing module import) or a runtime error that was not anticipated (e.g., a corrupt header field, unexpected object provided as input, etc.). Since `sendit` includes a uwsgi driven application, redis database with celery worker, and nginx server, a server error in this context typically is an issue with the application at runtime, and more rarely an issue with the database. This should not be confused with some error on the host (below) which is technically also a server.

### What does it produce?
Left unhandled, a server error will send a response of `500` to the client, meaning that an exception was triggered in the application. This is the most dangerous kind of error, because they can go un-noticed. 

### How is it handled?
To deal with this, the `sendit` application is registered with the researchapps organization (owned by @vsoch) on [opbeat](https://opbeat.com/researchapps/sendit/). Any server error relevant to the application that is not handled notifies the application manager (@vsoch) immediately by email, and text message, for the quickest possible fix. The stacktrace is provided. Additionally, the Docker image logs can be easily accessed to see messages from the worker, for example:

```
docker-compose logs -f worker
worker_1  | [2017-08-22 20:39:53,992: INFO/MainProcess] Task sendit.apps.main.tasks.get.import_dicomdir[5bd31e56-559a-4881-9b46-dfafaaa1ff79] succeeded in 0.6935751209966838s: None
worker_1  | [2017-08-22 20:39:53,995: DEBUG/MainProcess] Task accepted: sendit.apps.main.tasks.get.import_dicomdir[94b6526e-45d9-474c-9bb5-fc0a91ff8051] pid:9
worker_1  | DEBUG Importing /data/677777, found 36 .dcm files
worker_1  | ERROR 1.2.840.XXXXXXXXXXXXX954.943379.1.1 is not CT/MR, found US skipping
```

### How is it fixed?
These errors typically require an investigation (debugging), and then update to the application code to deal with the occurrence for next time. Opbeat keeps a log of the specific error types, so if it is flagged as "fixed" and then re-occurs, we will know it wasn't really fixed.


## 2. Expected Errors

### What kind of error is this?
For many of the examples above, we can actually anticipate them. This is the typical "try", "catch" and "except" loop that is common regardless of programming language.

### What does it produce?
When we catch an error in `sendit`, we log the exact error, the relevant object (a batch or image) and flag the batch as having an error. This log is maintained in the database, meaning that we query the database to see it. Specifically, each batch (a set of images associated with an Accession number) has a JSONfield in its database model that will store errors:

```
batch.logs['errors']
{'errors': ['1.2.84.0XXXXXXXXXXXXXXXXXX.2.10 is not CT/MR, found PR skipping', 
            '1.2.84.0XXXXXXXXXXXXXXXXXX2.8082.1415723274472.2.8 is not CT/MR, found PR skipping']}
```

There is also a boolean, and associated status that is changed at the onset of any error, and helps the user to index more easily:

```
Batch.objects.filter(has_error=True)
Batch.objects.filter(status='ERROR')
```

The application was originally configured to remove all images after a batch completes successfully, and keep them around given an error, however given the small amount of space and huge amount of images, we are currently over-riding this and deleting all intermediate images. To be clear, these images that are deleted are NOT the original obtained from the C-MOVE, but copies made for the application. Given that we are flagging many images (anything with burned in annotation / not MR or CT) it's more likely that a batch would be kept, and the server would run out of space and alarm. However, the database logs are *not* cleared, so we can go back and re-copy the errored images, clean pixels etc, and re-run the pipeline.

### How is it handled?
The majority of our "errors" are currently data that don't pass filters (meaning they have potentially PHI in the pixels and we won't continue processing). We aren't dealing with any of these now other than to keep log of them, and address when we have a solution.

### How is it fixed?
Ultimately, we want the "pixel cleaning" tool tested and integrated into the pipeline, so it's not flagged as an error, period.


## 3. Host Errors
The application is being hosted on a server provided by Stanford IRT. Given some kind of restart or error, `sendit` would also need to be restarted. I (@vsoch) don't know how these servers are managed, or how notifications are kept, so I cannot comment on how/if I will be notified, but I would hope that I would!


## 4. Endpoint Error

### What kind of error is this?
The `sendit` application uses many endpoints for obtaining identifiers, and uploading data. This is typically a hiccup in the remote, either if it is down, times out, or has an error parsing the request. When we talk about these kinds of errors, we should first know about the typical client to service relationship:

```
[ client ] -- makes request --> [ service provider receives request ] --> [ valid format? --> authenticated? --> authorized? ] --> [ response ]
```

In the example above, we might have `sendit` as a client, and `DASHER` as the provider. Communication between the two is done by way of [requests](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol#Request_methods), and then different [status codes](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes) sent back with any response. Generally, errors in the `200` family mean success, `300` is some kind of redirect / move, `400` is a client error, and `500` is a service provider error.

### What does it produce?
Endpoint errors usually send back responses in the `400` category to the client. Common ones are `401` (authentication required), `403` (Permission Denied or Forbidden) or `404` (oops, not found). `400` means "bad request" and some providers choose to return this as exposing a more specific error could be a security risk. Unfortuntely, timeouts don't send back anything at all, and it's the calling application that decides to hang up.

### How is it handled?
These kinds of errors are expected, and in fact quite reliable for some of the external APIs (for example, connecting to datastore almost always fails on the first attempt because it's run on Google Appspot). The `sendit` application deals with them by way of [exponential backoff](https://cloud.google.com/storage/docs/exponential-backoff) (retrying). This means that we keep trying the request with a longer delay between retries, up to some final number. This should deal with quirks and timeouts, and the error is only raised given that failure is consistent.

### How is it fixed?
This usually comes down to fixing the endpoint, meaning posting an issue on a board on Github, or in the case of an SOM API, contacting Stanford IRT.

# My Experience
 - The most common endpoint errors I've seen is with communicating with DASHER, mainly because we were figuring out formatting and setup, and since the early days of this it has worked very reliably. I would say our early troubles had to do with sending too many requests (representing every dicom image as an item). Once we chose to get just two identifiers (suid) per batch (for the patient, and study, respectively) the function was much improved. 
 - Google Cloud pretty reliably has timeouts and hiccups, as do most web applications. The exponential backoff strategy has (thus far) worked very well.
 - The most common error I've come across that is most significant is running out of room for images on the server. We are limited in the number of batches that can be processed because of it. Since it's the case that some batches can have thousands and some a few hundred, it isn't reliable to try and maximize the number processed at once. I've had a few times when 50 batches at once works ok (they are run as asynchronous tasks) but I've also had times when a server alarm went off because too many files were copied and room ran out. I've found N=25 to work reasonably given these constaints.
 - There is no "testing ground" between development and deployment, so typically I will see errors when I am interactively testing a function, and then adjust the software locally, push to Github, and pull to the server. These errors are sometimes logged on Opbeat, but more commonly appear in my console. 
 - The biggest trouble comes with needing to rebuild the image, as a change in one dependency can mean non-functioning of the application. In the long run we will want to have the image pre-built and used, and versions of software specified in detail.

## Summary
In summary:

 - `host machine`: I (@vsoch) don't know about errors on the host, as I don't manage the machine, but would like notification if the application needs attention. 
 - `server error`: We are notified immediately of unexpected errors from the application itself, and the error will be (granted that I'm not sleeping) fixed promptly.
 - `endpoint error`: Is protected greatly with exponential backoff. The fallback to complete failure of an endpoint is the `server error` above and notification.
 - `expected error`: can be viewed and managed on demand.

This isn't a perfect setup, but it's robust enough to be a good start :)


# Metrics

As an addition to the error logs, `sendit` keeps timing metrics for each batch:

```
batch.qa
{'StudyDate': {'20120809': 1619}, 'StartTime': 1503438295.6603007, 'ElapsedTime': 808.8025045394897, 'SizeBytes': 855393142, 'FinishTime': 1503439104.4628053}
```

So we can (hopefully) calculate some kind of MB/hour metric.


# Suggestions
The current implementation is reasonable for now, but I would make the following recommendations for moving forward:

 - *Testing*: The components of the application ([deid](https://www.github.com/pydicom/deid), [som](https://www.github.com/vsoch/som), and [pydicom](https://www.github.com/pydicom/pydicom)) carry their own tests, but missing is tests for the sendit application itself. A proper setup should have a testing environment (whether a separate testing server for manual testing or automated testing) to be sure that nothing goes into development that has bugs. Up to this point I've (@vsoch) have just been very careful to test everything and walk through steps manually, and this needs to be improved. If this application is to be moved to a cloud resource, and possibly scaled, a continuous integration --> deployment setup would be very ideal.

# Specific Error Handling

## Dicom Import
Dicom import is when we find a folder in the application data folder, copy it to the application storage, and start reading in files to a batch for processing.

1. `A dicom file is corrupt`: At initial read, we must look at the header to look for indicators of burned in pixels. This is an initial sanity check that the dicom file is valid, meaning the header is well formed. We use a `force` argument to read files that might have erroneous private tags (I've seen this is common with some files if a machine later adds some kind of header data / modifies the header in a way that it would be determined invalid by the dicom standard) so most files we are able to read, and thus move forward to provide to the researcher. The specific errors we check for to accept (and then log) are `InvalidDicomError`, `KeyError`, and then a base `Exception`. Lots of the specific image skipped are kept in all cases.

2. `dicom directory is not found`: There could be some race condition where the directory is found, and then deleted before the task starts. We check for this, and pass the error with a warning log (not to the database, just the terminal output) and move on. A batch not found or read in has no folder or way to represent it in the database.

3. `study id is different between dicom files`: We check the study identifier for each dicom file, and at the end of import, make sure that we only have 1. If there is more than 1, the error is logged to the application.

4. `the pixel has burned in identifiers`: a flag of "BurnedInAnnotation" issues a warning and skips adding an image to the batch, as it is an indicator of PHI. We log this to the application (database as a warning).

5. `modality not in CT or MR`: we found a lot of PHI in images other than MR/CT (eg, Ultrasound, Angiography) and so any image with `ImageType` field with something other than these two is treated as an item in 4 - logged and not added to the batch.

6. `images EMPTY`: in the case that no images pass filters, the count will be 0, and we set the batch status to `EMPTY` and move on to the next. This I've found to be a common issue given that many images are skipped due to potential PHI, and some of the batch folders are rather small. For example:

```
worker_1  | DEBUG Importing /data/XXXXXX, found 9 .dcm files
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX has burned pixel annotation, skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING 2.25.XXXXXXXXXXXXX is not CT/MR, found XA skipping
worker_1  | WARNING XXXXXXXXXXXXX is flagged EMPTY, no images pass filter
worker_1  | DEBUG Starting deid pipeline for 1 folders
worker_1  | [2017-08-23 05:54:29,430: INFO/MainProcess] Received task: sendit.apps.main.tasks.get.import_dicomdir[ec480057-9940-46b9-bfca-fb40eab343b0]
```

## Get Identifiers (DASHER)

1. `Error with DASHER`: An error in DASHER, in that no anonymization occurs, MUST be raised and stop processing. Thus, we don't try to catch anything at the moment. 

2. Malformed response from `DASHER`: In the case that results are not delivered with suid identifiers, we typically will get a response missing the 'results' header. In this case, the batch is flagged with an error. I also chose to stop processing here, because I'd want to investigate this issue. Arguably this could (and should) be better handled if/when I get a better sense of different error responses that might come back. So far, I've only seen one trigger of an error at this step, which likely was some issue with the VPN of the host.


## Replace Identifiers
This task will take the data from Dasher, and parse the data to replace identifiers. It is arguably the most important step of the pipeline, and my preference right now is to catch any error, stop, and then investigate.

1. `any error in replacement`: will return None, log the error, and stop the pipeline for manual investigation. Thus far, I haven't seen any issues here.


## Upload to Storage
This step will take a set of anonymized, filtered, and renamed images, compress them, and upload to storage.

1. `batch or batch_ids not found`: I'm not sure how this might happen, but you never know. If a previously submit task is missing the database information, the pipeline logs an error and stops. This is something else I'd want to know about it, because it shouldn't logically happen unless something bad happens like the postgres database goes down, but the redis does not (and still thinks it is there).


2. `compressed file missing images, or has none`: I saw some early cases of an image having an error when attempted addition to the .tar.gz, and I'm not sure what the cause is other than perhaps a file is corrupt. To maximize data availability, we catch `FileNotFoundError` for each attempted addition, and count the number of images added. If the count is == 0, the upload is cancelled and the error is logged. The pipeline moves on to the next batch.

3. `timeout / other API error`: right now this is handled by exponential backoff, and I haven't seen any issues. If this fails, the fallback is raising the error to the server, and notification.

4. `token refresh`: it's pretty standard to need to refresh tokens, and the Google python APIs handle this, for example:

```
worker_1  | LOG Uploading IR1c1d_20150525_IR661B26.tar.gz with 1848 images to Google Storage irlhs-dicom
worker_1  | [2017-08-23 05:51:37,262: INFO/Worker-1] URL being requested: GET https://www.googleapis.com/storage/v1/b/irlhs-dicom?alt=json
worker_1  | [2017-08-23 05:51:37,262: INFO/Worker-1] Attempting refresh to obtain initial access_token
...
worker_1  | [2017-08-23 05:51:37,303: INFO/Worker-1] Refreshing access_token
worker_1  | [2017-08-23 05:51:37,656: DEBUG/Worker-1] Making request: POST https://accounts.google.com/o/oauth2/token
worker_1  | [2017-08-23 05:51:37,657: DEBUG/Worker-1] Starting new HTTPS connection (1): accounts.google.com
worker_1  | [2017-08-23 05:51:37,752: DEBUG/Worker-1] https://accounts.google.com:443 "POST /o/oauth2/token HTTP/1.1" 200 None
worker_1  | [2017-08-23 05:51:38,721: INFO/Worker-1] URL being requested: POST https://www.googleapis.com/upload/storage/v1/b/irlhs-dicom/o?predefinedAcl=projectPrivate&uploadType=resumable&alt=json

```
