The issues I faced during setting up this configuration are
1.DNS Name resolution error .I got everytime when the session restarts.
2.Docker daemon connection error. Like docker runs in some process.
3.Pulling postgres images failures.
4.Socket Permission Issues.

```
sudo nano /etc/rresolv.conf
sudo chattr +i /etc/resolv.conf
wsl --shutdown
sudo dockerd
```
