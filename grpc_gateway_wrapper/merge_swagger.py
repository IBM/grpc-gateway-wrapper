"""
Utility to merge all swagger files into a single unified file
"""

# Standard
from typing import Iterable
import json

# Local
from .log import log


# CITE: https://stackoverflow.com/questions/20656135/python-deep-merge-dictionary-data
def merge(source: dict, destination: dict):
    """
    In-place deep dict merge

    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge(value, node)
        else:
            destination[key] = value


def merge_swagger(input_fnames: Iterable[str], output_fname: str):
    """Merge the given input swagger files into a single unified file"""
    merged = {}
    for fname in input_fnames:
        try:
            log.debug("Loading [%s]", fname)
            with open(fname, "r") as handle:
                js = json.load(handle)
            log.debug("Merging [%s]", fname)
            merge(js, merged)
        except Exception as err:
            log.error("Bad spec file [%s]: %s", fname, err)
            raise

    with open(output_fname, "w") as handle:
        handle.write(json.dumps(merged, indent=2))
