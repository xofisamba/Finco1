"""CLI tests."""
import pytest
from click.testing import CliRunner
from app.cli.commands import cli, run


def test_cli_solar_base_success():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['run', '--project', 'Solar', '--scenario', 'Base'])
        assert result.exit_code == 0
        assert 'IRR=' in result.output


def test_cli_solar_downside_success():
    runner = CliRunner()
    result = runner.invoke(cli, ['run', '--project', 'Solar', '--scenario', 'Downside'])
    assert result.exit_code == 0


def test_cli_invalid_project():
    runner = CliRunner()
    result = runner.invoke(cli, ['run', '--project', 'Invalid', '--scenario', 'Base'])
    assert result.exit_code != 0
    assert 'Error' in result.output


def test_cli_json_output():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, [
            'run', '--project', 'Solar', '--scenario', 'Base', '--json', 'out.json'
        ])
        assert result.exit_code == 0
        import os
        assert os.path.exists('out.json')


def test_cli_excel_output():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, [
            'run', '--project', 'Wind', '--scenario', 'Base', '--output', 'out.xlsx'
        ])
        assert result.exit_code == 0
        import os
        assert os.path.exists('out.xlsx')



def test_cli_input_mismatched_project_type(tmp_path):
    """CLI exits with error when --input project_type != --project."""
    import json
    data = {"project_type": "Wind", "scenario": "Base"}
    f = tmp_path / "wind.json"
    f.write_text(json.dumps(data))


    runner = CliRunner()
    result = runner.invoke(cli, [
        'run', '--project', 'Solar', '--scenario', 'Base', '--input', str(f)
    ])
    assert result.exit_code != 0
    assert 'mismatch' in result.output.lower() or 'Wind' in result.output



def test_cli_input_mismatched_scenario(tmp_path):
    """CLI exits with error when --input scenario != --scenario."""
    import json
    data = {"project_type": "Solar", "scenario": "Upside"}
    f = tmp_path / "solar.json"
    f.write_text(json.dumps(data))

    runner = CliRunner()
    result = runner.invoke(cli, [
        'run', '--project', 'Solar', '--scenario', 'Base', '--input', str(f)
    ])
    assert result.exit_code != 0
    assert 'mismatch' in result.output.lower() or 'Upside' in result.output


def test_cli_input_matching_ok(tmp_path):
    """CLI accepts input file when project_type and scenario match."""
    import json
    data = {"project_type": "Solar", "scenario": "Base", "capacity_mw": 50}
    f = tmp_path / "solar.json"
    f.write_text(json.dumps(data))

    runner = CliRunner()
    result = runner.invoke(cli, [
        'run', '--project', 'Solar', '--scenario', 'Base', '--input', str(f)
    ])
    assert result.exit_code == 0