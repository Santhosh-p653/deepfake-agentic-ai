
#   Troubleshooting Guide — Deepfake Agentic AI

This document captures real issues encountered during development and their solutions.
Kept as a personal reference — updated as new issues are resolved.

---

## 1. Docker Configuration Problems

**Problem:**
While setting up Docker, zombie processes occupied ports, causing service failures and manual
configuration overhead.

**Observations:**
- Multiple zombie processes were using required ports
- Manual configuration and cleanup consumed significant time

**Root Cause:**
- Docker socket and service conflicts from previous executions
- Unclean socket files or failed systemd services

**Solution:**
Manually stop Docker services, reset failed states, remove socket files, and restart Docker.

```bash
sudo systemctl stop docker
sudo systemctl stop docker.socket
sudo systemctl disable docker.socket
sudo systemctl reset-failed
sudo rm -f /var/run/docker.sock
sudo systemctl start docker
```

> ⚠️ Personal note: Docker zombie processes still appear occasionally. Keeping this section
> as a self-reference — handle manually when it comes up.

---

## 2. Image Communication Gap Between Agents and API

**Problem:**
The API service was unable to communicate with the agents container.

**Observed Errors:**
- `NameResolutionError`
- `HTTPConnectionPool Max retries exceeded`
- Agents container not visible in `docker network inspect`

**Root Cause:**
The agents container was implemented as a job-based module:
1. Executes `task_runner.py`
2. Completes execution
3. Exits immediately

Because the container exited:
- It was no longer attached to the Docker Compose network
- Docker DNS could not resolve the service name
- API could not communicate with agents

**Solution:**
Converted agents from a job-based container to a service-based container.

**Changes Made:**
1. Added a Flask application to the agents container
2. Exposed `/run` endpoint to trigger task execution
3. Exposed `/ping` endpoint for health checks
4. Ensured the container runs persistently
5. Updated API to call `http://agents:8123/run`

```
Before: API → docker run agents (job container, exits immediately)
After:  API → HTTP request → agents service (persistent container)
```

---

## 3. GitHub Actions — API Startup Failure in CI

**Problem:**
`curl -f http://localhost:8000/ping` returning `connection refused` in the network audit
workflow even though the start step appeared to succeed.

**Root Cause:**
Two issues combined:
- `cd api && uvicorn api.main:app` — wrong working directory caused module resolution failure
- `python-magic` requires `libmagic1` system library which is not present on GitHub Actions
  runners by default, causing a silent import crash on startup

**Solution:**
```yaml
- name: Install system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y libmagic1

- name: Start API
  run: |
    mkdir -p logs
    uvicorn api.main:app --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
    sleep 8
    cat /tmp/uvicorn.log
```

Key fixes:
- Run `uvicorn` from repo root, not from inside `api/`
- Install `libmagic1` before pip installs
- Redirect uvicorn output to a log file and print it — makes silent crashes visible

---

## 4. PostgreSQL FOR UPDATE with Aggregate Function

**Problem:**
`psycopg2.errors.FeatureNotSupported: FOR UPDATE is not allowed with aggregate functions`
when checking the temp file cap on upload.

**Root Cause:**
PostgreSQL does not allow `SELECT COUNT(*) ... FOR UPDATE` directly — you cannot combine
aggregate functions with row-level locking in the same query.

**Solution:**
Wrap the locked select in a subquery, count the outer result:

```sql
-- Wrong
SELECT COUNT(*) FROM media_uploads
WHERE status IN ('temp_stored', 'processing')
FOR UPDATE

-- Correct
SELECT COUNT(*) FROM (
    SELECT id FROM media_uploads
    WHERE status IN ('temp_stored', 'processing')
    FOR UPDATE
) AS locked_rows
```

**Tradeoff:**
Slightly more verbose but necessary. The subquery locks the rows first, then the outer
query counts them. This is the correct pattern for atomic cap enforcement under concurrent load.

---

## 5. MinIO Invalid Bucket Name

**Problem:**
`S3Error: InvalidBucketName — The specified bucket is not valid` on API startup when
calling `ensure_bucket()`.

**Root Cause:**
MinIO does not allow hyphens in bucket names in certain configurations. The bucket name
`deepfake-media` was rejected.

**Solution:**
Renamed bucket to `deepfakemedia` in both `.env` and `minio_client.py`:

```env
MINIO_BUCKET=deepfakemedia
```

---

## 6. Temp Path Mismatch After Startup Cleanup

**Problem:**
After a crash recovery, some `failed` rows in the DB still had their temp files sitting
in `/app/tmp`, causing disk buildup.

**Root Cause:**
The startup cleanup routine was only resetting the DB status to `failed` for stuck
`processing` rows but not deleting the corresponding file from disk.

**Solution:**
Updated `cleanup_on_startup()` in `temp_manager.py` to delete the temp file before
updating the DB status:

```python
for row in stuck:
    if row.temp_path:
        delete_from_temp(row.temp_path)  # delete file first
    update_status(db, row.id, ProcessingStatus.failed, processed_at=datetime.utcnow())
```

Rule: DB is source of truth, but filesystem must be cleaned before status is updated —
never leave a file on disk with a `failed` DB row pointing to it.
```



