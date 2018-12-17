#!/bin/bash

cd "$(dirname "$0")"

_fail() {
    docker rm -f reload-sample > /dev/null 2>&1
    exit 1
}

docker build -f Dockerfile -t reload-sample ../../. > /dev/null || _fail
docker run -d --name reload-sample -p 4000:4000 reload-sample > /dev/null || _fail

echo 'Waiting for the server to start...'

for _ in $(seq 1 10); do
    if curl -fs http://localhost:4000/ping > /dev/null; then
        break
    else
        sleep 0.2
    fi
done

echo 'Starting the initial tests...'

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

echo 'Changing the server...'
docker exec -it reload-sample sed -i "s#@app.route('/test')#@app.route('/changed')#" /var/flask/example.py
docker exec -it reload-sample sed -i "s#@app.route('/ping')#@app.route('/ping2')#" /var/flask/example.py

echo 'Waiting for the server to apply the changes...'

for _ in $(seq 1 10); do
    if curl -fs http://localhost:4000/ping2 > /dev/null; then
        break
    else
        sleep 0.2
    fi
done

echo 'Starting the changed tests...'

for _ in $(seq 1 12); do
    curl -s http://localhost:4000/changed > /dev/null
    if [ "$?" != "0" ]; then
        echo 'Failed to request the test endpoint'
        _fail
    fi
done

curl -s http://localhost:4000/metrics \
  | grep 'flask_http_request_duration_seconds_count{method="GET",path="/changed",status="200"} 12.0' \
  > /dev/null

if [ "$?" != "0" ]; then
    echo 'The expected metrics are not found'
    _fail
fi

docker rm -f reload-sample > /dev/null
echo 'OK, all done'
