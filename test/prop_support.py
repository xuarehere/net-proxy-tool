"""Hypothesis setup shared by the property-based tests (test_prop_*.py).

Importing this module raises unittest.SkipTest when Hypothesis is missing, so the
property tests are reported as skipped on minimal installs and old Pythons.
Profiles: "ci" runs 100 examples per property (selected when CI is set), "dev"
runs 50. HYPOTHESIS_PROFILE overrides the choice.
"""
import os
import unittest

try:
    from hypothesis import HealthCheck, assume, example, given, settings, strategies as st  # noqa: F401
except ImportError:
    raise unittest.SkipTest("Hypothesis is not installed; run python -m pip install -r requirements-dev.txt")

_COMMON = dict(deadline=None, suppress_health_check=[HealthCheck.too_slow], derandomize=False)
settings.register_profile("ci", max_examples=100, **_COMMON)
settings.register_profile("dev", max_examples=50, **_COMMON)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE") or ("ci" if os.environ.get("CI") else "dev"))
