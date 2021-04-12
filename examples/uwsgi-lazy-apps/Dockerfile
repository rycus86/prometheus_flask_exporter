FROM python:3.8-alpine

RUN apk add --no-cache gcc musl-dev linux-headers

ADD examples/uwsgi-lazy-apps/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD . /tmp/latest
RUN pip install -e /tmp/latest --upgrade

ADD examples/uwsgi-lazy-apps/server.py /var/flask/
WORKDIR /var/flask

ENV PROMETHEUS_MULTIPROC_DIR /tmp

CMD uwsgi --http 0.0.0.0:4000 --module server:app --master --processes 4 --threads 2 --lazy-apps
