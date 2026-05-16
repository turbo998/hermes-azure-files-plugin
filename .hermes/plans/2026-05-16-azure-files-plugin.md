# hermes-azure-files-plugin — 设计与实施计划

## 对标
原 `hermes-s3files-plugin` v2.0.0 (Allen Tang) — `type: toolset`
通过 `mount -t s3files` + amazon-efs-utils，把 S3 当本地 NFS 挂载。
4 工具：`s3files_mount / s3files_unmount / s3files_status / s3files_setup`

## Azure 等价映射
| 原工具 | Azure 等价 | 实现 |
|---|---|---|
| s3files_mount (NFS) | azurefiles_mount | (a) Blob 容器 → BlobFuse2 (推荐) (b) Azure Files NFS 4.1 → mount -t nfs (c) Azure Files SMB → mount -t cifs |
| s3files_unmount | azurefiles_unmount | sudo umount |
| s3files_status | azurefiles_status | 解析 /proc/mounts 找 blobfuse2 / azure files mounts |
| s3files_setup | azurefiles_setup | 装 blobfuse2 (apt/Microsoft repo) + 校验 az login / Managed Identity |

## 现代化增强（SDK 直调，避免 mount anti-pattern）
| 新工具 | 功能 | 实现 |
|---|---|---|
| blob_upload | 上传本地文件到容器 | azure-storage-blob + DefaultAzureCredential |
| blob_download | 下载 blob 到本地路径 | 同上 |
| blob_list | 列容器中 blob | 同上，支持 prefix |

## 认证
- 推荐：`DefaultAzureCredential`（Managed Identity / az CLI / env）
- 备选：account_key (env `AZURE_STORAGE_KEY`) 或 connection_string

## 项目结构
```
hermes-azure-files-plugin/
  pyproject.toml
  plugin.yaml
  LICENSE
  README.md
  hermes_azure_files/
    __init__.py        # register(ctx)
    mount.py           # blobfuse2 / azure files mount/unmount/status/setup
    blob.py            # SDK upload/download/list
    auth.py            # DefaultAzureCredential helper
  tests/
    conftest.py        # subprocess mock fixture
    test_mount.py
    test_blob.py
    test_register.py
  examples/
    quickstart.py
```

## TDD 批次
- **批1**: 脚手架 + plugin.yaml + pyproject + LICENSE + README 框架
- **批2**: mount.py + tests（subprocess mock）
- **批3**: blob.py + tests（azure SDK mock — 全部 NotImplementedError stub + mock client 路径，与 foundry-memory plugin 一致）
- **批4**: __init__.py register + quickstart + final pytest + commit

## 工具命名空间
`azurefiles_*` 对应 mount 类；`blob_*` 对应 SDK 类。区分清晰。
