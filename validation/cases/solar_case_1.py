"""Solar Validation Case 1 — standard utility-scale solar."""
from app.project_factories import create_default_solar_project

description = "Standard utility-scale solar PV, 50MW, base assumptions"
project_type = "Solar"

inputs = create_default_solar_project()

expected_outputs = {
    # Partial expectations — expand as model stabilizes
    "project_irr": 0.10,
    "total_revenue_keur": 1000.0,  # minimum expected
}