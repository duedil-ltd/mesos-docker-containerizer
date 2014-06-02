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

        logger.info("Prepraring to launch container %s", launch.container_id.value)

        # Build up the docker arguments
        arguments = []

        # Set the container ID
        arguments.extend([
            "--name", launch.container_id.value
        ])

        # Configure the user
        if launch.HasField("user"):
            arguments.extend([
                "-u", launch.user
            ])

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

        # Download the URIs
        logger.info("Fetching URIs")
        if fetch_uris(launch.directory, uris) > 0:
            logger.error("Mesos fetcher returned bad exit code")
            exit(1)

        # Link the mesos native library
        native_library = os.environ['MESOS_NATIVE_LIBRARY']
        arguments.extend(["-v", "%s:/usr/lib/%s" % (native_library, os.path.basename(native_library))])

        # Set the resource configuration
        for resource in launch.task_info.resources:
            if resource.name == "cpus":
                arguments.extend(["-c", str(int(resource.scalar.value * 256))])
            if resource.name == "mem":
                arguments.extend(["-m", "%dm" % (int(resource.scalar.value))])
            if resource.name == "ports":
                for port_range in resource.ranges.range:
                    for port in xrange(port_range.begin, port_range.end + 1):
                        arguments.extend(["-p", "%i:%i" % (port, port)])

        logger.info("Configured with executor %s" % executor)

        # Add the sandbox directory
        arguments.extend(["-v", "%s:/mesos-sandbox" % (launch.directory)])
        arguments.extend(["-w", "/mesos-sandbox"])

        # Set the MESOS_DIRECTORY environment variable to the sandbox mount point
        arguments.extend(["-e", "MESOS_DIRECTORY=/mesos-sandbox"])

        # Pass through the rest of the mesos environment variables
        mesos_env = ["MESOS_FRAMEWORK_ID", "MESOS_EXECUTOR_ID",
                     "MESOS_SLAVE_ID", "MESOS_CHECKPOINT",
                     "MESOS_SLAVE_PID", "MESOS_RECOVERY_TIMEOUT"]
        for key in mesos_env:
            if key in os.environ:
                arguments.extend(["-e", "%s=%s" % (key, os.environ[key])])

        # Parse the container image
        image = None
        extra_args = []
        if launch.task_info.HasField("executor"):
            image = launch.executor_info.command.container.image
            for option in launch.executor_info.command.container.options:
                extra_args.append(option.split(" "))
        else:
            image = launch.task_info.command.container.image
            for option in launch.task_info.command.container.options:
                extra_args.append(option.split(" "))

        if not image:
            image = os.environ["MESOS_DEFAULT_CONTAINER_IMAGE"]
        if not image:
            logger.error("No default container image")
            exit(1)

        url = urlparse(image)
        image = ""
        if url.netloc:
            image = url.netloc
        image += url.path


        # TODO(tarnfeld): Locking

        run_arguments = [
            "-d", # Enable daemon mode
            "--net=bridge" # Bridge the network with the host
        ]

        run_arguments.extend(arguments)
        run_arguments.extend(extra_args)
        run_arguments.extend(["-e", "GLOG_v=5"])
        run_arguments.append(image)
        run_arguments.extend(["sh", "-c"])
        run_arguments.append(executor + " >> stdout 2>>stderr")

        logger.info("Launching docker container")
        _, _, return_code = invoke_docker("run", run_arguments)

        if return_code > 0:
            logger.error("Failed to launch container")
            exit(1)
