"""Hermes Azure Files plugin entry point."""

from .mount import (
    azurefiles_mount_handler,
    azurefiles_unmount_handler,
    azurefiles_status_handler,
    azurefiles_setup_handler,
    AZUREFILES_MOUNT_SCHEMA,
    AZUREFILES_UNMOUNT_SCHEMA,
    AZUREFILES_STATUS_SCHEMA,
    AZUREFILES_SETUP_SCHEMA,
)
from .blob import (
    blob_upload_handler,
    blob_download_handler,
    blob_list_handler,
    BLOB_UPLOAD_SCHEMA,
    BLOB_DOWNLOAD_SCHEMA,
    BLOB_LIST_SCHEMA,
)


def register(ctx) -> None:
    """Register Azure Files tools with the Hermes plugin context."""
    ctx.register_tool(
        name="azurefiles_mount",
        toolset="azurefiles",
        schema=AZUREFILES_MOUNT_SCHEMA,
        handler=azurefiles_mount_handler,
        description="Mount Azure Files shares as local directories",
        emoji="📁",
    )
    ctx.register_tool(
        name="azurefiles_unmount",
        toolset="azurefiles",
        schema=AZUREFILES_UNMOUNT_SCHEMA,
        handler=azurefiles_unmount_handler,
        description="Unmount Azure Files shares",
        emoji="⏏️",
    )
    ctx.register_tool(
        name="azurefiles_status",
        toolset="azurefiles",
        schema=AZUREFILES_STATUS_SCHEMA,
        handler=azurefiles_status_handler,
        description="Show Azure Files mount status",
        emoji="📊",
    )
    ctx.register_tool(
        name="azurefiles_setup",
        toolset="azurefiles",
        schema=AZUREFILES_SETUP_SCHEMA,
        handler=azurefiles_setup_handler,
        description="Setup Azure Files prerequisites (blobfuse2 / cifs-utils)",
        emoji="⚙️",
    )
    ctx.register_tool(
        name="blob_upload",
        toolset="azurefiles",
        schema=BLOB_UPLOAD_SCHEMA,
        handler=blob_upload_handler,
        description="Upload a local file to an Azure Blob container",
        emoji="⬆️",
    )
    ctx.register_tool(
        name="blob_download",
        toolset="azurefiles",
        schema=BLOB_DOWNLOAD_SCHEMA,
        handler=blob_download_handler,
        description="Download a blob from an Azure Blob container",
        emoji="⬇️",
    )
    ctx.register_tool(
        name="blob_list",
        toolset="azurefiles",
        schema=BLOB_LIST_SCHEMA,
        handler=blob_list_handler,
        description="List blobs in an Azure Blob container",
        emoji="📜",
    )


__all__ = ["register"]
