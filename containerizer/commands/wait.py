"""
               _ _
__      ____ _(_) |_
\ \ /\ / / _` | | __|
 \ V  V / (_| | | |_
  \_/\_/ \__,_|_|\__|

Containerizer subcommand to wait for a running container to exit.
"""

import logging

from containerizer import app, send_proto, recv_proto, container_lock
from containerizer.docker import invoke_docker, PIPE
from containerizer.proto import Wait, Termination

logger = logging.getLogger(__name__)


@app.command()
def wait():
    """
    Wait for a running container to exit.
    """

    wait = recv_proto(Wait)

    # Acquire a lock for this container
    with container_lock(wait.container_id.value, "wait"):

        logger.info("Waiting for container %s", wait.container_id.value)

        stdout, _, return_code = invoke_docker("wait", [wait.container_id.value], stdout=PIPE)
        if return_code > 0:
            logger.error("Failed to wait for container, bad exit code (%d)", return_code)
            exit(1)

        container_exit = int(stdout.readline().rstrip())
        logger.info("Container exit code: %d", container_exit)

        termination = Termination()
        termination.killed = False
        termination.status = container_exit
        termination.message = ""

        send_proto(termination)
