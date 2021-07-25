#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker logs uwsgi-lazy-apps-sample
    docker rm -f uwsgi-lazy-apps-sample > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t uwsgi-lazy-apps-sample ../../. > /dev/null || _fail
docker run -d --name uwsgi-lazy-apps-sample -p 4000:4000 uwsgi-lazy-apps-sample > /dev/null || _fail

echo 'Waiting for uwsgi [lazy apps] to start...'

for _ in $(seq 1 10); do
    PROCESS_COUNT=$(docker exec uwsgi-lazy-apps-sample sh -c 'pgrep -a uwsgi | wc -l')
    if [ $PROCESS_COUNT -ge 5 ]; then
        break
    fi
done

echo 'Starting the tests...'

for _ in $(seq 1 10); do
    curl -s http://localhost:4000/test > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s http://localhost:4000/metrics \
  | grep 'flask_http_request_duration_seconds_count{method="GET",path="/test",status="200"} 10.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f uwsgi-lazy-apps-sample > /dev/null
echo 'OK, all done'