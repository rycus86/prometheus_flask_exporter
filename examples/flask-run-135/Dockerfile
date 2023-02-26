FROM python:3.11-alpine

RUN apk add --no-cache curl \
  && pip install flask prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/flask-run-135 /var/flask
WORKDIR /var/flask

ENV DEBUG_METRICS true

CMD flask run --host 0.0.0.0 --port 4000 --debug --reload
