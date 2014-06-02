
import os
import json
import logging
import subprocess
from subprocess import PIPE

logger = logging.getLogger(__name__)


def fetch_uris(sandbox_directory, uris):
    """
    Invoke the mesos-fetcher tool and download the given URIs.
    """

    # Build up the URIs
    fetcher_uris = []
    for uri in uris:
        uri_string = uri.value
        uri_string += "+"

        # Add the executable bit
        if uri.HasField("executable") and uri.executable:
            uri_string += "1"
        else:
            uri_string += "0"

        # Add the extraction bit
        if uri.extract:
            uri_string += "X"
        else:
            uri_string += "N"

        fetcher_uris.append(uri_string)

    # Pass through the LD_LIBRARY_PATH
    library_path = os.environ.get("LD_LIBRARY_PATH", "")
    logger.info("LD_LIBRARY_PATH: %s", library_path)

    fetcher_path = os.path.join(os.environ["MESOS_LIBEXEC_DIRECTORY"], "mesos-fetcher")
    proc = subprocess.Popen([fetcher_path], env={
        "MESOS_EXECUTOR_URIS": " ".join(fetcher_uris),
        "MESOS_WORK_DIRECTORY": sandbox_directory,
        "LD_LIBRARY_PATH": library_path
    })

    return proc.wait()
