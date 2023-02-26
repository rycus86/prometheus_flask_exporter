FROM python:3.11-alpine

RUN apk add --no-cache curl \
  && pip install flask Flask-HTTPAuth prometheus_client

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/flask-httpauth /var/flask
WORKDIR /var/flask

CMD python /var/flask/httpauth_example.py
