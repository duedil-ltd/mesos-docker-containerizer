## Docker Containerizer for Mesos

This repo contains a proof of concept external containerizer for Mesos. There are two components;

- The docker containerizer script itself
- A test framework for launching one-time throw away docker containers on a Mesos cluster

**Note: As of now, this requires mesos to be compiled from source with [RR(17567)](https://reviews.apache.org/r/17567/) applied to master.**
**Note: You also need to manually hard code `MESOS_BUILD_DIR` into `bin/docker-containerizer` for now as it's not passed through by mesos.**

### Containerizer

Docs to come.

### Launcher

The launcher connects to a mesos cluster configured to use the `bin/docker-containerizer` external containerizer.

```sh
$ MESOS_BUILD_DIR="/path/to/mesos/build" bin/launch-container -m "192.168.4.1:5050" -i ubuntu/ubuntu sleep 1
> I0216 09:08:18.470973 2040767248 sched.cpp:121] Version: 0.19.0
> I0216 09:08:18.472090 187219968 sched.cpp:217] New master detected at master@192.168.4.1:5050
> I0216 09:08:18.472190 187219968 sched.cpp:225] No credentials provided. Attempting to register without authentication
> I0216 09:08:18.472769 152768512 sched.cpp:391] Framework registered with 2014-02-16-08:51:32-17082560-5050-2432-0006
> Registered framework
> Offered resources
> Launching task
> Received task status update
> Received task status update
> Container task finished successfully
> I0216 09:08:20.686316 151695360 sched.cpp:730] Stopping framework '2014-02-16-08:51:32-17082560-5050-2432-0006'
```
