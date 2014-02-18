#!/usr/bin/env python

#      _            _                                  _        _                 _
#   __| | ___   ___| | _____ _ __       ___ ___  _ __ | |_ __ _(_)_ __   ___ _ __(_)_______ _ __
#  / _` |/ _ \ / __| |/ / _ \ '__|____ / __/ _ \| '_ \| __/ _` | | '_ \ / _ \ '__| |_  / _ \ '__|
# | (_| | (_) | (__|   <  __/ | |_____| (_| (_) | | | | || (_| | | | | |  __/ |  | |/ /  __/ |
#  \__,_|\___/ \___|_|\_\___|_|        \___\___/|_| |_|\__\__,_|_|_| |_|\___|_|  |_/___\___|_|
#
#  Pluggable containerizer implementation for Docker with Mesos
#

import subprocess
import argparse
import time
import sys
import os

import google
import mesos_pb2

# Base docker command
_BASE_DOCKER_COMMAND = ["docker", "-H", "192.168.4.2:7070"]


def launch(container, args):
    """Launch a new docker container, don't wait for the container to terminate."""

    # Read the TaskInfo from STDIN
    try:
        data = sys.stdin.read()
        if len(data) <= 0:
            print >> sys.stderr, "Expected protobuf over stdin. Received 0 bytes."
            return 1

        task = mesos_pb2.TaskInfo()
        task.ParseFromString(data)
    except google.protobuf.message.DecodeError:
        print >> sys.stderr, "Could not deserialise external container protobuf"
        return 1

    # Build the docker invocation
    command = []

    # If there's no executor command, wrap the docker invoke in our own
    if not task.executor.command.value:
        executor_path = os.path.join(
            os.path.dirname(
                os.path.realpath(__file__)
            ),
            "bin/docker-executor"
        )

        command.append(executor_path)

    command.extend(_BASE_DOCKER_COMMAND)

    for docker_arg in args.docker_arg:
        command.extend(docker_arg)

    command.append("run")

    # Add any environment variables
    for env in task.command.environment.variables:
        command.extend([
            "-e",
            "%s=%s" % (env.name, env.value)
        ])

    # Set the container ID
    command.extend([
        "-name", container
    ])

    # Set the resource configuration
    # TODO

    # Figure out what command to execute in the container
    # TODO: Test with executors that are fetched from a remote
    if task.executor.command.value:
        container_command = task.executor.command.value
    else:
        container_command = task.command.value

    # Put together the rest of the invoke
    command.append(task.command.container.image)
    command.extend(["/bin/sh", "-c", container_command])

    print >> sys.stderr, "Launching docker process with command %r" % (command)

    # Write the stdout/stderr of the docker container to the sandbox
    sandbox_dir = os.environ["MESOS_DIRECTORY"]

    stdout_path = os.path.join(sandbox_dir, "stdout")
    stderr_path = os.path.join(sandbox_dir, "stderr")

    with open(stdout_path, "w") as stdout:
        with open(stderr_path, "w") as stderr:
            proc = subprocess.Popen(command, stdout=stdout, stderr=stderr)
            return_code = proc.wait()

    print >> sys.stderr, "Docker container %s exited with return code %d" % (container, return_code)
    return return_code


def update(container, args):
    """Update an existing container."""

    # TODO
    return 0


def usage(container, args):
    """Retrieve the resource usage of a given container."""

    # TODO
    return 0


def destroy(container, args):
    """Destroy a container."""

    # Build the docker invocation
    command = list(_BASE_DOCKER_COMMAND)

    for docker_arg in args.docker_arg:
        command.extend(docker_arg)

    command.extend(["kill", container])

    print >> sys.stderr, "Destroying container with command %r" % (command)

    proc = subprocess.Popen(command)
    return proc.wait()


def recover(container, args):
    """Recover a container."""

    # TODO
    return 0


def wait(container, args):
    """Wait for the given container to come up."""

    timeout = 5.0
    interval = 0.1

    # Build the docker command
    command = list(_BASE_DOCKER_COMMAND)
    command.extend(["inspect", container])

    # Wait for `timeout` until the container comes up
    while timeout > 0.0:

        print >> sys.stderr, "Checking status of docker container %s" % (container)

        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return_code = proc.wait()

        # If the container is up, wait for it to finish
        if return_code == 0:

            print >> sys.stderr, "Waiting for docker container %s" % (container)

            command = list(_BASE_DOCKER_COMMAND)
            command.extend(["wait", container])

            # Wait for the container to finish
            proc = subprocess.Popen(command, stdout=subprocess.PIPE)
            proc.wait()

            container_exit_code = proc.stdout.read(1)

            print >> sys.stderr, "Container exited with exit code %s" % (container_exit_code)
            return int(container_exit_code)

        time.sleep(interval)
        timeout -= interval

    return 1


def main(args):

    commands = {
        "launch": launch,
        "update": update,
        "destroy": destroy,
        "usage": usage,
        "wait": wait
    }

    if args.command not in commands:
        print >> sys.stderr, "Invalid command %s" % (args.command)
        exit(2)

    return commands[args.command](args.container, args)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="docker-containerizer")
    parser.add_argument("--mesos-executor", required=False,
                        help="Path to the built-in mesos executor")
    parser.add_argument("--docker-arg", metavar=("option", "value"),
                        nargs=2, action="append", default=[],
                        help="Custom docker command to invoke")

    # Positional arguments
    parser.add_argument("command",
                        help="Containerizer command to run")
    parser.add_argument("container",
                        help="Container ID")

    exit(main(parser.parse_args()))
