"""Shared pytest fixtures for hermes-azure-files-plugin tests."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def fake_subprocess(monkeypatch):
    """Monkeypatch ``subprocess.run`` to return a configurable CompletedProcess.

    Usage::

        def test_x(fake_subprocess):
            calls = fake_subprocess(returncode=0, stdout="ok", stderr="")
            ...  # exercise code that invokes subprocess.run
            assert calls[0].args[0][0] == "blobfuse2"
    """

    def _install(returncode: int = 0, stdout: str = "", stderr: str = "",
                 cmd_results: dict | None = None):
        """Install fake subprocess.run.

        cmd_results: optional dict mapping a substring (matched against the
        joined command) -> (returncode, stdout, stderr). First matching key
        wins; otherwise the default (returncode, stdout, stderr) is used.
        """
        recorded: list = []

        def _fake_run(cmd, *args, **kwargs):  # noqa: ANN001
            joined = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
            rc, out, err = returncode, stdout, stderr
            if cmd_results:
                for key, val in cmd_results.items():
                    if key in joined:
                        rc, out, err = val
                        break
            completed = subprocess.CompletedProcess(
                args=cmd, returncode=rc, stdout=out, stderr=err,
            )
            recorded.append(completed)
            return completed

        monkeypatch.setattr(subprocess, "run", _fake_run)
        return recorded

    return _install


@pytest.fixture
def mock_blob_client():
    """Return a MagicMock standing in for ``azure.storage.blob.BlobServiceClient``."""
    client = MagicMock(name="BlobServiceClient")
    container = MagicMock(name="ContainerClient")
    blob = MagicMock(name="BlobClient")
    client.get_container_client.return_value = container
    container.get_blob_client.return_value = blob
    client.get_blob_client.return_value = blob
    return client


@pytest.fixture
def tmp_mount_path(tmp_path) -> Path:
    """A temporary directory suitable as a fake mount point."""
    mount = tmp_path / "mnt" / "azurefiles"
    mount.mkdir(parents=True, exist_ok=True)
    return mount
