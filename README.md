## Docker Containerizer for Mesos

This repo contains a proof of concept external containerizer for Mesos. There are two components;

- The docker containerizer script itself
- A test framework for launching one-time throw away docker containers on a Mesos cluster

#### Launcher

```sh
MESOS_BUILD_DIR="" ./bin/docker-launcher --help
```