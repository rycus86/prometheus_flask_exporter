from pydantic.dataclasses import dataclass
from main import metrics


@dataclass
class Info:
    foo: str


@metrics.summary('test_by_status', 'Test Request latencies by status', labels={
    'code': lambda r: r.status_code
})
def test() -> Info:
    return Info('Test version')
