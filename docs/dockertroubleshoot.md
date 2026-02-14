Issue: Configuration while Docker setup

1. I  recently gone through many  zombie process occupied my  ports .
2. I spend more time on configuring these things manually.
3. So I think,manually stop the docker socket and docker  and set that systemctl reset option disabled.
4. Remove socket  users list frequently.But there is a tradeoff of erasing logs.
5. Start the docker again.

```
sudo systemctl stop docker
sudo systemctl stop docker.socket
sudo systemctl disable docker.socket
sudo systemctl reset-failed
sudo rm -f /var/run/docker.sock
sudo systemctl start docker

```

Verify the setup :
```
systemctl status docker
docker info
docker ps
docker ps -a
```
Issue:Image Communication gap Between agents and api

Problem:
 The API service was unable to communicate with the agents conatiner.

Observed Errors:

1. NameResolutionError
2. HTTPConnectionPool Max retries exceeded
3. Agents conatiner not visible in docker network inspect

Root Cause:

The agents container was implemented as a job based module:
1. It executes task_runner.py
2. Completes execution
3. Exited immediately
Because the conatiner exited:
1. It was no longer attached to the Docker compose network
2. Docker NDS could not resolvve the service name
3. API could not communicate with agents

SOLUTION:

Converted agents from a job-based container to a service-based container.

CHANGES MADE:
1. Added Flask application to agents.
2. Exposed /run endpoint to trigger task execution
3. Exposed /ping command for health check
4. Ensured container runs  persistently
5. Updated API to call ``http:agents:8123/run``
 
