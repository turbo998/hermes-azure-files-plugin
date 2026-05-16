"""Tests for hermes_azure_files.blob handlers."""
from __future__ import annotations

import datetime as dt
import json
from unittest.mock import MagicMock

import pytest

from hermes_azure_files import blob as blob_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _install_mock_service(monkeypatch):
    """Patch get_blob_service_client to return a fresh MagicMock service."""
    service = MagicMock(name="BlobServiceClient")
    container = MagicMock(name="ContainerClient")
    service.get_container_client.return_value = container

    captured = {"args": None, "kwargs": None}

    def _factory(account_name, auth="default", api_key=None):
        captured["args"] = (account_name,)
        captured["kwargs"] = {"auth": auth, "api_key": api_key}
        return service

    monkeypatch.setattr(blob_mod, "get_blob_service_client", _factory)
    return service, container, captured


def _blob_item(name, size=10, last_modified=None):
    item = MagicMock()
    item.name = name
    item.size = size
    item.last_modified = last_modified or dt.datetime(2024, 1, 1, 12, 0, 0)
    return item


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------
def test_upload_success(monkeypatch, tmp_path):
    service, container, captured = _install_mock_service(monkeypatch)
    f = tmp_path / "hello.txt"
    f.write_bytes(b"hello world")

    out = blob_mod.blob_upload_handler(
        {
            "account_name": "acct",
            "container_name": "cont",
            "local_path": str(f),
        }
    )
    data = json.loads(out)
    assert data["success"] is True
    assert data["account"] == "acct"
    assert data["container"] == "cont"
    assert data["blob"] == "hello.txt"
    assert data["size_bytes"] == 11

    service.get_container_client.assert_called_once_with("cont")
    call_kwargs = container.upload_blob.call_args.kwargs
    assert call_kwargs["name"] == "hello.txt"
    assert call_kwargs["overwrite"] is False
    assert captured["kwargs"] == {"auth": "default", "api_key": None}


def test_upload_missing_args_returns_error(monkeypatch):
    _install_mock_service(monkeypatch)
    out = blob_mod.blob_upload_handler({"account_name": "a"})
    data = json.loads(out)
    assert "error" in data
    assert "hint" in data


def test_upload_local_file_missing(monkeypatch, tmp_path):
    _install_mock_service(monkeypatch)
    missing = tmp_path / "nope.bin"
    out = blob_mod.blob_upload_handler(
        {
            "account_name": "acct",
            "container_name": "cont",
            "local_path": str(missing),
        }
    )
    data = json.loads(out)
    assert "error" in data
    assert "not found" in data["error"]


def test_upload_overwrite_true_propagates(monkeypatch, tmp_path):
    service, container, _ = _install_mock_service(monkeypatch)
    f = tmp_path / "x.txt"
    f.write_text("abc")
    out = blob_mod.blob_upload_handler(
        {
            "account_name": "a",
            "container_name": "c",
            "local_path": str(f),
            "blob_name": "renamed.txt",
            "overwrite": True,
        }
    )
    data = json.loads(out)
    assert data["success"] is True
    assert data["blob"] == "renamed.txt"
    kwargs = container.upload_blob.call_args.kwargs
    assert kwargs["overwrite"] is True
    assert kwargs["name"] == "renamed.txt"


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------
def test_download_success(monkeypatch, tmp_path):
    service, container, _ = _install_mock_service(monkeypatch)
    downloader = MagicMock()
    downloader.readall.return_value = b"\x00\x01binary"
    container.download_blob.return_value = downloader

    dest = tmp_path / "out.bin"
    out = blob_mod.blob_download_handler(
        {
            "account_name": "a",
            "container_name": "c",
            "blob_name": "remote.bin",
            "local_path": str(dest),
        }
    )
    data = json.loads(out)
    assert data["success"] is True
    assert data["size_bytes"] == 8
    assert dest.read_bytes() == b"\x00\x01binary"
    container.download_blob.assert_called_once_with("remote.bin")


def test_download_creates_parent_dirs(monkeypatch, tmp_path):
    service, container, _ = _install_mock_service(monkeypatch)
    downloader = MagicMock()
    downloader.readall.return_value = b"data"
    container.download_blob.return_value = downloader

    dest = tmp_path / "deep" / "nested" / "out.txt"
    out = blob_mod.blob_download_handler(
        {
            "account_name": "a",
            "container_name": "c",
            "blob_name": "b",
            "local_path": str(dest),
        }
    )
    data = json.loads(out)
    assert data["success"] is True
    assert dest.exists()
    assert dest.read_bytes() == b"data"


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------
def test_list_returns_multiple_blobs(monkeypatch):
    service, container, _ = _install_mock_service(monkeypatch)
    container.list_blobs.return_value = iter(
        [_blob_item("a.txt", 1), _blob_item("b.txt", 2), _blob_item("c.txt", 3)]
    )

    out = blob_mod.blob_list_handler(
        {"account_name": "a", "container_name": "c"}
    )
    data = json.loads(out)
    assert data["success"] is True
    assert data["count"] == 3
    assert data["has_more"] is False
    assert [b["name"] for b in data["blobs"]] == ["a.txt", "b.txt", "c.txt"]
    assert data["blobs"][0]["size"] == 1
    assert data["blobs"][0]["last_modified"] == "2024-01-01T12:00:00"


def test_list_with_prefix(monkeypatch):
    service, container, _ = _install_mock_service(monkeypatch)
    container.list_blobs.return_value = iter([_blob_item("logs/x.txt")])

    blob_mod.blob_list_handler(
        {
            "account_name": "a",
            "container_name": "c",
            "prefix": "logs/",
            "max_results": 50,
        }
    )
    kwargs = container.list_blobs.call_args.kwargs
    assert kwargs["name_starts_with"] == "logs/"
    assert kwargs["results_per_page"] == 50


def test_list_max_results_clamped(monkeypatch):
    service, container, _ = _install_mock_service(monkeypatch)
    container.list_blobs.return_value = iter([])

    # too large -> 1000
    blob_mod.blob_list_handler(
        {"account_name": "a", "container_name": "c", "max_results": 99999}
    )
    assert container.list_blobs.call_args.kwargs["results_per_page"] == 1000

    # too small -> 1
    blob_mod.blob_list_handler(
        {"account_name": "a", "container_name": "c", "max_results": 0}
    )
    assert container.list_blobs.call_args.kwargs["results_per_page"] == 1


def test_list_has_more(monkeypatch):
    service, container, _ = _install_mock_service(monkeypatch)
    items = [_blob_item(f"b{i}.txt", i) for i in range(10)]
    container.list_blobs.return_value = iter(items)

    out = blob_mod.blob_list_handler(
        {"account_name": "a", "container_name": "c", "max_results": 3}
    )
    data = json.loads(out)
    assert data["success"] is True
    assert data["count"] == 3
    assert data["has_more"] is True


def test_list_missing_args(monkeypatch):
    _install_mock_service(monkeypatch)
    out = blob_mod.blob_list_handler({"account_name": "a"})
    data = json.loads(out)
    assert "error" in data
