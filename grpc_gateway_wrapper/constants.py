"""
Shared constants for the library
"""

# Standard
import os

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "resources")
GO_TEMPLATE = os.path.join(RESOURCES_DIR, "gateway.go.template")
SWAGGER_SERVE_ASSETS = os.path.join(RESOURCES_DIR, "swagger_serve")
