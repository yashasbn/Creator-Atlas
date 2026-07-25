# SigNoz Native Windows Setup Guide

If you are trying to run SigNoz natively on Windows using Docker Desktop, you may run into a few specific issues with the newer "Foundry" installation method or WSL bridging, as well as NTFS file-locking crashes in ClickHouse.

This guide provides a bulletproof way to spin up SigNoz 100% natively on Windows using standard `docker compose`, bypassing WSL and fixing the known bugs automatically.

## Prerequisites
- Docker Desktop installed and running on Windows
- Git installed on Windows
- PowerShell

## Automated PowerShell Setup

Open a normal Windows PowerShell window, navigate to the folder where you want to install SigNoz (e.g., alongside your project), and run these commands one by one:

```powershell
# 1. Create a directory and clone a stable release that supports standalone Docker Compose
mkdir signoz-native
cd signoz-native
git clone -b v0.45.0 https://github.com/SigNoz/signoz.git
cd signoz/deploy/docker/clickhouse-setup

# 2. Fix Zookeeper Image (Bitnami removed the original 3.7.1 tag from Docker Hub)
(Get-Content docker-compose.yaml) -replace 'image: bitnami/zookeeper:3.7.1', 'image: zookeeper:3.8' | Set-Content docker-compose.yaml
(Get-Content docker-compose.yaml) -replace 'ZOO_SERVER_ID=1', 'ZOO_MY_ID=1' | Set-Content docker-compose.yaml

# 3. Fix Windows NTFS File Permission Crash (ClickHouse cannot rename files on Windows bind mounts)
(Get-Content docker-compose.yaml) -replace '- \./data/clickhouse/:/var/lib/clickhouse/', '- clickhouse-data:/var/lib/clickhouse/' | Set-Content docker-compose.yaml
Add-Content -Path docker-compose.yaml -Value "`nvolumes:`n  clickhouse-data:"

# 4. Spin it up natively!
docker compose up -d
```

## What this script does:
1. **Bypasses Foundry & WSL:** We clone the `v0.45.0` tag which contains the official raw `docker-compose.yaml` files before they were removed in favor of Foundry.
2. **Fixes Zookeeper:** The official `docker-compose.yaml` tries to pull `bitnami/zookeeper:3.7.1`, which was deleted from Docker Hub. We hot-swap it with the official `zookeeper:3.8` image and adjust the environment variables accordingly.
3. **Fixes ClickHouse Migrator Crash:** ClickHouse crashes on Windows if its data folder is bind-mounted directly to the `C:` drive due to Windows file-locking. We swap the bind mount for a Docker **Named Volume** (`clickhouse-data`), which uses a virtual Linux filesystem and completely prevents the crash.

## Accessing the UI
Once the containers finish starting up, you can access the SigNoz dashboard at:
👉 **http://localhost:3301**

If you see an "Oops!!! Something went wrong" message on a fresh install, this simply means the database is 100% empty. Start your application to push your first telemetry data to `localhost:4318`, and the dashboard will instantly populate!
