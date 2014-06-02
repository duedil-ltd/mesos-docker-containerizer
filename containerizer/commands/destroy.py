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

        logger.info("Ensuring container %s is killed", destroy.container_id.value)

        stdout, _, return_code = invoke_docker("kill", [destroy.container_id.value], stdout=PIPE)
        if return_code > 0:
            logger.error("Failed to kill container, bad exit code (%d)", return_code)
            exit(1)

        logger.info("Removing container %s", destroy.container_id.value)

        stdout, _, return_code = invoke_docker("rm", [destroy.container_id.value], stdout=PIPE)
        if return_code > 0:
            logger.error("Failed to remove container, bad exit code (%d)", return_code)
            exit(1)
