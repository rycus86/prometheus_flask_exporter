FROM python:3.7-alpine

RUN apk add --no-cache curl && pip install flask prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/reload/reload_example.py /var/flask/example.py
WORKDIR /var/flask

ENV DEBUG_METRICS 1

CMD python /var/flask/example.py
