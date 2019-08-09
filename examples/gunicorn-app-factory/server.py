from app_setup import create_app, metrics

app = create_app()


@app.route('/test')
@metrics.counter('cnt_index', 'Counts invocations')
def index():
    return 'Hello world'


if __name__ == '__main__':
    app.run(debug=False, port=5000)
