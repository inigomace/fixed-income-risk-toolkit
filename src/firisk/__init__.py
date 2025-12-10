# src/firisk/__init__.py

"""
Fixed Income Risk Toolkit.

A compact rates/risk library that provides:
- Nelson–Siegel–Svensson (NSS) curve modeling and calibration
- Fixed-coupon bond cashflows and pricing
- Key-rate DV01, curve stress tests, and VaR
- A small portfolio container

Design note:
This __init__ keeps imports intentionally light to avoid circular-import
issues in interactive environments (e.g., Spyder).
Import submodules explicitly when you need them, e.g.:

    from firisk.data import load_yield_history
    from firisk.curve import NSSCurve, calibrate_nss_latest
    from firisk.instruments.bond import FixedCouponBond
    from firisk.risk.keyrate import compute_keyrate_dv01_with_settlement
"""

from importlib import metadata

# Version (safe even if package metadata isn't available during dev edits)
try:
    __version__ = metadata.version("fixed-income-risk-toolkit")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

# Re-export a few stable, low-risk entry points
from .curve import NSSCurve, calibrate_nss, calibrate_nss_latest, nss_yield
from .data import load_yield_history, validate_yield_table
from .utils import normalize_tenor, sort_tenors, tenor_to_years, year_fraction_act365

__all__ = [
    "__version__",
    # data
    "load_yield_history",
    "validate_yield_table",
    # curve
    "nss_yield",
    "calibrate_nss",
    "calibrate_nss_latest",
    "NSSCurve",
    # utils
    "normalize_tenor",
    "sort_tenors",
    "tenor_to_years",
    "year_fraction_act365",
]
