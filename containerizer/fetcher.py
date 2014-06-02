
import os
import json
import subprocess
from subprocess import PIPE


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

    fetcher_path = os.path.join(os.environ["MESOS_LIBEXEC_DIRECTORY"], "mesos-fetcher")
    proc = subprocess.Popen([fetcher_path], env={
        "MESOS_EXECUTOR_URIS": " ".join(fetcher_uris),
        "MESOS_WORK_DIRECTORY": sandbox_directory,
        "LD_LIBRARY_PATH": os.envrion.get("LD_LIBRARY_PATH", "")
    })

    return proc.wait()
