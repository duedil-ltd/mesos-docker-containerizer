## Docker Containerizer for Mesos

[![Build Status](https://travis-ci.org/duedil-ltd/mesos-docker-containerizer.svg?branch=master)](https://travis-ci.org/duedil-ltd/mesos-docker-containerizer)

This project is an implementation of an External Containerizer for [Apache Mesos](http://mesos.apache.org/), that allows Mesos Executors/Tasks to be launched inside a Docker container. This is especially useful as a mechanism for managing system dependencies, since you no longer need to ensure all of the Mesos slaves have everything installed.

This containerizer supports both the historic [`CommandInfo.ContainerInfo`](https://github.com/apache/mesos/blob/0.20.1/include/mesos/mesos.proto#L209-L228) protobuf message and the new root [`ContainerInfo`](https://github.com/apache/mesos/blob/0.20.1/include/mesos/mesos.proto#L849-L881) message. Effectively this containerizer can also be used in conjunction with the built-in mesos/docker containerizer released in 0.20.0.

### Getting Started

#### Configuration

You can configure various attributes of the containerizer using environment variables. If you wish to modify these, copy `./bin/environment.sh.dist` to `./bin/environment.sh` and change the values.

##### Mesos Master

First, launch a mesos master.


```shell
$ ./bin/mesos-master.sh --ip=127.0.0.1
...
```

##### Mesos Slave(s)

You now need to ensure the slave is configured to use `external` containerization, and give it the path to the docker containerizer.

```shell
$ ./bin/mesos-slave.sh --master=127.0.0.1:5050 \
                       --isolation="external" \
                       --containerizer_path="/path/to/this/repo/bin/docker-containerizer"
```

With the above slave, any tasks that are sent to the slave *must* contain container information otherwise they will be unable to run. You can configure a default image to allow users to submit tasks without this information, with `--default_container_image`.

### Vagrant Example

The `./example` folder contains a `Vagrantfile` that launches a vagrant VM ready and waiting for testing the containerizer.

- Installs docker
- Downloads and compiles mesos (at the right version) into `/opt/mesos`
- Includes the containerizer code into `/opt/mesos-docker-containerizer`

The VM doesn't launch a running mesos master or slave, you'll need to log in via `vagrant ssh` and use the `/opt/mesos/build/bin/*` tools to do that yourself.
