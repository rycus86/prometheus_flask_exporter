import os
import sys

from flask import Flask

from prometheus_flask_exporter import ConnexionPrometheusMetrics
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_flask_exporter import RESTfulPrometheusMetrics
from prometheus_flask_exporter.multiprocess import GunicornInternalPrometheusMetrics
from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
from prometheus_flask_exporter.multiprocess import MultiprocessPrometheusMetrics
from prometheus_flask_exporter.multiprocess import UWsgiPrometheusMetrics

from unittest_helper import BaseTestCase


class ExtensionsTest(BaseTestCase):
    def setUp(self):
        super(ExtensionsTest, self).setUp()

        if 'PROMETHEUS_MULTIPROC_DIR' not in os.environ:
            os.environ['PROMETHEUS_MULTIPROC_DIR'] = '/tmp'
            self._multiproc_dir_added = True
        elif 'prometheus_multiproc_dir' not in os.environ:
            os.environ['prometheus_multiproc_dir'] = '/tmp'
            self._multiproc_dir_added = True
        else:
            self._multiproc_dir_added = False

        if sys.version_info.major < 3:
            # some integrations don't work on Python 2 anymore:
            # - ConnexionPrometheusMetrics
            # - MultiprocessPrometheusMetrics
            self._all_extensions = [
                PrometheusMetrics, RESTfulPrometheusMetrics,
                UWsgiPrometheusMetrics, GunicornPrometheusMetrics, GunicornInternalPrometheusMetrics
            ]
        else:
            self._all_extensions = [
                PrometheusMetrics, RESTfulPrometheusMetrics, ConnexionPrometheusMetrics,
                MultiprocessPrometheusMetrics, UWsgiPrometheusMetrics,
                GunicornPrometheusMetrics, GunicornInternalPrometheusMetrics
            ]

    def tearDown(self):
        if self._multiproc_dir_added:
            if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
                del os.environ['PROMETHEUS_MULTIPROC_DIR']
            if os.environ.get('prometheus_multiproc_dir'):
                del os.environ['prometheus_multiproc_dir']

    def test_with_defaults(self):
        for extension_type in self._all_extensions:
            try:
                app = Flask(__name__)
                app.testing = True
                flask_app = app

                kwargs = {}

                if extension_type is ConnexionPrometheusMetrics:
                    class WrappedApp(object):
                        def __init__(self, app):
                            self.app = app

                    # ConnexionPrometheusMetrics wraps this in its own type of app
                    app = WrappedApp(app)
                elif extension_type is RESTfulPrometheusMetrics:
                    # RESTfulPrometheusMetrics has one additional positional argument
                    kwargs = {'api': None}

                obj = extension_type(app=app, **kwargs)
            except Exception as ex:
                self.fail('Failed to instantiate %s: %s' % (extension_type.__name__, ex))

            self.assertIs(obj.app, flask_app, 'Unexpected app object in %s' % extension_type.__name__)

    def test_with_registry(self):
        for extension_type in self._all_extensions:
            class MockRegistry(object):
                def register(self, *arg, **kwargs):
                    pass

            registry = MockRegistry()

            # RESTfulPrometheusMetrics has one additional positional argument
            kwargs = {'api': None} if extension_type is RESTfulPrometheusMetrics else {}
            kwargs['registry'] = registry

            try:
                obj = extension_type(app=None, **kwargs)
            except Exception as ex:
                self.fail('Failed to instantiate %s: %s' % (extension_type.__name__, ex))

            self.assertIs(obj.registry, registry, 'Unexpected registry object in %s' % extension_type.__name__)

    def test_with_other_parameters(self):
        for extension_type in self._all_extensions:
            # RESTfulPrometheusMetrics has one additional positional argument
            kwargs = {'api': None} if extension_type is RESTfulPrometheusMetrics else {}
            kwargs['path'] = '/testing'
            kwargs['export_defaults'] = False
            kwargs['defaults_prefix'] = 'unittest'
            kwargs['default_labels'] = {'testing': 1}

            try:
                obj = extension_type(app=None, **kwargs)
            except Exception as ex:
                self.fail('Failed to instantiate %s: %s' % (extension_type.__name__, ex))

            for arg, value in kwargs.items():
                if arg == 'api':
                    continue  # skip this argument for RESTfulPrometheusMetrics
                if arg == 'path':
                    continue  # path is set to None in many multiprocess implementations

                if hasattr(obj, '_' + arg):
                    self.assertIs(getattr(obj, '_' + arg), value,
                                  'Unexpected %s object in %s' % (arg, extension_type.__name__))
                else:
                    self.assertIs(getattr(obj, arg), value,
                                  'Unexpected %s object in %s' % (arg, extension_type.__name__))

    def test_prometheus_multiproc_env_var_change(self):
        for extension_type in self._all_extensions:
            if extension_type in [
                MultiprocessPrometheusMetrics, UWsgiPrometheusMetrics,
                GunicornPrometheusMetrics, GunicornInternalPrometheusMetrics
            ]:
                # Check only lower case env var works
                if os.environ.get('PROMETHEUS_MULTIPROC_DIR'):
                    del os.environ['PROMETHEUS_MULTIPROC_DIR']
                os.environ['prometheus_multiproc_dir'] = '/tmp'

                try:
                    app = Flask(__name__)
                    app.testing = True
                    flask_app = app

                    obj = extension_type(app=app)
                except Exception as ex:
                    self.fail('Failed to instantiate %s: %s' % (extension_type.__name__, ex))

                self.assertIs(obj.app, flask_app, 'Unexpected app object in %s' % extension_type.__name__)

                # Check only upper case env var works
                if os.environ.get('prometheus_multiproc_dir'):
                    del os.environ['prometheus_multiproc_dir']
                os.environ['PROMETHEUS_MULTIPROC_DIR'] = '/tmp'

                try:
                    app2 = Flask(__name__)
                    app2.testing = True
                    flask_app2 = app2

                    obj2 = extension_type(app=app2)
                except Exception as ex:
                    self.fail('Failed to instantiate %s: %s' % (extension_type.__name__, ex))

                self.assertIs(obj2.app, flask_app2, 'Unexpected app object in %s' % extension_type.__name__)
