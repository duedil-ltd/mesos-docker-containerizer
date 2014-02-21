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
import time
import sys
import os

from urlparse import urlparse

import google
import mesos_pb2


def _docker_command(args):
    """Return a docker command including any global options based on `args`."""

    command = ["docker"]
    return command


def _send_status(status):
    """Write a PluggableStatus protobuf object to stdout."""

    sys.stdout.write(status.SerializeToString())
    sys.stdout.flush()


def _lxc_metrics(lxc_container_id, metric):
    """A method to retrieve metrics about a given linux container. Returns a
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

            line = f.readline()


def _lxc_metric(lxc_container_id, metric, key=None):
    """A method to retrieve a specific metric and key about a given linux
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


def _download_hadoop_uri(uri, dest):

    raise NotImplementedError


def _download_s3_uri(uri, dest):

    raise NotImplementedError


def _download_http_uri(uri, dest):

    raise NotImplementedError


def _download_uri(sandbox, uri):
    """Download the given URI to the task sandbox directory."""

    downloaders = {
        "s3n": _download_hadoop_uri,
        "hdfs": _download_hadoop_uri,
        "s3": _download_s3_uri,
        "http": _download_http_uri,
        "https": _download_http_uri,
    }

    parsed_uri = urlparse(uri)

    if not len(parsed_uri.scheme):
        return uri  # Ignore local paths

    print >> sys.stderr, "Download URI %r" % (uri)

    basename = os.path.basename(parsed_uri.path)
    if parsed_uri.fragment:
        basename = parsed_uri.fragment
    local_path = os.path.join(sandbox, basename)

    # Create the direcotry if needed
    directory = os.path.dirname(local_path)
    if not os.path.isdir(directory):
        os.makedirs(directory)

    if parsed_uri.scheme not in downloaders:
        raise Exception("Unknown URI scheme %s" % (uri))

    downloaders[parsed_uri.scheme](parsed_uri, local_path)

    # TODO: Handle .(t|tar)(\.[gz|xz|bz2])
    # TODO: Handle .zip

    return local_path


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

    # Grab the task sandbox directory
    sandbox_dir = os.environ["MESOS_DIRECTORY"]

    # Download any URIs into the sandbox directory
    for uri in task.executor.command.uris:
        local_path = _download_uri(sandbox_dir, uri.value)

        # Make the file executable
        if uri.executable:
            os.chmod(local_path, 744)  # rwx-r--r--

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

    # Mount the sandbox into the container
    command.extend(["-v", "%s:/mesos-sandbox" % (sandbox_dir)])

    # Set the working directory of the container to the sandbox dir
    command.extend(["-w", sandbox_dir])

    # Set the MESOS_DIRECTORY environment variable to the sandbox mount point
    command.extend(["-e", "MESOS_DIRECTORY=/mesos-sandbox"])

    # Pass through the rest of the mesos environment variables
    mesos_env = ["MESOS_FRAMEWORK_ID", "MESOS_EXECUTOR_ID",
                 "MESOS_SLAVE_ID", "MESOS_CHECKPOINT",
                 "MESOS_RECOVERY_TIMEOUT"]
    for key in mesos_env:
        if key in os.environ:
            command.extend(["-e", "%s=%s" % (key, os.environ[key])])

    # Figure out what command to execute in the container
    if task.executor.command.value:
        container_command = task.executor.command.value
    else:
        container_command = task.command.value

    # Put together the rest of the invoke
    command.append(task.command.container.image.replace("docker:///", ""))
    command.extend(["/bin/sh", "-c", container_command])

    print >> sys.stderr, "Launching docker process with command %r" % (command)

    # Write the stdout/stderr of the docker container to the sandbox
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

    print >> sys.stderr, "Retrieving usage for container %s" % (container)

    # Find the lxc container ID
    info = _inspect_container(container, args)
    lxc_container_id = info["ID"]

    stats = mesos_pb2.ResourceStatistics()
    stats.timestamp = int(time.time())

    # Get the number of CPU ticks
    ticks = os.sysconf("SC_CLK_TCK")
    if not ticks > 0:
        raise Exception("Unable to retrieve number of clock ticks")

    # Retrieve the CPU stats
    stats.cpus_limit = float(_lxc_metric(lxc_container_id, "cpu.shares")) / 1024
    cpu_stats = dict(_lxc_metrics(lxc_container_id, "cpuacct.stat"))
    if "user" in cpu_stats and "system" in cpu_stats:
        stats.cpus_user_time_secs = float(cpu_stats["user"]) / ticks
        stats.cpus_system_time_secs = float(cpu_stats["system"]) / ticks

    cpu_stats = dict(_lxc_metrics(lxc_container_id, "cpu.stat"))
    if "nr_periods" in cpu_stats:
        stats.cpus_nr_periods = int(cpu_stats["nr_periods"])
    if "nr_throttled" in cpu_stats:
        stats.cpus_nr_throttled = int(cpu_stats["nr_throttled"])
    if "throttled_time" in cpu_stats:
        throttled_time_nano = int(cpu_stats["throttled_time"])
        throttled_time_secs = throttled_time_nano / 1000000000
        stats.cpus_throttled_time_secs = throttled_time_secs

    # Retrieve the mem stats
    stats.mem_limit_bytes = int(_lxc_metric(lxc_container_id, "memory.limit_in_bytes"))
    stats.mem_rss_bytes = int(_lxc_metric(lxc_container_id, "memory.usage_in_bytes"))

    mem_stats = dict(_lxc_metrics(lxc_container_id, "memory.stat"))
    if "total_cache" in mem_stats:
        stats.mem_file_bytes = int(mem_stats["total_cache"])
    if "total_rss" in mem_stats:
        stats.mem_anon_bytes = int(mem_stats["total_rss"])
    if "total_mapped_file" in mem_stats:
        stats.mem_mapped_file_bytes = int(mem_stats["total_mapped_file"])

    return stats


def destroy(container, args):
    """Destroy a container."""

    # Build the docker invocation
    command = list(_docker_command(args))
    command.extend(["kill", container])

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
