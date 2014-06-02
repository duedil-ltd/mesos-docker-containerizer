import os
import click
import lockfile
import logging
import sys
import struct

logger = logging.getLogger(__name__)


@click.group()
def app():
    """
    Mesos Docker Containerizer.

    TODO(tarnfeld): Document all the things.
    """

    pass


def send_proto(proto):
    """
    Send a protobuf object as a result. This method writes the object as a
    string of bytes to stdout.
    """

    data = proto.SerializeToString()
    sys.stdout.write(struct.pack('I', len(data)))
    sys.stdout.write(data)


def recv_proto(proto):
    """
    Receive a protobuf object from STDIN and deserliazize if to the given
    protobuf type.
    """

    data_size = struct.unpack('I', sys.stdin.read(4))[0]
    if data_size <= 0:
        logger.error("Failed to receive protobuf, zero bytes recevied")
        exit(1)

    data = sys.stdin.read(data_size)
    if len(data) != data_size:
        logger.error("Didn't receive %d bytes from stdin", data_size)
        exit(1)

    parsed = proto()
    parsed.ParseFromString(data)

    return parsed


def container_lock(container_id, label="global"):
    """
    Return a new `lockfile.FileLock` for the container lock. The label parameter
    is used to differentiate between multiple lock types for the same container.
    """

    lock_path = os.path.join("/tmp/docker-container-lock-%s-%s" % (label, container_id))
    return lockfile.FileLock(lock_path)
