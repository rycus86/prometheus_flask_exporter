FROM python:3.7-alpine

RUN apk add --no-cache curl && pip install flask flask-restplus prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/restplus-default-metrics/server.py /var/flask/example.py
WORKDIR /var/flask

CMD python /var/flask/example.py
