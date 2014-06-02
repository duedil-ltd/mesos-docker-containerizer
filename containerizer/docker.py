
import os
import json
import subprocess
import logging

from subprocess import PIPE

logger = logging.getLogger(__name__)


def invoke_docker(command, arguments=[], stdout=None, stderr=None):
    """
    Invoke the docker command line tool. This function returns a tuple that
    contains (stdout, stderr, return_code)
    """

    # Build up the docker command
    invoke = ["docker"]

    # Include any global docker arguments
    docker_args = os.environ.get("CONTAINERIZER_DOCKER_ARGS")
    if docker_args:
        invoke.extend(docker_args.split(" "))

    # Add the command and arguments
    invoke.append(command)
    invoke.extend(arguments)
    
    logger.info("Invoking docker with %r", invoke)

    proc = subprocess.Popen(invoke, stdout=stdout, stderr=stderr)
    return proc.stdout, proc.stderr, proc.wait()


def inspect_container(container):
    """
    Inspect a container a return a dictionary of its properties.
    """

    stdout, _, exit_code = invoke_docker("inspect", [container], stdout=PIPE)
    if exit_code > 0:
        raise Exception("Docker returned a bad exit code (%d)" % exit_code)

    containers = json.load(stdout)
    return containers[0]
