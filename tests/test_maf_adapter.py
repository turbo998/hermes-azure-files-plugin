"""Tests for the Microsoft Agent Framework (MAF) adapter layer."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

af = pytest.importorskip("agent_framework")

from hermes_azure_files import maf_adapter  # noqa: E402


EXPECTED_TOOL_NAMES = {
    "azurefiles_mount",
    "azurefiles_unmount",
    "azurefiles_status",
    "azurefiles_setup",
    "azurefiles_blob_upload",
    "azurefiles_blob_download",
    "azurefiles_blob_list",
}


def test_get_maf_tools_returns_7_function_tools():
    tools = maf_adapter.get_maf_tools()
    assert isinstance(tools, list)
    assert len(tools) == 7


def test_each_tool_has_name_and_description():
    tools = maf_adapter.get_maf_tools()
    names = set()
    for t in tools:
        assert getattr(t, "name", None), f"tool missing name: {t!r}"
        assert getattr(t, "description", None), f"tool missing description: {t!r}"
        names.add(t.name)
    assert names == EXPECTED_TOOL_NAMES


def test_tools_are_function_tool_instances():
    for t in maf_adapter.get_maf_tools():
        assert isinstance(t, af.FunctionTool)


def test_blob_upload_tool_invocable():
    """Mock the underlying handler; verify the wrapper passes args through."""
    tools = {t.name: t for t in maf_adapter.get_maf_tools()}
    upload_tool = tools["azurefiles_blob_upload"]

    fake_return = json.dumps({"success": True, "blob": "x.txt"})
    with patch(
        "hermes_azure_files.blob.blob_upload_handler", return_value=fake_return
    ) as mock_handler:
        result = upload_tool.func(
            account_name="myacct",
            container_name="mycont",
            local_path="/tmp/x.txt",
        )

    assert mock_handler.called
    args_passed = mock_handler.call_args.args[0]
    assert args_passed["account_name"] == "myacct"
    assert args_passed["container_name"] == "mycont"
    assert args_passed["local_path"] == "/tmp/x.txt"
    # wrapper should decode handler JSON into dict
    assert isinstance(result, dict)
    assert result["success"] is True
