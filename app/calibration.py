"""Legacy calibration module intentionally disabled in production app namespace.

Use tools.calibration_legacy only for historical diagnostics.
"""
raise ImportError(
    "app.calibration is disabled in industry-engine-refactor. "
    "Use tools.calibration_legacy.calibration only for legacy diagnostics."
)