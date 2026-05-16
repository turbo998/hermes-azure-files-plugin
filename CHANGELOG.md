## Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-16

### Added
- Initial public release of `hermes-azure-files-plugin` — Azure-native
  `toolset` plugin for Hermes Agent providing Azure Blob Storage and Azure
  Files access via two complementary paths.
- **Mount path** (`azurefiles_*` tools):
  - `azurefiles_mount` — mount a blob container or Azure Files share locally
    via BlobFuse2 (preferred), Azure Files NFS 4.1, or SMB.
  - `azurefiles_unmount`, `azurefiles_status`, `azurefiles_setup`.
  - Managed-Identity-only auth for mount path (account keys intentionally not
    exposed).
- **SDK path** (`blob_*` tools): `blob_upload`, `blob_download`, `blob_list`
  built on `azure-storage-blob` + `DefaultAzureCredential`.
- `register(ctx)` entry point + quickstart example.
- Shell-safe container / mount name validation and secret-redacting tool
  outputs.
- 30 passing tests.

[0.1.0]: https://github.com/turbo998/hermes-azure-files-plugin/releases/tag/v0.1.0
