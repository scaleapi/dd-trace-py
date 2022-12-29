import pytest

from ddtrace.internal import agent


@pytest.mark.parametrize(
    "hostname,expected",
    [
        (None, False),
        ("10.0.0.1", False),
        ("192.168.1.1", False),
        ("https://www.datadog.com", False),
        ("2001:db8:3333:4444:5555:6666:7777:8888", True),
        ("2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF", True),
        ("[2001:db8:3333:4444:5555:6666:7777:8888]", False),
        ("::", True),
    ],
)
def test_is_ipv6_hostname(hostname, expected):
    assert agent.is_ipv6_hostname(hostname) == expected


def test_hostname(monkeypatch):
    assert agent.get_hostname() == "localhost"
    monkeypatch.setenv("DD_AGENT_HOST", "host")
    assert agent.get_hostname() == "host"
    monkeypatch.setenv("DD_AGENT_HOST", "2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF")
    assert agent.get_hostname() == "[2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF]"


def test_trace_port(monkeypatch):
    assert agent.get_trace_port() == 8126
    monkeypatch.setenv("DD_TRACE_AGENT_PORT", "1235")
    assert agent.get_trace_port() == 1235
    monkeypatch.setenv("DD_AGENT_PORT", "1234")
    assert agent.get_trace_port() == 1234


def test_stats_port(monkeypatch):
    assert agent.get_stats_port() == 8125
    monkeypatch.setenv("DD_DOGSTATSD_PORT", "1235")
    assert agent.get_stats_port() == 1235


def test_trace_url(monkeypatch):
    assert agent.get_trace_url() == "http://localhost:8126"
    monkeypatch.setenv("DD_TRACE_AGENT_PORT", "1235")
    assert agent.get_trace_url() == "http://localhost:1235"
    monkeypatch.setenv("DD_AGENT_HOST", "mars")
    assert agent.get_trace_url() == "http://mars:1235"

    monkeypatch.setenv("DD_TRACE_AGENT_URL", "http://saturn:1111")
    assert agent.get_trace_url() == "http://saturn:1111"


def test_stats_url(monkeypatch):
    assert agent.get_stats_url() == "udp://localhost:8125"
    monkeypatch.setenv("DD_AGENT_HOST", "saturn")
    assert agent.get_stats_url() == "udp://saturn:8125"
    monkeypatch.setenv("DD_DOGSTATSD_PORT", "1235")
    assert agent.get_stats_url() == "udp://saturn:1235"

    monkeypatch.setenv("DD_DOGSTATSD_URL", "udp://mars:1234")
    assert agent.get_stats_url() == "udp://mars:1234"


def test_get_connection():
    with pytest.raises(ValueError):
        agent.get_connection("bad://localhost:1234", timeout=1)

    with pytest.raises(ValueError):
        agent.get_connection(":#@$@!//localhost:1234", timeout=1)

    with pytest.raises(ValueError):
        agent.get_connection("", timeout=1)


def test_verify_url():
    agent.verify_url("http://localhost:1234")
    agent.verify_url("https://localhost:1234")
    agent.verify_url("https://localhost")
    agent.verify_url("http://192.168.1.1")
    agent.verify_url("http://[2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF]")
    agent.verify_url("http://[2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF]:1234")
    agent.verify_url("unix:///file.sock")
    agent.verify_url("unix:///file")

    with pytest.raises(ValueError) as e:
        agent.verify_url("unix://")
    assert str(e.value) == "Invalid file path in Agent URL 'unix://'"

    with pytest.raises(ValueError) as e:
        agent.verify_url("http2://localhost:1234")
    assert (
        str(e.value)
        == "Unsupported protocol 'http2' in Agent URL 'http2://localhost:1234'. Must be one of: http, https, unix"
    )

    with pytest.raises(ValueError) as e:
        agent.verify_url("adsf")
    assert str(e.value) == "Unsupported protocol '' in Agent URL 'adsf'. Must be one of: http, https, unix"

    with pytest.raises(ValueError) as e:
        agent.verify_url("http://")
    assert str(e.value) == "Invalid hostname in Agent URL 'http://'"

    with pytest.raises(ValueError) as e:
        agent.verify_url("https://")
    assert str(e.value) == "Invalid hostname in Agent URL 'https://'"

    with pytest.raises(ValueError) as e:
        agent.verify_url("unix://")
    assert str(e.value) == "Invalid file path in Agent URL 'unix://'"
