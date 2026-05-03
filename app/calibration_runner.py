"""Legacy calibration runner intentionally disabled in production app namespace.

Use tools.calibration_legacy only for historical diagnostics.
"""
raise ImportError(
    "app.calibration_runner is disabled in industry-engine-refactor. "
    "Use tools.calibration_legacy.calibration_runner only for legacy diagnostics."
)