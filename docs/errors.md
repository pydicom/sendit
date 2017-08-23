# Error Handling
We will discuss errors on four levels:

 - [Application Server Errors](#1-application-server-errors)
 - [Expected Errors](#2-expected-errors)
 - [Host Server Errors](#3-host-errors)
 - [Endpoint Errors](4-endpoint-error)

all in the context of the application `sendit`. Specifically we will review:

 - the kind of error
 - what it produces
 - how it is handled / logged
 - how it should be / is fixed

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
The `sendit` application uses many endpoints for obtaining identifiers, and uploading data. This is typically a hiccup in the remote, either if it is down, times out, or has an error parsing the request.

### What does it produce?
Endpoint errors usually send back responses in the `400` category to the client. Common ones are `400` (authentication required), `403` (Permission Denied or Forbidden) or `404` (oops, not found). Unfortuntely, timeouts don't send back anything at all, and it's the calling application that decides to hang up.

### How is it handled?
These kinds of errors are expected, and in fact quite reliable for some of the external APIs (for example, connecting to datastore almost always fails on the first attempt because it's run on Google Appspot). The `sendit` application deals with them by way of [exponential backoff](https://cloud.google.com/storage/docs/exponential-backoff) (retrying). This means that we keep trying the request with a longer delay between retries, up to some final number. This should deal with quirks and timeouts, and the error is only raised given that failure is consistent.

### How is it fixed?
This usually comes down to fixing the endpoint, meaning posting an issue on a board on Github, or in the case of an SOM API, contacting Stanford IRT.

# My Experience
 - The most common endpoint errors I've seen is with communicating with DASHER, mainly because we were figuring out formatting and setup, and since the early days of this it has worked very reliably.
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
