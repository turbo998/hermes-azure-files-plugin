"""Tests for plugin register() entry point."""

from hermes_azure_files import register


class FakeCtx:
    def __init__(self):
        self.registered = []

    def register_tool(self, **kwargs):
        self.registered.append(kwargs)


def test_register_all_seven_tools():
    ctx = FakeCtx()
    register(ctx)

    assert len(ctx.registered) == 7

    expected_names = {
        "azurefiles_mount",
        "azurefiles_unmount",
        "azurefiles_status",
        "azurefiles_setup",
        "blob_upload",
        "blob_download",
        "blob_list",
    }
    actual_names = {t["name"] for t in ctx.registered}
    assert actual_names == expected_names

    for tool in ctx.registered:
        assert tool["toolset"] == "azurefiles"
        assert callable(tool["handler"])
        assert "schema" in tool and isinstance(tool["schema"], dict)
        assert tool.get("description")
        assert tool.get("emoji")
