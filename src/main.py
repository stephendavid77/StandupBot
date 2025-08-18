import click
import yaml
from pathlib import Path

from jira_client import JiraClient
from analyzer import SprintAnalyzer
from reporter import Reporter

def load_config():
    """
    Loads the configuration from config.yaml.
    """
    config_path = Path(__file__).parent.parent / 'config/config.yaml'
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config.yaml not found. Please copy config.yaml.sample and fill it out.")
        exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}")
        exit(1)

@click.group()
def cli():
    """
    A CLI tool to get daily sprint health insights from Jira.
    """
    pass

@cli.command(name='run', help='Run the sprint analysis and generate a report.')
@click.option('--report-type', '-r', type=click.Choice(['daily', 'full']), default=None, help='Override the report type from config.')
@click.option('--export/--no-export', '-e', default=None, help="Enable or disable report exporting, overriding config.")
@click.option('--skip-pdf/--no-skip-pdf', default=None, help="Skip or include PDF generation, overriding config.")
def run(report_type, export, skip_pdf):
    config = load_config()
    run_settings = config.get('run_settings', {})

    # Determine final settings, with CLI flags taking precedence over config file
    final_report_type = report_type if report_type is not None else run_settings.get('report_type', 'daily')
    final_export = export if export is not None else run_settings.get('export', False)
    final_skip_pdf = skip_pdf if skip_pdf is not None else run_settings.get('skip_pdf', False)

    try:
        jira = JiraClient(config)
    except ConnectionError as e:
        print(f"Failed to initialize Jira Client: {e}")
        return

    analyzer = SprintAnalyzer(jira, config)

    for project_config in config.get('projects', []):
        results = analyzer.analyze(project_config)
        
        if results:
            reporter = Reporter(results)
            if final_report_type == 'daily':
                report_content = reporter.generate_daily_summary()
            else:
                report_content = reporter.generate_full_report()
            
            print(report_content)

            if final_export:
                project_key = project_config['project_key']
                filename = f"{project_key}_sprint_report_{final_report_type}"
                
                formats = ['md']
                if not final_skip_pdf:
                    formats.append('pdf')
                
                reporter.export_report(report_content, filename=filename, formats=formats)

@cli.command(name='discover-fields', help='Discover all available Jira fields and save them to a file.')
def discover_fields():
    config = load_config()
    try:
        jira = JiraClient(config)
    except ConnectionError as e:
        print(f"Failed to initialize Jira Client: {e}")
        return

    fields = jira.get_all_fields()
    if not fields:
        print("Could not discover any fields.")
        return

    # We are interested in the name and id of the fields
    field_data = {field['id']: field['name'] for field in fields}
    
    output_path = Path(__file__).parent.parent / 'jira_fields.yml'
    with open(output_path, 'w') as f:
        yaml.dump(field_data, f, default_flow_style=False, sort_keys=True)
    
    print(f"Successfully discovered {len(fields)} fields.")
    print(f"Field details have been saved to: {output_path}")
    print("You can now use this file to find the correct 'story_points_field' for your config.yaml.")

if __name__ == "__main__":
    cli()
