import pytest
from flask import Flask, request, jsonify
from modules.http_utils import (
    BridgeHTTPError,
    route_errors,
    json_payload,
    string_field,
    int_field,
    bool_field,
    string_list_field,
    path_field,
    content_field,
    inbox_name_field,
    MISSING
)
import subprocess
import re
import errno
import os

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

def test_bridge_http_error():
    err = BridgeHTTPError(404, "Not Found", details="some detail")
    assert err.status_code == 404
    assert err.error == "Not Found"
    assert err.payload == {"details": "some detail"}

def test_route_errors_bridge_http_error(app):
    @app.route("/test")
    @route_errors
    def test_route():
        raise BridgeHTTPError(400, "Bad Request", info="bad")

    client = app.test_client()
    response = client.get("/test")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Bad Request", "info": "bad"}

def test_route_errors_timeout(app):
    @app.route("/test")
    @route_errors
    def test_route():
        raise subprocess.TimeoutExpired("cmd", 5.0)

    client = app.test_client()
    response = client.get("/test")
    assert response.status_code == 504
    assert "Execution timed out after 5.0 seconds" in response.get_json()["error"]

def test_route_errors_generic_exceptions(app):
    @app.route("/perm")
    @route_errors
    def perm():
        raise PermissionError("denied")

    @app.route("/fnf")
    @route_errors
    def fnf():
        raise FileNotFoundError("missing")

    @app.route("/value")
    @route_errors
    def val():
        raise ValueError("invalid value")

    @app.route("/oserr")
    @route_errors
    def oserr():
        e = OSError("os error")
        e.errno = errno.EACCES
        raise e

    @app.route("/internal")
    @route_errors
    def internal():
        raise RuntimeError("boom")

    @app.route("/isdir")
    @route_errors
    def isdir():
        raise IsADirectoryError("is a dir")

    @app.route("/reerr")
    @route_errors
    def reerr():
        raise re.error("bad regex")

    client = app.test_client()
    assert client.get("/perm").status_code == 403
    assert client.get("/fnf").status_code == 404
    assert client.get("/value").status_code == 400
    assert client.get("/oserr").status_code == 403
    assert client.get("/internal").status_code == 500
    assert client.get("/isdir").status_code == 400
    assert client.get("/reerr").status_code == 400

def test_json_payload(app):
    with app.test_request_context(method="POST", json={"key": "value"}):
        data = json_payload()
        assert data == {"key": "value"}

    with app.test_request_context(method="POST", data=""):
        data = json_payload()
        assert data == {}

    with app.test_request_context(method="POST", data="not json", content_type="application/json"):
        with pytest.raises(BridgeHTTPError) as excinfo:
            json_payload()
        assert excinfo.value.status_code == 400

    with app.test_request_context(method="POST", json=["list"]):
        with pytest.raises(BridgeHTTPError) as excinfo:
            json_payload()
        assert excinfo.value.status_code == 400

def test_string_field():
    data = {"name": "Jules"}
    assert string_field(data, "name") == "Jules"

    with pytest.raises(BridgeHTTPError) as exc:
        string_field({}, "name")
    assert exc.value.status_code == 400

    assert string_field({}, "name", default="guest") == "guest"

    with pytest.raises(BridgeHTTPError):
        string_field({"name": ""}, "name")

    assert string_field({"name": ""}, "name", allow_empty=True) == ""

    with pytest.raises(BridgeHTTPError):
        string_field({"name": "a\x00b"}, "name", control_safe=True)

def test_int_field():
    assert int_field({"age": 20}, "age") == 20
    assert int_field({"age": "20"}, "age") == 20

    with pytest.raises(BridgeHTTPError):
        int_field({}, "age")

    with pytest.raises(BridgeHTTPError):
        int_field({"age": "abc"}, "age")

    with pytest.raises(BridgeHTTPError):
        int_field({"age": 10}, "age", min_value=15)

    with pytest.raises(BridgeHTTPError):
        int_field({"age": 30}, "age", max_value=25)

    with pytest.raises(BridgeHTTPError):
        int_field({"age": True}, "age")

def test_bool_field():
    assert bool_field({"is_active": True}, "is_active") is True
    assert bool_field({"is_active": False}, "is_active") is False

    with pytest.raises(BridgeHTTPError):
        bool_field({}, "is_active")

    assert bool_field({}, "is_active", default=True) is True

    with pytest.raises(BridgeHTTPError):
        bool_field({"is_active": "true"}, "is_active")

def test_string_list_field():
    assert string_list_field({"items": ["a", "b"]}, "items") == ["a", "b"]
    assert string_list_field({}, "items") == []

    with pytest.raises(BridgeHTTPError):
        string_list_field({"items": "not a list"}, "items")

    with pytest.raises(BridgeHTTPError):
        string_list_field({"items": ["a", ""]}, "items")

    with pytest.raises(BridgeHTTPError):
        string_list_field({"items": ["a\x00b"]}, "items", control_safe=True)

def test_path_field():
    assert path_field({"path": "/foo/bar"}) == "/foo/bar"

    with pytest.raises(BridgeHTTPError):
        path_field({"path": "/foo/\x00bar"})

def test_content_field():
    assert content_field({"content": "hello"}) == "hello"
    assert content_field({"data": "world"}) == "world"

    with pytest.raises(BridgeHTTPError):
        content_field({"other": "hello"})

def test_inbox_name_field():
    assert inbox_name_field({"file": "/path/to/file.txt"}, default="def") == "file.txt"
    assert inbox_name_field({}, default="def") == "def"
    assert inbox_name_field({"file": ""}, default="def") == "def"

    with pytest.raises(BridgeHTTPError):
        inbox_name_field({"file": "/path/to/\x00file"}, default="def")

def test_route_errors_specific_exceptions(app):
    class ShellNotAvailableError(Exception):
        pass

    @app.route("/shellerr")
    @route_errors
    def shellerr():
        raise ShellNotAvailableError("no shell")

    @app.route("/oserr_enoent")
    @route_errors
    def oserr_enoent():
        e = OSError("os error enoent")
        e.errno = errno.ENOENT
        raise e

    @app.route("/oserr_other")
    @route_errors
    def oserr_other():
        e = OSError("os error other")
        e.errno = 999
        raise e

    client = app.test_client()
    assert client.get("/shellerr").status_code == 400
    assert client.get("/oserr_enoent").status_code == 404
    assert client.get("/oserr_other").status_code == 500

def test_json_payload_not_json_request(app):
    with app.test_request_context(method="POST", data='{"a": 1}'):
        # No content-type header makes it not JSON for Flask
        with pytest.raises(BridgeHTTPError) as excinfo:
            json_payload()
        assert excinfo.value.status_code == 400

def test_string_field_not_string():
    with pytest.raises(BridgeHTTPError) as exc:
        string_field({"name": 123}, "name")
    assert exc.value.status_code == 400
    assert "must be a string" in exc.value.payload["details"]

def test_int_field_default():
    assert int_field({}, "age", default=25) == 25

def test_inbox_name_field_empty_basename():
    with pytest.raises(BridgeHTTPError) as exc:
        inbox_name_field({"file": "/"}, default="def")
    assert exc.value.status_code == 400
    assert "cannot be empty" in exc.value.payload["details"]
