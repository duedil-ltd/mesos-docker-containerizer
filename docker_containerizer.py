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
import json
import sys
import os

import google
import mesos_pb2


def _docker_command(args):
    """Return a docker command including any global options based on `args`."""

    command = ["docker"]
    if args.docker_host:
        command.extend(["-H", args.docker_host])

    return command


def _send_status(status):
    """Write a PluggableStatus protobuf object to stdout."""

    sys.stdout.write(status.SerializeToString())
    sys.stdout.flush()


def _lxc_metrics(lxc_container_id, metric):
    """A method to retreive metrics about a given linux container. Returns a
    generator of key,value pairs for the given container metric."""

    metric_keys = metric.split(".")
    if len(metric_keys) < 2:
        raise Exception("Invalid metric %r" % (metric))

    path = os.path.join(
        "/sys/fs/cgroup", metric_keys[0], "lxc", lxc_container_id, metric
    )

    if not os.path.exists(path):
        raise Exception("LXC metric file does not exist %r" % (path))

    # Parse the individual keys out of the file
    with open(path, "r") as f:
        line = f.readline()
        while line:
            parts = line.strip().split(" ")

            if len(parts) == 1:
                yield None, parts[0]
            elif len(parts) == 2:
                key, value = parts
                yield key, value
            else:
                raise Exception("Unknown metric syntax %r %r" % (line, parts))


def _lxc_metric(lxc_container_id, metric, key=None):
    """A method to retreive a specific metric and key about a given linux
    container."""

    for metric_key, metric_value in _lxc_metrics(lxc_container_id, metric):
        if metric_key == key:
            return metric_value

    return None


def _inspect_container(container, args):

    command = list(_docker_command(args))
    command.extend(["inspect", container])

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return_code = proc.wait()

    if return_code == 0:
        containers = json.load(proc.stdout)
        return containers[0]

    for line in proc.stderr:
        print >> sys.stderr, "Inspect STDERR: %s" % (line)

    raise Exception("Failed to inspect container %r" % (container))


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

    command.extend(_docker_command(args))
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
    for resource in task.resources:
        if resource.name == "cpus":
            command.extend(["-c", str(int(resource.scalar.value * 256))])
        if resource.name == "mem":
            command.extend(["-m", "%dm" % (int(resource.scalar.value))])
        # TODO: Handle port configurations

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

            status = mesos_pb2.PluggableStatus()
            status.message = "launch/docker: ok"

            _send_status(status)
            os.close(1)  # Close stdout

            return_code = proc.wait()

    print >> sys.stderr, "Docker container %s exited with return code %d" % (container, return_code)
    return return_code


def usage(container, args):
    """Retrieve the resource usage of a given container."""

    # Find the lxc container ID
    info = _inspect_container(container, args)
    lxc_container_id = info["ID"]

    # Retreive the CPU
    cpu = int(_lxc_metric(lxc_container_id, "cpuacct.usage"))
    print >> sys.stderr, "CPU Usage of container %s : %d" % (container, cpu)

    # Retreive the mem usage
    mem_bytes = int(_lxc_metric(lxc_container_id, "memory.usage_in_bytes"))
    print >> sys.stderr, "Memory usage of container %s : %d" % (container, mem_bytes)

    return 0


def destroy(container, args):
    """Destroy a container."""

    # Build the docker invocation
    command = list(_docker_command(args))
    command.extend(["stop", "-t", args.docker_stop_timeout, container])

    print >> sys.stderr, "Destroying container with command %r" % (command)

    proc = subprocess.Popen(command)
    return_code = proc.wait()

    if return_code == 0:
        status = mesos_pb2.PluggableStatus()
        status.message = "destroy/docker: ok"
        return status

    return return_code


def main(args):

    # Simple default function for ignoring a command
    ignore = lambda c, a: 0

    commands = {
        "launch": launch,
        "destroy": destroy,
        "usage": usage,

        "wait": ignore,
        "update": ignore,
        "recover": ignore,
    }

    if args.command not in commands:
        print >> sys.stderr, "Invalid command %s" % (args.command)
        exit(2)

    return commands[args.command](args.container, args)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="docker-containerizer")
    parser.add_argument("--mesos-executor", required=False,
                        help="Path to the built-in mesos executor")
    parser.add_argument("-H", "--docker-host", required=False,
                        help="Docker host for client to connect to")
    parser.add_argument("-T", "--docker-stop-timeout", default=2,
                        help="Number of seconds to wait when stopping a container")

    # Positional arguments
    parser.add_argument("command",
                        help="Containerizer command to run")
    parser.add_argument("container",
                        help="Container ID")

    output = main(parser.parse_args())

    # Pass protobuf responses through
    if not isinstance(output, int):
        _send_status(output)
        output = 0

    exit(output)
