import inspect
import threading
from uuid import uuid4

import attr
import mock
import pytest

from ddtrace.debugging._probe.model import DDExpression
from ddtrace.debugging._snapshot.collector import SnapshotCollector
from ddtrace.debugging._snapshot.model import Snapshot
from tests.debugging.utils import create_snapshot_line_probe


class MockLimiter:
    def limit(self):
        return


@attr.s
class MockFrame(object):
    f_locals = attr.ib(type=dict)


@attr.s
class MockThread(object):
    ident = attr.ib(type=int)
    name = attr.ib(type=str)


def mock_encoder(wraps=None):
    encoder = mock.Mock(wraps=wraps)
    snapshot_encoder = mock.Mock()
    encoder._encoders = {Snapshot: snapshot_encoder}

    return encoder, snapshot_encoder


def test_collector_cond():
    encoder, _ = mock_encoder()

    collector = SnapshotCollector(encoder=encoder)
    collector.push(
        create_snapshot_line_probe(
            probe_id=uuid4(),
            source_file="file.py",
            line=123,
            condition=DDExpression("a not null", lambda _: _["a"] is not None),
        ),
        MockFrame(dict(a=42)),
        MockThread(-1, "MainThread"),
        (Exception, Exception("foo"), None),
    )
    collector.push(
        create_snapshot_line_probe(
            probe_id=uuid4(),
            source_file="file.py",
            line=123,
            condition=DDExpression("b not null", lambda _: _["b"] is not None),
        ),
        MockFrame(dict(b=None)),
        MockThread(-2, "WorkerThread"),
        (Exception, Exception("foo"), None),
    )

    encoder.put.assert_called_once()


def test_collector_collect_enqueue():
    encoder, snapshot_encoder = mock_encoder()

    def wrapped(posarg, foo):
        i = posarg
        posarg = i << 1
        return "[%d] %s" % (i, foo)

    collector = SnapshotCollector(encoder=encoder)
    for i in range(10):
        with collector.collect(
            create_snapshot_line_probe(probe_id="batch-test", source_file="foo.py", line=42),
            inspect.currentframe(),
            threading.current_thread(),
            [("posarg", i), ("foo", "bar")],
        ) as sc:
            assert sc.snapshot.entry_capture
            sc.return_value = wrapped(i, foo="bar")

        assert "[%d] bar" % i == sc.return_value
        assert sc.snapshot.return_capture

    assert len(encoder.put.mock_calls) == 10


def test_collector_collect_exception_enqueue():
    encoder, snapshot_encoder = mock_encoder()

    class MockException(Exception):
        pass

    def wrapped():
        raise MockException("test")

    collector = SnapshotCollector(encoder=encoder)
    for _ in range(10):
        with pytest.raises(MockException), collector.collect(
            create_snapshot_line_probe(probe_id="batch-test", source_file="foo.py", line=42),
            inspect.currentframe(),
            threading.current_thread(),
            [],
        ) as sc:
            assert sc.snapshot.entry_capture
            sc.return_value = wrapped()

        assert sc.snapshot.return_capture

    assert len(encoder.put.mock_calls) == 10


def test_collector_push_enqueue():
    encoder, _ = mock_encoder()

    collector = SnapshotCollector(encoder=encoder)
    for _ in range(10):
        collector.push(
            create_snapshot_line_probe(probe_id=uuid4(), source_file="file.py", line=123),
            inspect.currentframe(),
            threading.current_thread(),
            (Exception, Exception("foo"), None),
        )

    assert len(encoder.put.mock_calls) == 10
