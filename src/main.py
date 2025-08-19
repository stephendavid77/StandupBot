import click
import yaml
from pathlib import Path
import shutil
from datetime import datetime, timezone, timedelta  # Added this import

from jira_client import JiraClient
from analyzer import SprintAnalyzer
from email_report import email_report
# Reporter classes will be imported dynamically based on report_type


def load_config():
    """
    Loads the configuration from config.yaml.
    """
    config_path = Path(__file__).parent.parent / "config/config.yaml"
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


def _load_jira_fields(config, jira_client):
    jira_fields_path = Path(__file__).parent.parent / "jira_fields.yml"
    jira_fields = {}

    # Load existing jira_fields.yml if it exists and is not empty
    if jira_fields_path.exists() and jira_fields_path.stat().st_size > 0:
        with open(jira_fields_path, "r") as f:
            jira_fields = yaml.safe_load(f) or {}

    reload_fields = config.get("jira", {}).get("reload_fields_from_file", False)

    if reload_fields or not jira_fields:
        print("Reloading Jira fields from API...")
        try:
            fetched_fields = jira_client.get_all_fields()
            jira_fields = {field["id"]: field["name"] for field in fetched_fields}
            with open(jira_fields_path, "w") as f:
                yaml.dump(jira_fields, f, default_flow_style=False, sort_keys=True)
            print(f"Successfully reloaded {len(jira_fields)} Jira fields.")
        except Exception as e:
            print(
                f"Error reloading Jira fields from API: {e}. Using cached fields if available."
            )
            # If reload fails, and no cached fields, exit or raise error
            if not jira_fields:
                print("No cached Jira fields available. Exiting.")
                exit(1)
    else:
        print("Using cached Jira fields from jira_fields.yml.")

    return jira_fields


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
def run(report_type, export, skip_pdf):
    print("Loading configuration...")
    config = load_config()
    print("Configuration loaded.")
    reports_dir = Path(__file__).parent.parent / "reports"
    if reports_dir.exists() and reports_dir.is_dir():
        print(f"Clearing existing reports in {reports_dir}...")
        for item in reports_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    reports_dir.mkdir(parents=True, exist_ok=True)
    print("Reports directory ready.")
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
    # Read the new flag
    send_email_report = run_settings.get("send_email_report", False)  # Default to False
    include_epics = run_settings.get("include_epics", False)

    try:
        print("Initializing Jira Client...")
        jira = JiraClient(config)
        print("Jira Client initialized.")
    except ConnectionError as e:
        print(f"Failed to initialize Jira Client: {e}")
        return

    # Load or reload Jira fields
    jira_field_mappings = _load_jira_fields(config, jira)
    # Update config with loaded field mappings, prioritizing config.yaml if present
    if "jira" not in config:
        config["jira"] = {}
    config["jira"]["field_mappings"] = jira_field_mappings

    analyzer = SprintAnalyzer(jira, config, include_epics=include_epics)

    for project_config in config.get("projects", []):
        project_key = project_config["project_key"]
        board_id = project_config["board_id"]
        print(
            f"Preparing analysis for project: {project_key} (Board ID: {board_id})..."
        )

        sprint_to_analyze = None
        if final_report_type == "previous":
            sprint_to_analyze = jira.get_last_closed_sprint(board_id)
        else:  # 'daily' or 'full'
            sprint_to_analyze = jira.get_active_sprint(board_id)

        if not sprint_to_analyze:
            print(
                f"No sprint found for analysis for project {project_key} with report type '{final_report_type}'. Skipping."
            )
            continue  # Skip to the next project

        print(
            f"Analyzing sprint: {sprint_to_analyze.name} for project: {project_key}..."
        )
        results = analyzer.analyze(project_config, sprint_to_analyze)

        if results:
            print(f"Analysis complete for project: {project_key}. Generating report...")

            # Determine which reporter to use
            if final_report_type in ["daily", "full"]:
                from current_sprint_reporter import CurrentSprintReporter

                reporter_instance = CurrentSprintReporter(
                    results, config, project_config
                )
                if final_report_type == "daily":
                    report_content = reporter_instance.generate_daily_summary()
                else:  # 'full'
                    report_content = reporter_instance.generate_full_report()
            elif final_report_type == "previous":
                from previous_sprint_reporter import PreviousSprintReporter

                reporter_instance = PreviousSprintReporter(
                    results, config, project_config
                )
                report_content = reporter_instance.generate_previous_sprint_report()

            print("Report generated. Printing to console...")
            print(report_content)

            if final_export:
                print("Exporting report...")
                filename = f"{project_key}_sprint_report_{final_report_type}"

                formats = ["md"]
                if not final_skip_pdf:
                    formats.append("pdf")

                reporter_instance.export_report(
                    report_content, filename=filename, formats=formats
                )
                print("Report export complete.")

                # Conditionally send email report
                if send_email_report:
                    print("Attempting to send email report...")
                    # Assuming the report is exported as .md and .pdf, we can choose which one to send
                    # For simplicity, let's send the .md file, or .pdf if it was generated.
                    report_to_email = Path(reports_dir) / f"{filename}.md"
                    if not final_skip_pdf:
                        pdf_report_path = Path(reports_dir) / f"{filename}.pdf"
                        if pdf_report_path.exists():
                            report_to_email = pdf_report_path  # Prefer PDF if generated

                    if report_to_email.exists():
                        recipient_emails = run_settings.get("email_recipient_email")

                        # Load email sender settings from config.yaml
                        email_sender_settings = config.get("email_settings", {})
                        sender_email = email_sender_settings.get("sender_email")
                        sender_password = email_sender_settings.get("sender_password")
                        smtp_server = email_sender_settings.get("smtp_server")
                        smtp_port = email_sender_settings.get("smtp_port")

                        if recipient_emails:
                            # Ensure recipient_emails is a list
                            if not isinstance(recipient_emails, list):
                                recipient_emails = [recipient_emails]

                            for recipient in recipient_emails:
                                print(f"Sending email to: {recipient}...")
                                # Calculate sprint day number for email subject
                                sprint_start_datetime = datetime.strptime(
                                    sprint_to_analyze.startDate, "%Y-%m-%dT%H:%M:%S.%fZ"
                                ).replace(tzinfo=timezone.utc)
                                now_utc = datetime.now(timezone.utc)

                                # Calculate working days
                                sprint_day_number = 0
                                current_date_iter = sprint_start_datetime.date()
                                while current_date_iter <= now_utc.date():
                                    # Check if it's a weekday (Monday=0, Sunday=6)
                                    if (
                                        current_date_iter.weekday() < 5
                                    ):  # Monday to Friday
                                        sprint_day_number += 1
                                    current_date_iter += timedelta(days=1)

                                if sprint_day_number < 1:
                                    sprint_day_number = 1  # Ensure it's at least day 1

                                email_success = email_report(
                                    report_path=str(report_to_email),
                                    report_content=report_content,
                                    recipient_emails=recipient,
                                    project_name=project_key,
                                    sprint_name=sprint_to_analyze.name,
                                    sprint_day_number=sprint_day_number,
                                    sender_email=sender_email,
                                    sender_password=sender_password,
                                    smtp_server=smtp_server,
                                    smtp_port=smtp_port,
                                )
                                if email_success:
                                    print(
                                        f"Email report sent successfully to {recipient}."
                                    )
                                else:
                                    print(
                                        f"Failed to send email report to {recipient}."
                                    )
                        else:
                            print(
                                "email_recipient_email not set in config.yaml. Skipping email report."
                            )
                    else:
                        print(
                            f"Report file for email not found at {report_to_email}. Skipping email."
                        )
            else:
                print("Email report not sent as export is disabled.")
        else:
            print(
                f"No analysis results for project: {project_key}. Skipping report generation."
            )


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

    # We are interested in the name and id of the fields
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
