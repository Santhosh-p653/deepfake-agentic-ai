WHAT I FACE THROUGH DURING DOCKER CONFIGURATION:

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

