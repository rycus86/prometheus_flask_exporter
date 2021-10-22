FROM python:3.8-alpine

ADD examples/gunicorn-multiprocess-109/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/gunicorn-multiprocess-109/server.py /var/flask/
WORKDIR /var/flask

ENV PROMETHEUS_MULTIPROC_DIR /tmp
ENV prometheus_multiproc_dir /tmp

CMD python /var/flask/server.py
