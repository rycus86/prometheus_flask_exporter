FROM python:3.7-alpine

RUN pip install flask prometheus_flask_exporter pytest

ENV prometheus_multiproc_dir=/tmp
ENV PYTHONPATH=/data

ADD . /data
WORKDIR /data
