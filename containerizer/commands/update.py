"""
                 _       _
 _   _ _ __   __| | __ _| |_ ___
| | | | '_ \ / _` |/ _` | __/ _ \
| |_| | |_) | (_| | (_| | ||  __/
 \__,_| .__/ \__,_|\__,_|\__\___|
      |_|

Containerizer subcommand to update a running container with new resources.
"""

import logging

from containerizer import app, recv_proto, container_lock
from containerizer.docker import inspect_container
from containerizer.proto import Update
from containerizer.cgroups import read_metric, write_metric

logger = logging.getLogger(__name__)


@app.command()
def update():
    """
    Update the resources of a running container.
    """

    update = recv_proto(Update)

    logger.info("Updating resources for container %s", update.container_id.value)
    with container_lock(update.container_id.value, "update"):
        update_container(update.container_id.value, update.resources)


def update_container(container_id, resources):

    # Get the container ID
    info = inspect_container(container_id)
    lxc_container_id = info.get("ID", info.get("Id"))

    if lxc_container_id is None:
        raise Exception("Failed to get full container ID")

    # Gather the resoures
    max_mem = None
    max_cpus = None

    for resource in update.resources:
        if resource.name == "mem":
            max_mem = int(resource.scalar.value) * 1024 * 1024
        if resource.name == "cpus":
            max_cpus = int(resource.scalar.value) * 256
        if resource.name == "ports":
            logger.error("Unable to process an update to port configuration!")

    if max_mem:
        # Update the soft limit
        write_metric(lxc_container_id, "memory.soft_limit_in_bytes", max_mem)

        # Figure out if we can update the hard limit
        # If we reduce the hard limit and too much memory is in use, this
        # can invoke an OOM.
        current_mem = int(read_metric(lxc_container_id, "memory.limit_in_bytes"))
        if current_mem > max_mem:
            write_metric(lxc_container_id, "memory.limit_in_bytes", max_mem)
        else:
            logger.info("Skipping hard memory limit, would invoke OOM")

    if max_cpus:
        shares = max_cpus * 256
        write_metric(lxc_container_id, "cpu.shares", shares)

    logger.info("Finished processing container update")
