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
import sys

import google
import mesos_pb2


# Base docker command
_DOCKER_BASE_COMMAND = ["docker", "-H", "192.168.4.2:7070"]


def launch(container, args):
    """Launch a new docker container."""

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

    if not args.mesos_executor:
        print >> sys.stderr, "Mesos executor is required"
        return 1

    # Build the docker invocation
    command = [args.mesos_executor]
    command.extend(_DOCKER_BASE_COMMAND)
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

    # Put together the rest of the invoke
    command.append(task.command.container.image)
    command.extend(["/bin/sh", "-c", task.command.value])

    print >> sys.stderr, "Launching docker process with command %r" % (command)

    proc = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr)
    return proc.wait()


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
    command = list(_DOCKER_BASE_COMMAND)
    command.extend(["kill", container])

    print >> sys.stderr, "Destroying container with command %r" % (command)

    proc = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr)
    return proc.wait()


def recover(container, args):
    """Recover a container."""

    # TODO
    return 0


def wait(container, args):
    """Wait for a container to terminate."""

    # We use the default implementation as the `launch` command will attach to the
    # docker container.
    # TODO: Check how this interacts with `recover`
    return 0


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

    print >> sys.stderr, "Command %r for container %r" % (args.command, args.container)

    return commands[args.command](args.container, args)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="docker-containerizer")
    parser.add_argument("--mesos-executor", required=False,
                        help="Path to the mesos executor")
    parser.add_argument("command",
                        help="Containerizer command to run")
    parser.add_argument("container",
                        help="Container ID")

    exit(main(parser.parse_args()))
