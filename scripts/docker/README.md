# Send It Base Image

The sendit base image (with general requirements for Google Cloud and Django
is built locally and then used for the application. This is a record of how that was done.

First I created [pydicom/sendit-base](https://hub.docker.com/r/pydicom/sendit-base/) on dockerhub.
Then build the image, from the root of sendit:

```
cd scripts/Docker
docker build -t pydicom/sendit-base .
```

After successful build, you should then confirm the image was created:

```
docker images
REPOSITORY            TAG                 IMAGE ID            CREATED             SIZE
pydicom/sendit-base   latest              3d41520d4192        3 minutes ago       2.64GB
```

and then push

```
docker push pydicom/sendit-base
```
