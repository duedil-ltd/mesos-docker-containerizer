"""
     _           _
  __| | ___  ___| |_ _ __ ___  _   _
 / _` |/ _ \/ __| __| '__/ _ \| | | |
| (_| |  __/\__ \ |_| | | (_) | |_| |
 \__,_|\___||___/\__|_|  \___/ \__, |
                               |___/

Containerizer subcommand to destroy a container.
"""

import logging

from containerizer import app, recv_proto, container_lock
from containerizer.docker import invoke_docker, PIPE
from containerizer.proto import Destroy

logger = logging.getLogger(__name__)


@app.command()
def destroy():
    """
    Kill and remove a container.
    """

    destroy = recv_proto(Destroy)

    # Acquire a lock for this container
    with container_lock(destroy.container_id.value):
        success = destroy_container(destroy.container_id)

    if not success:
        exit(1)


def destroy_container(container_id):

    logger.info("Ensuring container %s is killed", container_id.value)

    stdout, _, return_code = invoke_docker("kill", [container_id.value], stdout=PIPE)
    if return_code > 0:
        logger.error("Failed to kill container, bad exit code (%d)", return_code)
        return False

    logger.info("Removing container %s", container_id.value)

    stdout, _, return_code = invoke_docker("rm", [container_id.value], stdout=PIPE)
    if return_code > 0:
        logger.error("Failed to remove container, bad exit code (%d)", return_code)
        return False

    return True
