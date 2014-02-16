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
import os

import google
import mesos_pb2


def launch(container, args):
    """Launch a new docker container."""

    try:
        data = sys.stdin.read()
        if len(data) <= 0:
            print >> sys.stderr, "Expected protobuf over stdin. Received 0 bytes."
            return 1

        if not args.mesos_executor:
            print >> sys.srderr, "No executor specified"
            return 1

        task = mesos_pb2.TaskInfo()
        task.ParseFromString(data)

        # This needs serious work
        command = ["docker", "-H", "192.168.4.2:7070", "run", task.command.container.image, "/bin/bash", "-c", task.command.value]

        proc = subprocess.Popen(command, env=os.environ.copy())
        proc.wait()
    except google.protobuf.message.DecodeError:
        print >> sys.stderr, "Could not deserialise external container protobuf"
        return 1

    return 0


def update(container, args):
    """Update an existing container."""

    return 0


def usage(container, args):
    """Retrieve the resource usage of a given container."""

    return 0


def destroy(container, args):
    """Destroy a container."""

    return 0


def recover(container, args):
    """Recover a container."""

    return 0


def wait(container, args):
    """Wait for a container to terminate."""

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

    return commands[args.command](args.container, args)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="docker-launcher")
    parser.add_argument("--mesos-executor", required=False,
                        help="Path to the mesos executor")
    parser.add_argument("command",
                        help="Containerizer command to run")
    parser.add_argument("container",
                        help="Container ID")

    exit(main(parser.parse_args()))
