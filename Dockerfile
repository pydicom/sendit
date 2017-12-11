FROM pydicom/sendit-base

# update deid
WORKDIR /opt
RUN git clone -b development https://github.com/pydicom/deid
WORKDIR /opt/deid
RUN python setup.py install

# som
WORKDIR /opt
RUN git clone -b add/bigquery https://github.com/vsoch/som
WORKDIR /opt/som
RUN python setup.py install

WORKDIR /code
ADD . /code/
CMD /code/run_uwsgi.sh

EXPOSE 3031
