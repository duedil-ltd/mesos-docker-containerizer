"""

 _ __ ___  ___ _____   _____ _ __
| '__/ _ \/ __/ _ \ \ / / _ \ '__|
| | |  __/ (_| (_) \ V /  __/ |
|_|  \___|\___\___/ \_/ \___|_|

Containerizer subcommand to perform any internal recovery operations.
"""

import sys
import logging

from containerizer import app

logger = logging.getLogger(__name__)


@app.command()
def recover():
    """
    Recover any internal containerizer state. Note: this does nothing.
    """

    pass
