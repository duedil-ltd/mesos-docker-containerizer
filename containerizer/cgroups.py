
import os


def read_metrics(lxc_container_id, metric):
    """
    A method to retrieve metrics about a given linux container. Returns a
    generator of key,value pairs for the given container metric.
    """

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


def read_metric(lxc_container_id, metric, key=None):
    """
    A method to retrieve a specific metric and key about a given linux
    container.
    """

    for metric_key, metric_value in _lxc_metrics(lxc_container_id, metric):
        if metric_key == key:
            return metric_value

    return None


def write_metric(lxc_container_id, metric, value):
    """
    Write a value to a group metric, for example changing the memory
    limit. `memory.soft_limit_in_bytes`
    """

    metric_keys = metric.split(".")
    if len(metric_keys) < 2:
        raise Exception("Invalid metric %r" % (metric))

    path = os.path.join(
        "/sys/fs/cgroup", metric_keys[0], "lxc", lxc_container_id, metric
    )

    previous_value = read_metric(metric)
    new_value = str(value)

    logger.info("Updating cgroup metric %s from %r to %r", path, previous_value, new_value)

    with open(path, "w") as f:
        f.write(new_value)

    updated_value = read_metric(metric)
    if updated_value != new_value:
        raise Exception("Failed to write updated cgroup value to %s" % path)
