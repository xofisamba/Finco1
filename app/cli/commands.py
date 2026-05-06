"""CLI commands."""
import click
from app.ui_runner import run_demo_project
from app.excel_export import build_excel_export
import json
import sys


@click.group()
def cli():
    """FincoGPT CLI — run project models from the command line."""
    pass


SUPPORTED_PROJECTS = {"Solar", "Wind"}
SUPPORTED_SCENARIOS = {"Base", "Downside", "Upside"}
SUPPORTED_PERIOD_VIEWS = {"Semiannual", "Annual"}


@cli.command()
@click.option('--project', required=True, type=str, help='Solar or Wind')
@click.option('--scenario', required=True, type=str, help='Base, Downside, or Upside')
@click.option('--period-view', default='Semiannual', type=str, help='Semiannual or Annual')
@click.option('--output', default=None, type=str, help='Output Excel file path')
@click.option('--json', 'json_output', default=None, type=str, help='Output JSON file path')
def run(project, scenario, period_view, output, json_output):
    """Run a project model and optionally export results."""
    # Validate
    if project not in SUPPORTED_PROJECTS:
        click.echo(f'Error: --project must be one of {SUPPORTED_PROJECTS}', err=True)
        sys.exit(1)
    if scenario not in SUPPORTED_SCENARIOS:
        click.echo(f'Error: --scenario must be one of {SUPPORTED_SCENARIOS}', err=True)
        sys.exit(1)
    if period_view not in SUPPORTED_PERIOD_VIEWS:
        click.echo(f'Error: --period-view must be one of {SUPPORTED_PERIOD_VIEWS}', err=True)
        sys.exit(1)

    click.echo(f'Running {project} {scenario} ({period_view})...')

    try:
        demo = run_demo_project(project, scenario)
        result = demo.result
        project_inputs = getattr(demo, 'project_inputs', None)

        if json_output:
            kpis = {
                'project_irr': result.project_irr,
                'equity_irr': result.equity_irr,
                'actual_min_dscr': result.actual_min_dscr,
                'actual_avg_dscr': result.actual_avg_dscr,
                'total_revenue_keur': result.total_revenue_keur,
                'total_ebitda_keur': result.total_ebitda_keur,
            }
            with open(json_output, 'w') as f:
                json.dump(kpis, f, indent=2)
            click.echo(f'JSON output: {json_output}')

        if output:
            excel_bytes = build_excel_export(
                result=result,
                scenario=scenario,
                project_type=project,
                period_view=period_view,
                advanced_opex_line_items=None,
                advanced_capex_line_items=None,
                warnings=[{"code": "INFO", "message": msg} for msg in demo.messages] if getattr(demo, 'messages', None) else None,
                validation_issues=getattr(demo, 'validation_issues', None),
                project_inputs=project_inputs,
                integration_status=getattr(demo, 'integration_status', 'full'),
                integration_note=getattr(demo, 'integration_note', None),
            )
            with open(output, 'wb') as f:
                f.write(excel_bytes)
            click.echo(f'Excel output: {output}')

        click.echo(f'Success: IRR={result.project_irr*100:.2f}%, minDSCR={result.actual_min_dscr:.3f}x')

    except Exception as e:
        click.echo(f'Error: {e}', err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()