# Docker Troubleshooting Guide

This document captures common issues and solutions encountered while setting up Docker and running the Deepfake-Agentic-AI project.  

---

## 1. Docker Configuration Problems

**Problem:**  
While setting up Docker, many zombie processes occupied ports, causing service failures and manual configuration overhead.

**Observations:**

- Multiple zombie processes were using required ports.
- Manual configuration and cleanup consumed significant time.

**Root Cause:**

- Docker socket and service conflicts from previous executions.
- Unclean socket files or failed systemd services.

**Solution:**

Manually stop Docker services, reset failed states, remove socket files, and restart Docker.

**Steps Taken:**

```bash
sudo systemctl stop docker
sudo systemctl stop docker.socket
sudo systemctl disable docker.socket
sudo systemctl reset-failed
sudo rm -f /var/run/docker.sock
sudo systemctl start docker
```
# Issue: Image Communication Gap Between Agents and API

## Problem
The API service was unable to communicate with the agents container.

## Observed Errors

1. `NameResolutionError`
2. `HTTPConnectionPool Max retries exceeded`
3. Agents container not visible in `docker network inspect`

## Root Cause

The agents container was implemented as a **job-based module**:

1. Executes `task_runner.py`
2. Completes execution
3. Exits immediately

Because the container exited:

1. It was no longer attached to the Docker Compose network
2. Docker DNS could not resolve the service name
3. API could not communicate with agents

## Solution

Converted agents from a **job-based container** to a **service-based container**.

## Changes Made

1. Added a Flask application to the agents container.
2. Exposed `/run` endpoint to trigger task execution.
3. Exposed `/ping` endpoint for health checks.
4. Ensured the container runs **persistently**.
5. Updated API to call:

```
http://agents:8123/run
```
