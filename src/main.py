import click
import yaml
from pathlib import Path

from src.jira_client import JiraClient
from src.runner import execute_run

def load_config():
    """
    Loads the configuration from config.yaml.
    """
    config_path = Path(__file__).parent.parent / "config/config.yaml"
    if not config_path.exists():
        print("config.yaml not found, using config.yaml.sample")
        config_path = Path(__file__).parent.parent / "config/config.yaml.sample"

    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(
            "Error: config.yaml not found. Please copy config.yaml.sample and fill it out."
        )
        exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}")
        exit(1)

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    A CLI tool to get daily sprint health insights from Jira.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)

@cli.command(name="run", help="Run the sprint analysis and generate a report.")
@click.option(
    "--report-type",
    "-r",
    type=click.Choice(["daily", "full", "previous"]),
    default=None,
    help="Override the report type from config.",
)
@click.option(
    "--export/--no-export",
    "-e",
    default=None,
    help="Enable or disable report exporting, overriding config.",
)
@click.option(
    "--skip-pdf/--no-skip-pdf",
    default=None,
    help="Skip or include PDF generation, overriding config.",
)
@click.option(
    "--include-epics/--no-include-epics",
    default=None,
    help="Include epics in the report, overriding config.",
)
@click.option(
    "--send-email-report/--no-send-email-report",
    default=None,
    help="Send email report, overriding config.",
)
def run(report_type, export, skip_pdf, include_epics, send_email_report):
    print("Loading configuration...")
    config = load_config()
    print("Configuration loaded.")

    run_settings = config.get("run_settings", {})

    # Determine final settings, with CLI flags taking precedence over config file
    final_report_type = (
        report_type
        if report_type is not None
        else run_settings.get("report_type", "daily")
    )
    final_export = export if export is not None else run_settings.get("export", False)
    final_skip_pdf = (
        skip_pdf if skip_pdf is not None else run_settings.get("skip_pdf", False)
    )
    final_include_epics = (
        include_epics if include_epics is not None else run_settings.get("include_epics", False)
    )
    final_send_email_report = (
        send_email_report if send_email_report is not None else run_settings.get("send_email_report", False)
    )

    try:
        print("Initializing Jira Client...")
        jira_client = JiraClient(config)
        print("Jira Client initialized.")
        jira_fields = jira_client.load_jira_fields()
        if "jira" not in config:
            config["jira"] = {}
        config["jira"]["field_mappings"] = jira_fields

        execute_run(config, final_report_type, final_export, final_skip_pdf, final_include_epics, final_send_email_report)

    except ConnectionError as e:
        print(f"Failed to initialize Jira Client: {e}")
        return

@cli.command(
    name="discover-fields",
    help="Discover all available Jira fields and save them to a file.",
)
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

    field_data = {field["id"]: field["name"] for field in fields}

    output_path = Path(__file__).parent.parent / "jira_fields.yml"
    with open(output_path, "w") as f:
        yaml.dump(field_data, f, default_flow_style=False, sort_keys=True)

    print(f"Successfully discovered {len(fields)} fields.")
    print(f"Field details have been saved to: {output_path}")
    print(
        "You can now use this file to find the correct 'story_points_field' for your config.yaml."
    )

if __name__ == "__main__":
    cli()