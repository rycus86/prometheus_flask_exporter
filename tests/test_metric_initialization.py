from abc import ABC, abstractmethod

from flask import request

from unittest_helper import BaseTestCase


# The class nesting avoids that the abstract base class will be tested (which is not possible because it is abstract..)
class MetricInitializationTest:
    class MetricInitializationTest(BaseTestCase, ABC):
        metric_suffix = None

        @property
        @abstractmethod
        def metric_type(self):
            pass

        def get_metric_decorator(self, metrics):
            return getattr(metrics, self.metric_type)

        def _test_metric_initialization(self, labels=None, initial_value_when_only_static_labels=True):
            metrics = self.metrics()
            metric_decorator = self.get_metric_decorator(metrics)

            test_path = '/test/1'

            @self.app.route(test_path)
            @metric_decorator('metric_1', 'Metric 1',
                              labels=labels,
                              initial_value_when_only_static_labels=initial_value_when_only_static_labels)
            def test1():
                return 'OK'

            if labels:
                # replace callable with the "expected" result
                if 'path' in labels:
                    labels['path'] = test_path

                label_value_pairs = labels.items()
            else:
                label_value_pairs = []

            prometheus_metric_name = 'metric_1'
            if self.metric_suffix:
                prometheus_metric_name += self.metric_suffix

            # test metric value before any incoming HTTP call
            self.assertMetric(prometheus_metric_name, '0.0', *label_value_pairs)

            self.client.get('/test/1')

            if self.metric_type == 'gauge':
                expected_metric_value = '0.0'
            else:
                expected_metric_value = '1.0'

            self.assertMetric(prometheus_metric_name, expected_metric_value, *label_value_pairs)

        def test_initial_value_no_labels(self):
            self._test_metric_initialization()

        def test_initial_value_only_static_labels(self):
            labels = {'label_name': 'label_value'}
            self._test_metric_initialization(labels)

        def test_initial_value_only_static_labels_no_initialization(self):
            labels = {'label_name': 'label_value'}
            self.assertRaises(AssertionError, self._test_metric_initialization, labels, initial_value_when_only_static_labels=False)

        def test_initial_value_callable_label(self):
            labels = {'path': lambda: request.path}
            self.assertRaises(AssertionError, self._test_metric_initialization, labels)



class HistogramInitializationTest(MetricInitializationTest.MetricInitializationTest):
    metric_suffix = '_count'

    @property
    def metric_type(self):
        return 'histogram'


class SummaryInitializationTest(MetricInitializationTest.MetricInitializationTest):
    metric_suffix = '_count'

    @property
    def metric_type(self):
        return 'summary'


class GaugeInitializationTest(MetricInitializationTest.MetricInitializationTest):
    @property
    def metric_type(self):
        return 'gauge'


class CounterInitializationTest(MetricInitializationTest.MetricInitializationTest):
    metric_suffix = '_total'

    @property
    def metric_type(self):
        return 'counter'
