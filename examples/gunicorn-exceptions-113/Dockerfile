FROM python:3.8-alpine

ADD examples/gunicorn-exceptions-113/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/gunicorn-exceptions-113/server.py examples/gunicorn-exceptions-113/config.py /var/flask/
WORKDIR /var/flask

ENV PROMETHEUS_MULTIPROC_DIR /tmp

CMD gunicorn -c config.py -w 4 -b 0.0.0.0:4000 server
