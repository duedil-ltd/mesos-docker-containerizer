## Docker Containerizer for Mesos

This project is an implementation of an External Containerizer for [Apache Mesos](http://mesos.apache.org/), that allows Mesos Executors/Tasks to be launched inside a Docker container. This is especially useful as a mechanism for managing system dependencies, since you no longer need to ensure all of the Mesos slaves have everything installed.

*Note: The External Containerizer is an unreleased feature of Mesos. To run this, mesos 0.19.0 is required.*

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

##### Launching a docker container

As of version 0.19.0 a new `CommandInfo.ContainerInfo` message has been introduced. This message is designed to outline any attributes to pass to the containerizer when launching a task or executor, such as the docker image. If you don't specify this, the default docker image will be used.

Images are specified using the `docker:///` URL scheme. For example use `docker:///ubuntu:13.04` to launch the 13.04 ubuntu docker image in your container. If you're using a custom private registry, you can specify the registry URL also by using `docker://my.registry.com/foo/bar:tag`.

**Note: Unless you're using one of the pure-language mesos frameworks (not released yet) you'll need to ensure the docker image you use has a recent version of Mesos installed. This is to allow running executors to gain access to the Mesos native libraries.**

```proto
message TaskInfo {
  ...
  optional CommandInfo command = 7;
  ...
}

message CommandInfo {
  ...
  // Describes a container.
  // Not all containerizers currently implement ContainerInfo, so it
  // is possible that a launched task will fail due to supplying this
  // attribute.
  // NOTE: The containerizer API is currently in an early beta or
  // even alpha state. Some details, like the exact semantics of an
  // "image" or "options" are not yet hardened.
  // TODO(tillt): Describe the exact scheme and semantics of "image"
  // and "options".
  message ContainerInfo {
    // URI describing the container image name.
    required string image = 1;

    // Describes additional options passed to the containerizer.
    repeated string options = 2;
  }

  // NOTE: MesosContainerizer does currently not support this
  // attribute and tasks supplying a 'container' will fail.
  optional ContainerInfo container = 4;
  ...
}
```
### Vagrant Example

The `./example` folder contains a `Vagrantfile` that launches a vagrant VM ready and waiting for testing the containerizer.

- Installs docker
- Downloads and compiles mesos (at the right version) into `/opt/mesos`
- Includes the containerizer code into `/opt/mesos-docker-containerizer`

The VM doesn't launch a running mesos master or slave, you'll need to log in via `vagrant ssh` and use the `/opt/mesos/build/bin/*` tools to do that yourself.
