"""
Common test config
"""
# Standard
import os

# Third Party
import alog

alog.configure(default_level=os.environ.get("LOG_LEVEL", "off"))
