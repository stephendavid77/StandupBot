import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
import markdown2

def email_report(report_path, report_content, recipient_emails, sender_email=None, sender_password=None, smtp_server=None, smtp_port=None):
    """
    Emails the generated report.

    Args:
        report_path (str): The absolute path to the report file (e.g., Markdown or PDF).
        report_content (str): The Markdown content of the report to be included in the email body.
        recipient_emails (list or str): The email address(es) of the recipient(s). Can be a single string or a list of strings.
        sender_email (str, optional): The sender's email address. Defaults to environment variable.
        sender_password (str, optional): The sender's email password or app-specific password. Defaults to environment variable.
        smtp_server (str, optional): The SMTP server address. Defaults to environment variable.
        smtp_port (int, optional): The SMTP server port. Defaults to environment variable.
    """
    # Ensure recipient_emails is a list
    if not isinstance(recipient_emails, list):
        recipient_emails = [recipient_emails]

    print(f"--- Email Send Flow Triggered for report: {Path(report_path).name} ---")
    print(f"Attempting to email report to {', '.join(recipient_emails)}...")

    # Try to get values from arguments (config.yaml) first
    # If not provided as argument or is an empty string, try environment variables
    if sender_email is None or sender_email == '': # Check for None or empty string
        _env_val = os.getenv("EMAIL_SENDER_EMAIL")
        print(f"DEBUG: os.getenv('EMAIL_SENDER_EMAIL') returned: '{_env_val}'") # Added debug print
        sender_email = _env_val
        if sender_email is not None and sender_email != '': # Check for None or empty string from env
            print("- Sender Email: Retrieved from Environment Variable")
        else:
            print("- Sender Email: Not Set (neither in config nor env)")
    else:
        print("- Sender Email: Retrieved from Config")

    if sender_password is None or sender_password == '': # Check for None or empty string
        _env_val = os.getenv("EMAIL_SENDER_PASSWORD")
        print(f"DEBUG: os.getenv('EMAIL_SENDER_PASSWORD') returned: '{_env_val}'") # Added debug print
        sender_password = _env_val
        if sender_password is not None and sender_password != '': # Check for None or empty string from env
            print("- Sender Password: Retrieved from Environment Variable")
        else:
            print("- Sender Password: Not Set (neither in config nor env)")
    else:
        print("- Sender Password: Retrieved from Config")

    if smtp_server is None or smtp_server == '': # Check for None or empty string
        _env_val = os.getenv("EMAIL_SMTP_SERVER")
        print(f"DEBUG: os.getenv('EMAIL_SMTP_SERVER') returned: '{_env_val}'") # Added debug print
        smtp_server = _env_val
        if smtp_server is not None and smtp_server != '': # Check for None or empty string from env
            print("- SMTP Server: Retrieved from Environment Variable")
        else:
            print("- SMTP Server: Not Set (neither in config nor env)")
    else:
        print("- SMTP Server: Retrieved from Config")

    if smtp_port is None or smtp_port == '': # Check for None or empty string
        _env_val = os.getenv("EMAIL_SMTP_PORT")
        print(f"DEBUG: os.getenv('EMAIL_SMTP_PORT') returned: '{_env_val}'") # Added debug print
        smtp_port = _env_val
        if smtp_port is not None and smtp_port != '': # Check for None or empty string from env
            print("- SMTP Port: Retrieved from Environment Variable")
        else:
            print("- SMTP Port: Not Set (neither in config nor env)")
    else:
        print("- SMTP Port: Retrieved from Config")

    # Convert port to int, with default if still None
    if smtp_port is None:
        smtp_port = 587 # Default if not set anywhere
        print(f"- SMTP Port: Defaulted to {smtp_port}")
    try:
        smtp_port = int(smtp_port)
    except ValueError:
        print(f"Error: Invalid SMTP port '{smtp_port}'. Must be an integer.")
        print("--- Email Send Flow Failed ---")
        return False


    if not all([sender_email, sender_password, smtp_server]): # smtp_port is now guaranteed to be int or cause error
        print("Error: Email configuration missing. Please set sender_email, sender_password, and smtp_server in config.yaml or as environment variables.")
        print("--- Email Send Flow Failed ---")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails) # Join multiple recipients with a comma
    msg['Subject'] = f"StandupBot Sprint Report - {Path(report_path).stem}"

    # Attach the report file
    try:
        with open(report_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=Path(report_path).name)
        part['Content-Disposition'] = f'attachment; filename="{Path(report_path).name}"'
        msg.attach(part)
        print(f"Attached report: {Path(report_path).name}")
    except FileNotFoundError:
        print(f"Error: Report file not found at {report_path}")
        print("--- Email Send Flow Failed ---")
        return False
    except Exception as e:
        print(f"Error attaching file {report_path}: {e}")
        print("--- Email Send Flow Failed ---")
        return False

    # Convert Markdown report_content to HTML for the email body
    html_body = markdown2.markdown(report_content, extras=['tables', 'fenced-code-blocks'])

    # Add basic CSS for table styling (re-using from PdfGenerator)
    css_style = """
<style>
  body {
      font-family: Arial, sans-serif;
      margin: 20px;
      line-height: 1.6;
  }
  h1, h2, h3, h4 {
      color: #333;
      margin-top: 1em;
      margin-bottom: 0.5em;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1em;
  }
  th, td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: left;
  }
  th {
    background-color: #f2f2f2;
  }
  pre {
      background-color: #f8f8f8;
      padding: 10px;
      border-radius: 4px;
      overflow-x: auto;
  }
  code {
      font-family: monospace;
  }
  ul, ol {
      margin-bottom: 1em;
      padding-left: 20px;
  }
  hr {
      border: none;
      border-top: 1px solid #ccc;
      margin: 1em 0;
  }
</style>
"""

    # Inject CSS into the HTML content
    html_body_with_css = f"<html><head><meta charset=\"UTF-8\"><title>Sprint Report</title>{css_style}</head><body>{html_body}</body></html>"

    # Attach the HTML content to the email
    msg.attach(MIMEText(html_body_with_css, 'html'))

    try:
        print(f"Connecting to SMTP server: {smtp_server}:{smtp_port}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.send_message(msg) # send_message can take a list of recipients
        print("Email sent successfully!")
        print("--- Email Send Flow Completed Successfully ---")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Error: SMTP authentication failed. Check your sender email and password.")
        print("For Gmail, you might need to use an App Password if 2FA is enabled.")
        print("--- Email Send Flow Failed ---")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"Error: Could not connect to SMTP server. Check server address and port. Error: {e}")
        print("--- Email Send Flow Failed ---")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")
        print("--- Email Send Flow Failed ---")
        return False

if __name__ == "__main__":
    pass