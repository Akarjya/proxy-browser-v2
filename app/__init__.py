"""
Proxy Browser V2 - Main Application Package
A modern proxy-based web browsing solution with mobile support
"""

__version__ = "2.0.0"
__author__ = "Proxy Browser Team"

from .core.app import create_app

__all__ = ["create_app"]
