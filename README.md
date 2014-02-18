## Docker Containerizer for Mesos

This is an implementation of a Pluggable Containerizer for [Apache Mesos](http://mesos.apache.org/), that allows launching containers through Docker instead of standard unix processes or cgroups. 

##### How does this compare to [mesosphere/mesos-docker](https://github.com/mesosphere/mesos-docker)? 

The mesosphere implementation of docker is aimed largely at being used with [mesosphere/marathon](https://github.com/mesosphere/marathon) which is a framework for long-running processes on mesos. It requires the framework to have a much more explicit knowledge of the existence of docker, whereas the new "pluggable containerizer" feature of mesos allows the framework to be container agnostic.

For more details on the benefits of external/pluggable containerizers read over the review request linked above.

*Note: The "pluggable containerizer" feature of mesos is still in development, to use this you need to apply the review request [r17567](https://reviews.apache.org/r/17567/) to the latest master, and recompile.*


### Getting Started

As mentioned above, you need to apply the "pluggable containerizer" implementation to the latest master of mesos before being able to use this. Once done so, start a mesos master and slave like below.


#### Configuration

1. Copy `./bin/environment.sh.dist` to `./bin/environment.sh`
2. Fill in the `MESOS_BUILD_DIR` environment variable in `./bin/environment.sh`


##### Master

First, launch a mesos master.


```shell
$ ./bin/mesos-master.sh --ip=127.0.0.1
...
```


##### Mesos Slave(s)

At the moment, you must specify the default external containerizer when launching the slave. This is to be improved such that a single slave is capable of running multiple types of containers.


```shell
$ ./bin/mesos-slave.sh --master=127.0.0.1:5050 \
                       --isolation="external" \
                       --containerizer_path="/path/to/this/repo/bin/docker-containerizer"
```

With the above slave, any tasks that are sent to the slave *must* contain container information otherwise they will be unable to run.


##### Launching a docker container

If you're not writing your own framework and just want to test this out, or simply need to launch one-off containers on a mesos cluster, included here is an implementation of a mesos framework just for that.

```shell
$ ./bin/launch-container --master=127.0.0.1:5050 \
                         ubuntu:13.10 \
                         "echo before && sleep 5 && echo after"
```

This will pull and launch a docker container for `ubuntu:13.10` and run the bash commands given. The output from the container isn't written to the terminal, but can be retrieved through viewing the task's sandbox is the mesos web UI.


### Custom Executors

If you need to run something a little more advanced than a simple bash command (such as modifying an existing framework+executor to run in a docker container) the docker containerizer does support custom executors.

When a custom executor command is provided with the `TaskInfo` object, the executor will be launched *within* the docker container. This means your container image needs to have the correct version of mesos and your executor already installed.