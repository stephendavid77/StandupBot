from flask import Blueprint, render_template, request, send_from_directory
from flask_login import login_required
from pathlib import Path
import logging
import json

from src.utils.helpers import get_config, REPORTS_DIR
from src.services.jira_service import JiraClient
from src.services.email_service import email_report
from src.runner import execute_run

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    config = get_config()
    run_settings = config.get('run_settings', {})
    projects = config.get('projects', [])
    
    facts_path = Path(__file__).parent.parent.parent / "interesting_facts.json"
    if facts_path.exists():
        with open(facts_path, "r") as f:
            interesting_facts = json.load(f)["facts"]
    else:
        interesting_facts = []
    
    return render_template('index.html', run_settings=run_settings, projects=projects, interesting_facts=interesting_facts)

@main_bp.route('/run', methods=['POST'])
@login_required
def run_report():
    report_type = request.form.get('report_type')
    include_epics = 'include_epics' in request.form

    # Process selected projects
    selected_project_keys = request.form.getlist('selected_projects')
    config = get_config()
    all_projects = config.get('projects', [])
    projects_to_run = [p for p in all_projects if p['project_key'] in selected_project_keys]

    # Process newly added projects
    new_project_keys = [v for k, v in request.form.items() if k.startswith('new_project_key')]
    new_board_ids = [v for k, v in request.form.items() if k.startswith('new_board_id')]

    for i in range(len(new_project_keys)):
        projects_to_run.append({"project_key": new_project_keys[i], "board_id": int(new_board_ids[i])})

    debug_messages = [
        f"Report Type: {report_type}",
        f"Include Epics: {include_epics}",
        f"Projects to run: {[p['project_key'] for p in projects_to_run]}"
    ]

    try:
        jira_client = JiraClient(config)
        jira_fields = jira_client.load_jira_fields()
        if 'jira' not in config:
            config['jira'] = {}
        config['jira']['field_mappings'] = jira_fields

        # The config passed to execute_run will now have the user-selected projects
        config['projects'] = projects_to_run

        result = execute_run(config, report_type, include_epics, debug_messages)
        
        exported_files_relative = [Path(f).relative_to(REPORTS_DIR) for f in result['exported_files']]

        return render_template('result.html', summary=result['summary'], exported_files=exported_files_relative)
    except Exception as e:
        logging.exception("An unexpected error occurred during report generation:")
        summary = [f"An unexpected error occurred: {e}"]
        return render_template('result.html', summary=summary, exported_files=[])

@main_bp.route('/reports/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)

@main_bp.route('/send_email', methods=['POST'])
@login_required
def send_email():
    recipient_emails = request.form.getlist('recipient_emails')
    files_to_send = request.form.getlist('files_to_send')

    config = get_config()
    email_sender_settings = config.get("email_settings", {})
    sender_email = email_sender_settings.get("sender_email")
    sender_password = email_sender_settings.get("sender_password")
    smtp_server = email_sender_settings.get("smtp_server")
    smtp_port = email_sender_settings.get("smtp_port")

    email_results = []

    if not recipient_emails:
        email_results.append("No recipient emails provided.")
        return render_template('email_sent.html', email_results=email_results)

    if not files_to_send:
        email_results.append("No files selected to send.")
        return render_template('email_sent.html', email_results=email_results)

    for file_path_relative in files_to_send:
        file_path_absolute = REPORTS_DIR / file_path_relative
        if not file_path_absolute.exists():
            email_results.append(f"Error: File not found for email: {file_path_relative}")
            continue

        # For simplicity, assuming report_content can be read from the file for now
        # In a real app, you might pass report_content from the previous step
        try:
            with open(file_path_absolute, 'r') as f:
                report_content = f.read()
        except Exception as e:
            email_results.append(f"Error reading file {file_path_relative} for email: {e}")
            continue

        # Extract project_name, sprint_name, sprint_day_number from filename or pass from previous step
        # For now, using dummy values or parsing from filename
        # Example: AH_sprint_report_daily.md
        parts = file_path_relative.stem.split('_')
        project_name = parts[0] if len(parts) > 0 else "Report"
        sprint_name = parts[2] if len(parts) > 2 else "Sprint"
        report_type_part = parts[3] if len(parts) > 3 else "daily"
        sprint_day_number = 1 # Dummy value

        for recipient in recipient_emails:
            if not recipient:
                continue
            success, message = email_report(
                report_path=str(file_path_absolute),
                report_content=report_content,
                recipient_emails=recipient,
                project_name=project_name,
                sprint_name=sprint_name,
                sprint_day_number=sprint_day_number,
                sender_email=sender_email,
                sender_password=sender_password,
                smtp_server=smtp_server,
                smtp_port=smtp_port
            )
            email_results.append(message)
    
    return render_template('email_sent.html', email_results=email_results)
