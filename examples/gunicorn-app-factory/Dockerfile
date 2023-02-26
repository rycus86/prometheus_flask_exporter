FROM python:3.11-alpine

ADD examples/gunicorn-app-factory/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/gunicorn-app-factory/server.py \
    examples/gunicorn-app-factory/app_setup.py \
    examples/gunicorn-app-factory/config.py \
    /var/flask/
WORKDIR /var/flask

ENV PROMETHEUS_MULTIPROC_DIR /tmp
ENV prometheus_multiproc_dir /tmp

CMD gunicorn -c config.py -w 4 -b 0.0.0.0:4000 server:app
