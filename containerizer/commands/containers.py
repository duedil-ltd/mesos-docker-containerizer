"""
                 _        _
  ___ ___  _ __ | |_ __ _(_)_ __   ___ _ __ ___
 / __/ _ \| '_ \| __/ _` | | '_ \ / _ \ '__/ __|
| (_| (_) | | | | || (_| | | | | |  __/ |  \__ \
 \___\___/|_| |_|\__\__,_|_|_| |_|\___|_|  |___/

Containerizer subcommand to list all running containers.
"""

import logging

from containerizer import app, send_proto
from containerizer.docker import invoke_docker, PIPE
from containerizer.proto import Containers

logger = logging.getLogger(__name__)


@app.command()
def containers():
    """
    List all running containers. Dumps out the containerizer. Containers proto
    which lists all of the container IDs.
    """

    stdout, _, exit_code = invoke_docker("ps", stdout=PIPE, stderr=PIPE)
    if exit_code > 0:
        logger.error("Docker returned a bad status code (%d)" % exit_code)
        exit(1)

    running_containers = Containers()

    stdout.readline() # Read off the header
    for line in stdout:
        container_id = line.rstrip().split(" ")[-1]

        if len(container_id) > 0:
            container = running_containers.containers.add()
            container.value = container_id
        else:
            logger.error("Failed to parse container id, empty")
            exit(1)

    send_proto(running_containers)
