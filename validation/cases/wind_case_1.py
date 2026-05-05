"""Wind Validation Case 1 — standard onshore wind."""
from app.project_factories import create_default_wind_project

description = "Standard onshore wind, 72MW, base assumptions"
project_type = "Wind"

inputs = create_default_wind_project()

expected_outputs = {
    "project_irr": 0.09,
}