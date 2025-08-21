import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
import markdown2

def email_report(
    report_path,
    report_content,
    recipient_emails,
    project_name,
    sprint_name,
    sprint_day_number,
    sender_email=None,
    sender_password=None,
    smtp_server=None,
    smtp_port=None,
):
    """
    Emails the generated report.
    Returns a tuple (success, message).
    """
    if not isinstance(recipient_emails, list):
        recipient_emails = [recipient_emails]

    # Get credentials
    sender_email = sender_email or os.getenv("EMAIL_SENDER_EMAIL")
    sender_password = sender_password or os.getenv("EMAIL_SENDER_PASSWORD")
    smtp_server = smtp_server or os.getenv("EMAIL_SMTP_SERVER")
    smtp_port = smtp_port or os.getenv("EMAIL_SMTP_PORT")

    if not all([sender_email, sender_password, smtp_server, smtp_port]):
        msg = "Email configuration missing. Please set sender_email, sender_password, smtp_server, and smtp_port in config.yaml or as environment variables."
        logging.error(msg)
        return False, msg

    try:
        smtp_port = int(smtp_port)
    except (ValueError, TypeError):
        msg = f"Invalid SMTP port '{smtp_port}'. Must be an integer."
        logging.error(msg)
        return False, msg

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipient_emails)
    msg["Subject"] = f"{project_name} Sprint Report - {sprint_name} - Day {sprint_day_number}"

    try:
        with open(report_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=Path(report_path).name)
        part["Content-Disposition"] = f'attachment; filename="{Path(report_path).name}"'
        msg.attach(part)
    except FileNotFoundError:
        msg = f"Report file not found at {report_path}"
        logging.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Error attaching file {report_path}: {e}"
        logging.error(msg)
        return False, msg

    html_body = markdown2.markdown(report_content, extras=["tables", "fenced-code-blocks"])
    css_style = """
    <style>
      body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
      h1, h2, h3, h4 { color: #333; margin-top: 1em; margin-bottom: 0.5em; }
      table { width: 100%; border-collapse: collapse; margin-bottom: 1em; }
      th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
      th { background-color: #f2f2f2; }
    </style>
    """
    html_body_with_css = f'<html><head><meta charset="UTF-8"><title>Sprint Report</title>{css_style}</head><body>{html_body}</body></html>'
    msg.attach(MIMEText(html_body_with_css, "html"))

    try:
        logging.info(f"Connecting to SMTP server: {smtp_server}:{smtp_port}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        msg = f"Email sent successfully to {', '.join(recipient_emails)}."
        logging.info(msg)
        return True, msg
    except smtplib.SMTPAuthenticationError as e:
        msg = f"SMTP authentication failed. Check your sender email and password. Error: {e}"
        logging.error(msg)
        return False, msg
    except smtplib.SMTPConnectError as e:
        msg = f"Could not connect to SMTP server. Check server address and port. Error: {e}"
        logging.error(msg)
        return False, msg
    except Exception as e:
        msg = f"An unexpected error occurred while sending email: {e}"
        logging.error(msg)
        return False, msg
