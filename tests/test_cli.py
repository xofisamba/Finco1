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