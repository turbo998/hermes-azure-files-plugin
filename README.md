# hermes-azure-files-plugin

> **STATUS: Preview** — API surface and tool names may change before 1.0.

Hermes Agent `toolset` plugin that integrates **Azure Blob Storage** and
**Azure Files** with the agent runtime. It exposes two complementary access
paths:

1. **Mount path** — `blobfuse2` (or NFS 4.1 / SMB for Azure Files) so blobs
   appear as a local directory.
2. **SDK path** — direct `azure-storage-blob` operations (`upload / download /
   list`) without any kernel-level mount, recommended for batch or programmatic
   access.

This plugin is the Azure analogue of `hermes-s3files-plugin` (AWS).

---

## AWS → Azure mapping

| AWS (hermes-s3files-plugin)  | Azure (this plugin)   | Implementation                                                    |
|------------------------------|-----------------------|-------------------------------------------------------------------|
| `s3files_mount` (NFS)        | `azurefiles_mount`    | BlobFuse2 (preferred) / Azure Files NFS 4.1 / Azure Files SMB     |
| `s3files_unmount`            | `azurefiles_unmount`  | `sudo umount <path>`                                              |
| `s3files_status`             | `azurefiles_status`   | Parse `/proc/mounts` for `blobfuse2` / `azurefiles` entries       |
| `s3files_setup`              | `azurefiles_setup`    | Install `blobfuse2` from MS apt repo + verify `az` / MSI          |
| —                            | `blob_upload`         | `azure-storage-blob` + `DefaultAzureCredential` (SDK)             |
| —                            | `blob_download`       | SDK direct                                                        |
| —                            | `blob_list`           | SDK direct, optional `prefix` filter                              |

---

## Architecture

```
                    ┌──────────────────────────┐
                    │     Hermes Agent         │
                    └────────────┬─────────────┘
                                 │  toolset
              ┌──────────────────┼──────────────────┐
              │                                     │
       MOUNT PATH                              SDK PATH
       (azurefiles_*)                          (blob_*)
              │                                     │
   ┌──────────▼──────────┐              ┌───────────▼───────────┐
   │  blobfuse2 /        │              │ azure-storage-blob    │
   │  mount -t nfs       │              │ + azure-identity      │
   └──────────┬──────────┘              └───────────┬───────────┘
              │                                     │
              └────────────────┬────────────────────┘
                               ▼
                ┌──────────────────────────────┐
                │  Azure Storage Account       │
                │  (Blob containers / Files)   │
                └──────────────────────────────┘
```

---

## Installation

```bash
pip install -e .
# or with dev extras
pip install -e ".[dev]"
```

System dependencies for the mount path (installed by `azurefiles_setup`):

- `blobfuse2` (from Microsoft apt repository on Ubuntu / Debian)
- `fuse3`
- `nfs-common` (for Azure Files NFS) — optional

---

## Authentication

The SDK path uses [`DefaultAzureCredential`](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)
by default, which transparently picks up:

- Managed Identity (on Azure VMs / AKS / App Service)
- `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_CLIENT_SECRET` env vars
- `az login` shared token cache
- Visual Studio Code / Azure CLI / Azure PowerShell

The mount path supports **Managed Identity only** (`auth='managed_identity'`,
which is the default). Account-key and service-principal mount auth modes are
intentionally not exposed yet — use the SDK path (`blob_*`) if you need static
credentials.

Fallback for the SDK path: account key via `auth.get_credential(mode="key",
account=..., api_key=...)` — typically loaded from `AZURE_STORAGE_KEY`.

### Required RBAC role

The principal running this plugin needs at minimum:

> **Storage Blob Data Contributor** scoped to the storage account
> (or container) for read/write blob operations.

For listing-only workflows, `Storage Blob Data Reader` suffices.

---

## Tools

| Tool                  | Path  | Description                                              |
|-----------------------|-------|----------------------------------------------------------|
| `azurefiles_mount`    | mount | Mount blob container / Azure Files share to a local path |
| `azurefiles_unmount`  | mount | Unmount a previously mounted path                        |
| `azurefiles_status`   | mount | List active Azure mounts from `/proc/mounts`             |
| `azurefiles_setup`    | mount | Install `blobfuse2` and validate credentials             |
| `blob_upload`         | sdk   | Upload a local file to a blob                            |
| `blob_download`       | sdk   | Download a blob to a local file                          |
| `blob_list`           | sdk   | List blobs in a container (optional `prefix`)            |

---

## Security notes

- **Never commit `connection_string` or `account_key` to git.** Use env vars or
  a secret manager (Azure Key Vault, GitHub Secrets, etc.).
- Prefer Managed Identity / `DefaultAzureCredential` over static keys.
- The plugin will refuse to log secret values; tool outputs redact `*_key` and
  `*_secret` fields.
- BlobFuse2 caches data under `fuse_tmp_path` (default `/tmp/blobfuse2`) —
  ensure this path is on encrypted storage if your data is sensitive.

---

## Status

| Component                      | State    |
|--------------------------------|----------|
| Scaffold + auth helper         | ✅ done  |
| `azurefiles_*` mount tools     | ✅ done  |
| `blob_*` SDK tools             | ✅ done  |
| `register(ctx)` entrypoint     | ✅ done  |

Author: **Chen Qi (turbo998)** · License: MIT
