from flask import Flask, render_template, request, redirect, url_for, flash
import yaml
from pathlib import Path
from src.runner import execute_run
from src.jira_client import JiraClient

app = Flask(__name__)
app.secret_key = 'super secret key'

def get_config():
    config_path = Path(__file__).parent / "config/config.yaml"
    if not config_path.exists():
        config_path = Path(__file__).parent / "config/config.yaml.sample"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

@app.route('/')
def index():
    config = get_config()
    run_settings = config.get('run_settings', {})
    projects = config.get('projects', [])
    return render_template('index.html', run_settings=run_settings, projects=projects)

@app.route('/run', methods=['POST'])
def run_report():
    report_type = request.form.get('report_type')
    export = 'export' in request.form
    skip_pdf = 'skip_pdf' in request.form
    include_epics = 'include_epics' in request.form
    send_email_report = 'send_email_report' in request.form

    try:
        config = get_config()
        jira_client = JiraClient(config)
        jira_fields = jira_client.load_jira_fields()
        if 'jira' not in config:
            config['jira'] = {}
        config['jira']['field_mappings'] = jira_fields

        execute_run(config, report_type, export, skip_pdf, include_epics, send_email_report)
        flash('Report generation finished successfully!', 'success')
    except Exception as e:
        flash(f"An error occurred: {e}", 'danger')

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
