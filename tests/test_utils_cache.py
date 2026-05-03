"""Tests for utils/cache.py deprecation and compute_waterfall_cached delegation."""
import pytest
import warnings
import inspect
import utils.cache
from utils.cache import compute_waterfall_cached, deprecated


def test_deprecated_decorator_warns():
    """@deprecated decorator emits DeprecationWarning."""
    @deprecated("test message")
    def dummy():
        return 42

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = dummy()
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "test message" in str(w[0].message)
        assert result == 42


def test_compute_waterfall_cached_marked_deprecated():
    """compute_waterfall_cached has @deprecated decorator."""
    src = inspect.getsource(compute_waterfall_cached)
    # The source of the wrapper function contains the deprecated marker
    assert "deprecated" in src.lower()


def test_utils_cache_no_annual_divide_by_two_waterfall_logic():
    """Reject opex_annual.get.../2 and dep_per_year/2 in compute_waterfall_cached."""
    import inspect
    from utils.cache import compute_waterfall_cached
    source = inspect.getsource(compute_waterfall_cached)
    # After delegation, should NOT contain manual OPEX annual/2 or dep_per_year/2 patterns
    assert not ("opex_annual.get" in source and "/ 2" in source), \
        "compute_waterfall_cached still uses opex_annual/2"
    assert not ("dep_per_year / 2" in source), \
        "compute_waterfall_cached still uses dep_per_year/2"


def test_compute_waterfall_cached_delegates_to_run_waterfall_v3_core():
    """compute_waterfall_cached calls run_waterfall_v3_core (verified in source)."""
    import os
    cache_path = inspect.getfile(utils.cache)
    with open(cache_path) as f:
        src = f.read()
    # Find the function body of compute_waterfall_cached
    func_start = src.index('def compute_waterfall_cached(')
    func_chunk = src[func_start:func_start + 2000]
    assert 'run_waterfall_v3_core' in func_chunk, \
        "compute_waterfall_cached body should call run_waterfall_v3_core"


def test_deprecated_decorator_preserves_function_name():
    """@deprecated preserves __name__."""
    @deprecated("msg")
    def my_func():
        pass

    assert my_func.__name__ == "my_func"