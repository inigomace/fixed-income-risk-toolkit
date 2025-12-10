# src/firisk/curve/__init__.py

"""
Yield curve models and calibration utilities.

This subpackage focuses on the Nelson–Siegel–Svensson (NSS) model:
- Core NSS functions
- Calibration routines
- NSSCurve object for yields and discount factors
"""

from .nss import nss_yield
from .calibration import calibrate_nss, calibrate_nss_latest
from .curve_object import NSSCurve

__all__ = [
    "nss_yield",
    "calibrate_nss",
    "calibrate_nss_latest",
    "NSSCurve",
]
