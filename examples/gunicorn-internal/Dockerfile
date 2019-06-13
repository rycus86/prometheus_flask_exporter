FROM python:3.7-alpine

ADD examples/gunicorn-internal/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/gunicorn-internal/server.py examples/gunicorn-internal/config.py /var/flask/
WORKDIR /var/flask

ENV prometheus_multiproc_dir /tmp

CMD gunicorn -c config.py -w 4 -b 0.0.0.0:4000 server:app
