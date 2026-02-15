# Docker Setup Issues and Fixes

During the setup of the Deepfake-Agentic-AI project, the following issues were observed:

## Issues Faced

1. **DNS Name Resolution Error**  
   - Occurred every time the session restarted.
   - Prevented containers from resolving service names properly.

2. **Docker Daemon Connection Error**  
   - Docker sometimes ran in a conflicting process.
   - Caused failures in container startup.

3. **Pulling Postgres Images Failures**  
   - Network or Docker misconfiguration caused image pull errors.

4. **Socket Permission Issues**  
   - `/var/run/docker.sock` permission problems blocked container communication.

---

## Solutions / Workarounds

**Step 1: Lock DNS Configuration**

```bash
sudo nano /etc/resolv.conf
sudo chattr +i /etc/resolv.conf
```
# From Windows Terminal
wsl --shutdown

# From WSL Terminal
sudo dockerd
