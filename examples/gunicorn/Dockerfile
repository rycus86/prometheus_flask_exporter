FROM python:3.7-alpine

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD server.py config.py /var/flask/
WORKDIR /var/flask

ENV prometheus_multiproc_dir /tmp
ENV METRICS_PORT 9200

CMD gunicorn -c config.py -w 4 -b 0.0.0.0:4000 server:app
