"""
Shell tools that offer convenience methods for interacting with external
executables
"""

# Standard
import shlex
import subprocess

# Local
from .log import log


def cmd(cmd: str, **kwargs):
    """Shortcut to run a subprocess command"""
    log.debug("CMD: %s", cmd)
    res = subprocess.run(shlex.split(cmd), **kwargs)
    if res.returncode != 0:
        raise RuntimeError(f"Command [{cmd}] failed with code {res.returncode}")
    return res


def verify_executable(exe_name: str, install_url: str):
    """Verify that the given executable is present. An EnvironmentError is
    raised if not found
    """
    try:
        cmd(f"which {exe_name}", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except RuntimeError:
        raise EnvironmentError(
            f"Missing required executable [{exe_name}]. Install instructions: {install_url}",
        )
