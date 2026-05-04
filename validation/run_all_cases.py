"""Run all validation cases and print reports."""
import sys
sys.path.insert(0, ".")

from app.validation_framework import run_validation_case, generate_validation_report

from validation.cases.solar_case_1 import inputs as solar1_inputs, expected_outputs as solar1_exp
from validation.cases.wind_case_1 import inputs as wind1_inputs, expected_outputs as wind1_exp
from validation.cases.solar_case_2 import inputs as solar2_inputs, expected_outputs as solar2_exp

CASES = [
    ("solar_case_1", solar1_inputs, solar1_exp),
    ("wind_case_1", wind1_inputs, wind1_exp),
    ("solar_case_2", solar2_inputs, solar2_exp),
]

if __name__ == "__main__":
    for name, inputs, expected in CASES:
        print(f"\n{'='*50}")
        print(f"Running: {name}")
        print('='*50)
        actual = run_validation_case(inputs, expected)
        report = generate_validation_report(name, actual, expected)
        print(report["printable"])