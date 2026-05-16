"""Tests for hermes_azure_files.mount tool handlers."""
from __future__ import annotations

import builtins
import json
import os
from pathlib import Path

import pytest

from hermes_azure_files import mount as m


# ─── Helpers ────────────────────────────────────────────────────────────────


def _patch_mounted(monkeypatch, mounted: bool) -> None:
    monkeypatch.setattr(m, "_is_mounted", lambda _mp: mounted)


def _patch_blobfuse2(monkeypatch, installed: bool) -> None:
    monkeypatch.setattr(m, "_check_blobfuse2_installed", lambda: installed)


def _fake_proc_mounts(monkeypatch, content: str) -> None:
    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if str(path) == "/proc/mounts":
            from io import StringIO
            return StringIO(content)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)


# ─── azurefiles_mount_handler ───────────────────────────────────────────────


def test_mount_blobfuse2_success(fake_subprocess, monkeypatch, tmp_path):
    monkeypatch.setattr(m, "FUSE_TMP_PATH", str(tmp_path / "fuse"))
    _patch_mounted(monkeypatch, False)
    _patch_blobfuse2(monkeypatch, True)
    calls = fake_subprocess(returncode=0)

    result = json.loads(
        m.azurefiles_mount_handler(
            {"account_name": "acct1", "container_name": "data"}
        )
    )

    assert result["success"] is True
    assert result["mode"] == "blobfuse2"
    assert result["account_name"] == "acct1"
    assert result["container_name"] == "data"

    yaml_path = tmp_path / "fuse" / "data.yaml"
    assert yaml_path.exists()
    yaml_content = yaml_path.read_text()
    assert "account-name: acct1" in yaml_content
    assert "container: data" in yaml_content
    assert "mode: managed_identity" in yaml_content

    joined_cmds = [" ".join(c.args) for c in calls]
    assert any("sudo blobfuse2 mount" in j and "--config-file=" in j for j in joined_cmds)


def test_mount_nfs_success(fake_subprocess, monkeypatch):
    _patch_mounted(monkeypatch, False)
    calls = fake_subprocess(returncode=0)

    result = json.loads(
        m.azurefiles_mount_handler(
            {
                "account_name": "myacct",
                "container_name": "share1",
                "mode": "nfs",
                "mount_path": "/mnt/x",
            }
        )
    )

    assert result["success"] is True
    assert result["mode"] == "nfs"
    joined_cmds = [" ".join(c.args) for c in calls]
    assert any(
        "sudo mount -t nfs" in j
        and "vers=4,minorversion=1,sec=sys" in j
        and "myacct.file.core.windows.net:/myacct/share1" in j
        and "/mnt/x" in j
        for j in joined_cmds
    )


def test_mount_smb_returns_error(monkeypatch):
    _patch_mounted(monkeypatch, False)
    result = json.loads(
        m.azurefiles_mount_handler(
            {"account_name": "a", "container_name": "c", "mode": "smb"}
        )
    )
    assert "error" in result
    assert "SMB" in result["error"]


def test_mount_missing_account_name():
    result = json.loads(m.azurefiles_mount_handler({"container_name": "c"}))
    assert "error" in result
    assert "account_name" in result["error"]


def test_mount_missing_container_name():
    result = json.loads(m.azurefiles_mount_handler({"account_name": "a"}))
    assert "error" in result
    assert "container_name" in result["error"]


def test_mount_already_mounted(monkeypatch):
    _patch_mounted(monkeypatch, True)
    result = json.loads(
        m.azurefiles_mount_handler(
            {"account_name": "a", "container_name": "c", "mount_path": "/mnt/x"}
        )
    )
    assert result["success"] is True
    assert "Already mounted" in result["message"]


def test_mount_blobfuse2_auto_install(fake_subprocess, monkeypatch, tmp_path):
    """If blobfuse2 missing, _install_blobfuse2 is called automatically."""
    monkeypatch.setattr(m, "FUSE_TMP_PATH", str(tmp_path / "fuse"))
    _patch_mounted(monkeypatch, False)
    _patch_blobfuse2(monkeypatch, False)
    fake_subprocess(returncode=0)

    installed = {"called": False}

    def fake_install():
        installed["called"] = True
        return True, "ok"

    monkeypatch.setattr(m, "_install_blobfuse2", fake_install)

    result = json.loads(
        m.azurefiles_mount_handler(
            {"account_name": "a", "container_name": "c"}
        )
    )

    assert installed["called"] is True
    assert result["success"] is True


# ─── azurefiles_unmount_handler ─────────────────────────────────────────────


def test_unmount_success(fake_subprocess, monkeypatch):
    _patch_mounted(monkeypatch, True)
    calls = fake_subprocess(returncode=0)
    result = json.loads(m.azurefiles_unmount_handler({"mount_path": "/mnt/x"}))
    assert result["success"] is True
    assert any("sudo umount /mnt/x" in " ".join(c.args) for c in calls)


def test_unmount_not_mounted(monkeypatch):
    _patch_mounted(monkeypatch, False)
    result = json.loads(m.azurefiles_unmount_handler({"mount_path": "/mnt/x"}))
    assert result["success"] is True
    assert "not currently mounted" in result["message"]


def test_unmount_failure_hint_lazy(fake_subprocess, monkeypatch):
    _patch_mounted(monkeypatch, True)
    fake_subprocess(returncode=1, stderr="busy")
    result = json.loads(m.azurefiles_unmount_handler({"mount_path": "/mnt/x"}))
    assert "error" in result
    assert "umount -l" in result["hint"]


# ─── azurefiles_status_handler ──────────────────────────────────────────────


def test_status_lists_blobfuse2_mount(monkeypatch):
    proc_content = (
        "proc /proc proc rw,relatime 0 0\n"
        "blobfuse2 /mnt/azurefiles/acct/data fuse.blobfuse2 rw,nosuid,nodev 0 0\n"
        "myacct.file.core.windows.net:/myacct/share /mnt/nfs nfs4 rw,vers=4 0 0\n"
        "tmpfs /run tmpfs rw 0 0\n"
    )
    _fake_proc_mounts(monkeypatch, proc_content)

    result = json.loads(m.azurefiles_status_handler({}))
    assert result["success"] is True
    assert result["count"] == 2
    paths = [m_["mount_path"] for m_ in result["mounts"]]
    assert "/mnt/azurefiles/acct/data" in paths
    assert "/mnt/nfs" in paths


# ─── azurefiles_setup_handler ───────────────────────────────────────────────


def test_setup_all_ok(fake_subprocess, monkeypatch):
    # which az → 0, az account show → 0, which blobfuse2 → 0, sudo mkdir → 0
    _patch_blobfuse2(monkeypatch, True)
    fake_subprocess(returncode=0)

    result = json.loads(m.azurefiles_setup_handler({}))
    assert result["success"] is True
    assert result["checks"]["az_cli"]["ok"] is True
    assert result["checks"]["credentials"]["ok"] is True
    assert result["checks"]["blobfuse2"]["ok"] is True
    assert result["checks"]["mount_directory"]["ok"] is True


def test_setup_blobfuse2_missing_then_installed(fake_subprocess, monkeypatch):
    _patch_blobfuse2(monkeypatch, False)
    fake_subprocess(returncode=0)

    installed = {"called": False}

    def fake_install():
        installed["called"] = True
        return True, "blobfuse2 installed successfully"

    monkeypatch.setattr(m, "_install_blobfuse2", fake_install)

    result = json.loads(m.azurefiles_setup_handler({}))
    assert installed["called"] is True
    assert result["checks"]["blobfuse2"]["ok"] is True
    assert result["success"] is True
