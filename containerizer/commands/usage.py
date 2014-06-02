"""

 _   _ ___  __ _  __ _  ___
| | | / __|/ _` |/ _` |/ _ \
| |_| \__ \ (_| | (_| |  __/
 \__,_|___/\__,_|\__, |\___|
                 |___/

Containerizer subcommand to retreive resource usage information from a
running container.
"""

import os
import logging
import time

from containerizer import app, recv_proto, send_proto
from containerizer.docker import inspect_container
from containerizer.cgroups import read_metric, read_metrics
from containerizer.proto import Usage, ResourceStatistics

logger = logging.getLogger(__name__)


@app.command()
def usage():
    """
    Retrieve usage information about a running container.
    """

    usage = recv_proto(Usage)
    logger.info("Retrieving usage for container %s", usage.container_id.value)

    # Find the lxc container ID
    info = inspect_container(usage.container_id.value)
    lxc_container_id = info["ID"]

    logger.info("Using LXC container ID %s", lxc_container_id)

    stats = ResourceStatistics()
    stats.timestamp = int(time.time())

    # Get the number of CPU ticks
    ticks = os.sysconf("SC_CLK_TCK")
    if not ticks > 0:
        logger.error("Unable to retrieve number of CPU clock ticks")
        exit(1)

    # Retrieve the CPU stats
    try:
        stats.cpus_limit = float(read_metric(lxc_container_id, "cpu.shares")) / 256
        cpu_stats = dict(read_metrics(lxc_container_id, "cpuacct.stat"))
        if "user" in cpu_stats and "system" in cpu_stats:
            stats.cpus_user_time_secs = float(cpu_stats["user"]) / ticks
            stats.cpus_system_time_secs = float(cpu_stats["system"]) / ticks
    except:
        logger.error("Failed to get CPU usage")

    try:
        cpu_stats = dict(read_metrics(lxc_container_id, "cpu.stat"))
        if "nr_periods" in cpu_stats:
            stats.cpus_nr_periods = int(cpu_stats["nr_periods"])
        if "nr_throttled" in cpu_stats:
            stats.cpus_nr_throttled = int(cpu_stats["nr_throttled"])
        if "throttled_time" in cpu_stats:
            throttled_time_nano = int(cpu_stats["throttled_time"])
            throttled_time_secs = throttled_time_nano / 1000000000
            stats.cpus_throttled_time_secs = throttled_time_secs
    except:
        logger.error("Failed to get detailed CPU usage")

    # Retrieve the mem stats
    try:
        stats.mem_limit_bytes = int(read_metric(lxc_container_id, "memory.limit_in_bytes"))
        stats.mem_rss_bytes = int(read_metric(lxc_container_id, "memory.usage_in_bytes"))
    except:
        logger.error("Failed to get memory usage")

    try:
        mem_stats = dict(read_metrics(lxc_container_id, "memory.stat"))
        if "total_cache" in mem_stats:
            stats.mem_file_bytes = int(mem_stats["total_cache"])
        if "total_rss" in mem_stats:
            stats.mem_anon_bytes = int(mem_stats["total_rss"])
        if "total_mapped_file" in mem_stats:
            stats.mem_mapped_file_bytes = int(mem_stats["total_mapped_file"])
    except:
        logger.error("Failed to get detailed memory usage")

    logger.debug("Container usage: %s", stats)

    # Send the stats back to mesos
    send_proto(stats)
