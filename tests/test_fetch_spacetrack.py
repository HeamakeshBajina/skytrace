import json
from urllib.parse import parse_qs

import pytest

from scripts import fetch_satellites as fetcher


class FakeResponse:
    def __init__(self, body):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_spacetrack_fetch_authenticates_and_filters_stations(monkeypatch):
    monkeypatch.setenv("SPACETRACK_USER", "test@example.com")
    monkeypatch.setenv("SPACETRACK_PASS", "test-password")

    records = [
        {
            "OBJECT_NAME": "ISS (ZARYA)",
            "TLE_LINE0": "0 ISS (ZARYA)",
            "TLE_LINE1": "1 25544U 98067A   26294.04791053  .00009575  00000+0  18188-3 0  9996",
            "TLE_LINE2": "2 25544  51.6327  37.2623 0006759 289.5321  70.4938 15.48967427591263",
        },
        {
            "OBJECT_NAME": "UNRELATED TEST OBJECT",
            "TLE_LINE0": "0 UNRELATED TEST OBJECT",
            "TLE_LINE1": "1 12345U 98067A   26294.04791053  .00009575  00000+0  18188-3 0  9996",
            "TLE_LINE2": "2 12345  51.6327  37.2623 0006759 289.5321  70.4938 15.48967427591263",
        },
    ]

    class FakeOpener:
        def __init__(self):
            self.requests = []
            self.responses = iter([
                FakeResponse("Login successful"),
                FakeResponse(json.dumps(records)),
            ])

        def open(self, request, timeout):
            self.requests.append((request, timeout))
            return next(self.responses)

    fake_opener = FakeOpener()
    monkeypatch.setattr(fetcher.urllib.request, "build_opener",
                        lambda *args: fake_opener)

    text, source = fetcher.fetch_spacetrack()

    assert "ISS (ZARYA)" in text
    assert "UNRELATED TEST OBJECT" not in text
    assert "class/gp/" in source
    assert len(fake_opener.requests) == 2

    login_request, login_timeout = fake_opener.requests[0]
    assert login_request.full_url.endswith("/ajaxauth/login")
    assert login_timeout == 15
    login_fields = parse_qs(login_request.data.decode("utf-8"))
    assert login_fields["identity"] == ["test@example.com"]
    assert login_fields["password"] == ["test-password"]

    _, query_timeout = fake_opener.requests[1]
    assert query_timeout == 45


def test_spacetrack_requires_both_credentials(monkeypatch):
    monkeypatch.delenv("SPACETRACK_USER", raising=False)
    monkeypatch.delenv("SPACETRACK_PASS", raising=False)

    with pytest.raises(RuntimeError, match="credentials are not configured"):
        fetcher.fetch_spacetrack()
