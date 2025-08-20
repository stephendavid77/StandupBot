import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.jira_client import JiraClient
from src.analyzer import SprintAnalyzer
from src.email_report import email_report

def execute_run(config, report_type, export, skip_pdf, include_epics, send_email_report):
    """
    Core logic for sprint analysis and report generation.
    """
    summary = []
    reports_dir = Path(__file__).parent.parent / "reports"
    if reports_dir.exists() and reports_dir.is_dir():
        shutil.rmtree(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    try:
        jira = JiraClient(config)
    except ConnectionError as e:
        summary.append(f"Failed to initialize Jira Client: {e}")
        return summary

    analyzer = SprintAnalyzer(jira, config, include_epics=include_epics)

    for project_config in config.get("projects", []):
        project_key = project_config["project_key"]
        board_id = project_config["board_id"]

        sprint_to_analyze = None
        if report_type == "previous":
            sprint_to_analyze = jira.get_last_closed_sprint(board_id)
        else:
            sprint_to_analyze = jira.get_active_sprint(board_id)

        if not sprint_to_analyze:
            summary.append(f"No sprint found for analysis for project {project_key} with report type '{report_type}'. Skipping.")
            continue

        results = analyzer.analyze(project_config, sprint_to_analyze)

        if results:
            summary.append(f"Analysis complete for project: {project_key}. Generating report...")

            if report_type in ["daily", "full"]:
                from src.current_sprint_reporter import CurrentSprintReporter
                reporter_instance = CurrentSprintReporter(results, config, project_config)
                if report_type == "daily":
                    report_content = reporter_instance.generate_daily_summary()
                else:
                    report_content = reporter_instance.generate_full_report()
            elif report_type == "previous":
                from src.previous_sprint_reporter import PreviousSprintReporter
                reporter_instance = PreviousSprintReporter(results, config, project_config)
                report_content = reporter_instance.generate_previous_sprint_report()

            summary.append(f"Report for {project_key} generated.")

            if export:
                filename = f"{project_key}_sprint_report_{report_type}"
                formats = ["md"]
                if not skip_pdf:
                    formats.append("pdf")

                exported_files = reporter_instance.export_report(report_content, filename=filename, formats=formats)
                for f in exported_files:
                    summary.append(f"Report exported to {f}")

                if send_email_report:
                    report_to_email = Path(reports_dir) / f"{filename}.md"
                    if not skip_pdf:
                        pdf_report_path = Path(reports_dir) / f"{filename}.pdf"
                        if pdf_report_path.exists():
                            report_to_email = pdf_report_path

                    if report_to_email.exists():
                        run_settings = config.get("run_settings", {})
                        recipient_emails = run_settings.get("email_recipient_email")
                        email_sender_settings = config.get("email_settings", {})
                        sender_email = email_sender_settings.get("sender_email")
                        sender_password = email_sender_settings.get("sender_password")
                        smtp_server = email_sender_settings.get("smtp_server")
                        smtp_port = email_sender_settings.get("smtp_port")

                        if recipient_emails:
                            if not isinstance(recipient_emails, list):
                                recipient_emails = [recipient_emails]

                            for recipient in recipient_emails:
                                sprint_start_datetime = datetime.strptime(sprint_to_analyze.startDate, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
                                now_utc = datetime.now(timezone.utc)
                                sprint_day_number = 0
                                current_date_iter = sprint_start_datetime.date()
                                while current_date_iter <= now_utc.date():
                                    if current_date_iter.weekday() < 5:
                                        sprint_day_number += 1
                                    current_date_iter += timedelta(days=1)
                                if sprint_day_number < 1:
                                    sprint_day_number = 1

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
                                    summary.append(f"Email report sent successfully to {recipient}.")
                                else:
                                    summary.append(f"Failed to send email report to {recipient}.")
                        else:
                            summary.append("email_recipient_email not set in config.yaml. Skipping email report.")
                    else:
                        summary.append(f"Report file for email not found at {report_to_email}. Skipping email.")
            else:
                summary.append("Report generation complete. Export was not enabled.")
        else:
            summary.append(f"No analysis results for project: {project_key}. Skipping report generation.")
            
    return summary
