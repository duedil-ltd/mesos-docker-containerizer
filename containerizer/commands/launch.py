"""
 _                        _
| | __ _ _   _ _ __   ___| |__
| |/ _` | | | | '_ \ / __| '_ \
| | (_| | |_| | | | | (__| | | |
|_|\__,_|\__,_|_| |_|\___|_| |_|

Containerizer subcommand to launch a new container.
"""

import os
import logging
from urlparse import urlparse

from containerizer import app, recv_proto, container_lock
from containerizer.docker import invoke_docker
from containerizer.proto import Launch
from containerizer.fetcher import fetch_uris

logger = logging.getLogger(__name__)


@app.command()
def launch():
    """
    Launch a new Mesos executor in a Docker container.
    """

    launch = recv_proto(Launch)

    # Acquire a lock for this container
    with container_lock(launch.container_id.value):

        logger.info("Preparing to launch container %s", launch.container_id.value)

        try:
            run_arguments = build_docker_args(launch)
        except Exception, e:
            logger.error("Caught exception: %s", e)
            raise  # Re-raise the exception

        logger.info("Launching docker container")
        _, _, return_code = invoke_docker("run", run_arguments)

        if return_code > 0:
            logger.error("Failed to launch container")
            exit(1)


def build_docker_args(launch):

    # Build up the docker arguments
    arguments = []

    # Set the container ID
    arguments.extend([
        "--name", launch.container_id.value
    ])

    container_info = None

    # Figure out where the executor is
    if launch.HasField("executor_info"):
        executor = launch.executor_info.command.value
        uris = launch.executor_info.command.uris

        # Environment variables
        for env in launch.executor_info.command.environment.variables:
            arguments.extend([
                "-e",
                "%s=%s" % (env.name, env.value)
            ])

        if launch.executor_info.HasField("container"):
            container_info = launch.executor_info.container
    else:
        logger.info("No executor given, launching with mesos-executor")
        executor = "%s/mesos-executor" % os.environ['MESOS_LIBEXEC_DIRECTORY']
        uris = launch.task_info.command.uris

        # Environment variables
        for env in launch.task_info.command.environment.variables:
            arguments.extend([
                "-e",
                "%s=%s" % (env.name, env.value)
            ])

    # Pull out the ContainerInfo from either the task or the executor
    if launch.executor_info.HasField("container"):
        container_info = launch.executor_info.container
    elif launch.task_info.HasField("container"):
        container_info = launch.task_info.container

    # Pull out DockerInfo if it's there
    docker_info = None
    if container_info and container_info.type == 1:  # ContainerInfo.Type.DOCKER
        docker_info = container_info.docker

    # Configure the docker network to share the hosts
    net = "host"
    if docker_info:
        if docker_info.network == 1:  # DockerInfo.Network.HOST
            pass
        elif docker_info.network == 2:  # DockerInfo.Network.BRIDGE
            net = "bridge"
        elif docker_info.network == 3:  # DockerInfo.Network.NONE
            net = "none"
        else:
            raise Exception("Unsupported docker network type")

    arguments.extend([
        "--net", "%s" % net.lower()
    ])

    # Configure the user
    if launch.HasField("user"):
        arguments.extend([
            "-u", launch.user
        ])

    # Download the URIs
    logger.info("Fetching URIs")
    if fetch_uris(launch.directory, uris) > 0:
        raise Exception("Mesos fetcher returned bad exit code")

    # Set the resource configuration
    cpu_shares = 0
    max_memory = 0
    ports = set()

    # Grab the resources from the task and executor
    resource_sets = [launch.task_info.resources,
                     launch.executor_info.resources]
    for resources in resource_sets:
        for resource in resources:
            if resource.name == "cpus":
                cpu_shares += float(resource.scalar.value)
            if resource.name == "mem":
                max_memory += int(resource.scalar.value)
            if resource.name == "ports":
                for port_range in resource.ranges.range:
                    for port in xrange(port_range.begin, port_range.end + 1):
                        ports.add(port)

    if cpu_shares > 0.0:
        arguments.extend(["-c", str(int(cpu_shares * 1024))])
    if max_memory > 0:
        arguments.extend(["-m", "%dm" % max_memory])
    if len(ports) > 0:
        for port in ports:
            arguments.extend(["-p", ":%i" % port])

    logger.info("Configured with executor %s" % executor)

    # Set the MESOS_DIRECTORY environment variable to the sandbox mount point
    arguments.extend(["-e", "MESOS_DIRECTORY=/mesos-sandbox"])

    # Pass through the rest of the mesos environment variables
    mesos_env = ["MESOS_FRAMEWORK_ID", "MESOS_EXECUTOR_ID",
                 "MESOS_SLAVE_ID", "MESOS_CHECKPOINT",
                 "MESOS_SLAVE_PID", "MESOS_RECOVERY_TIMEOUT",
                 "MESOS_NATIVE_LIBRARY"]
    for key in mesos_env:
        if key in os.environ:
            arguments.extend(["-e", "%s=%s" % (key, os.environ[key])])

    # Add the sandbox directory
    arguments.extend(["-v", "%s:/mesos-sandbox" % (launch.directory)])
    arguments.extend(["-w", "/mesos-sandbox"])

    # Populate the docker arguments with any volumes to be mounted
    if container_info:
        for volume in container_info.volumes:
            volume_args = volume.container_path
            if volume.HasField("host_path"):
                volume_args = "%s:%s" % (
                    volume.host_path,
                    volume.container_path
                )
            if volume.HasField("mode"):
                if not volume.HasField("host_path"):
                    raise Exception("Host path is required with mode")
                if volume.mode == Volume.Mode.RW:
                    volume_args += ":rw"
                elif volume.mode == Volume.Mode.RO:
                    volume_args += ":ro"
                else:
                    raise Exception("Unsupported volume mode")

            arguments.extend(["-v", volume_args])

    # Populate the docker arguments with any port mappings
    if docker_info:
        for port_mapping in docker_info.port_mappings:
            if port_mapping.host_port not in ports:
                raise Exception("Port %i not included in resources" % port_mapping.host_port)
            port_args = "%i:%i" % (
                port_mapping.host_port,
                port_mapping.container_port
            )

            if port_mapping.HasField("protocol"):
                port_args += "/%s" % (port_mapping.protocol.lower())

            arguments.extend(["-p", port_args])

        if docker_info.privileged:
            arguments.append('--privileged')

        if docker_info.parameters:
            for param in docker_info.parameters:
                if param.key:
                    arguments.append(param.key)
                if param.value:
                    arguments.append(param.value)

    extra_args = []
    if docker_info:
        image = docker_info.image
    else:
        image = None
        if launch.HasField("executor_info"):
            image = launch.executor_info.command.container.image
            for option in launch.executor_info.command.container.options:
                extra_args.extend(option.split(" "))
        else:
            image = launch.task_info.command.container.image
            for option in launch.task_info.command.container.options:
                extra_args.extend(option.split(" "))

    if not image:
        image = os.environ["MESOS_DEFAULT_CONTAINER_IMAGE"]
    if not image:
        raise Exception("No default container image")

    # Parse the container image
    url = urlparse(image)
    if url.netloc:
        docker_image = "%s/%s" % (url.netloc, url.path.lstrip("/"))
    else:
        docker_image = url.path

    # Pull the image
    logger.info("Pulling latest docker image: %s", docker_image)
    _, _, return_code = invoke_docker("pull", [docker_image])
    if return_code > 0:
        raise Exception("Failed to pull image (%d)", return_code)

    run_arguments = [
        "-d",  # Enable daemon mode
    ]

    run_arguments.extend(arguments)
    run_arguments.extend(extra_args)
    run_arguments.append(docker_image)
    run_arguments.extend(["sh", "-c"])
    run_arguments.append(executor + " >> /mesos-sandbox/docker_stdout 2>> /mesos-sandbox/docker_stderr")

    return run_arguments
