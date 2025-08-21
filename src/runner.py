import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.services.jira_service import JiraClient
from src.analyzer import SprintAnalyzer
from src.services.email_service import email_report

def execute_run(config, report_type, include_epics, debug_messages=None):
    """
    Core logic for sprint analysis and report generation.
    """
    summary = []
    exported_files = []
    logging.info("--- Starting Report Generation ---")
    if debug_messages:
        for msg in debug_messages:
            logging.info(msg)

    run_settings = config.get("run_settings", {})
    logging.info(f"Loaded run_settings from config: {run_settings}")
    
    reports_dir = Path(__file__).parent.parent / "reports"
    if reports_dir.exists() and reports_dir.is_dir():
        for item in reports_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    reports_dir.mkdir(parents=True, exist_ok=True)

    try:
        jira = JiraClient(config)
    except ConnectionError as e:
        summary.append(f"Failed to initialize Jira Client: {e}")
        logging.error(f"Failed to initialize Jira Client: {e}")
        return {"summary": summary, "exported_files": []}

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
            msg = f"No sprint found for analysis for project {project_key} with report type '{report_type}'. Skipping."
            summary.append(msg)
            logging.warning(msg)
            continue

        results = analyzer.analyze(project_config, sprint_to_analyze)

        if results:
            summary.append(f"Successfully generated {report_type} report for project: {project_key}.")

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

            filename = f"{project_key}_sprint_report_{report_type}"

            formats = ["md", "html", "excel"]
            summary.append(f"Generating reports in the following formats: {formats}")
            successful_files, error_messages = reporter_instance.export_report(report_content, filename=filename, formats=formats)
            exported_files.extend(successful_files)
            for f in successful_files:
                summary.append(f"Report exported to {f}")
            for e in error_messages:
                summary.append(e)

        else:
            summary.append(f"No analysis results for project: {project_key}. Skipping report generation.")
            
    return {"summary": summary, "exported_files": exported_files}
