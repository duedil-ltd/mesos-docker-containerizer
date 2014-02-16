## Docker Containerizer for Mesos

This repo contains a proof of concept external containerizer for Mesos. There are two components;

- The docker containerizer script itself
- A test framework for launching one-time throw away docker containers on a Mesos cluster

**Note: As of now, this requires mesos to be compiled from source with [RR(17567)](https://reviews.apache.org/r/17567/) applied to master.**

### Containerizer

Docs to come.

### Launcher

The launcher connects to a mesos cluster configured to use the `bin/docker-containerizer` external containerizer.

```sh
MESOS_BUILD_DIR="/path/to/mesos/build" ./bin/launch-container --help
```
