#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker logs gunicorn-sample
    docker rm -f gunicorn-sample > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t gunicorn-sample ../../. > /dev/null || _fail
docker run -d --name gunicorn-sample -p 9200:9200 gunicorn-sample > /dev/null || _fail

echo 'Waiting for Gunicorn to start...'

for _ in $(seq 1 10); do
    PROCESS_COUNT=$(docker exec gunicorn-sample sh -c 'pgrep -a gunicorn | wc -l')
    if [ $PROCESS_COUNT -ge 5 ]; then
        break
    fi
done

echo 'Starting the tests...'

for _ in $(seq 1 10); do
    curl -s http://localhost:9200/test > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s http://localhost:9200/metrics \
  | grep -E 'flask_http_request_total\{.*status="200".*} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

NUMBER_OF_FLASK_EXPORTER_INFO_METRICS=$(curl -s http://localhost:9200/metrics \
  | grep 'flask_exporter_info{' \
  | wc -l)

if [ "$NUMBER_OF_FLASK_EXPORTER_INFO_METRICS" -lt "1" ] || [ "$NUMBER_OF_FLASK_EXPORTER_INFO_METRICS" -gt 2 ]; then
    echo "Unexpected number of info metrics: $NUMBER_OF_FLASK_EXPORTER_INFO_METRICS"
    _fail
fi

docker rm -f gunicorn-sample > /dev/null
echo 'OK, all done'