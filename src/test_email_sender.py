import os
from pathlib import Path
from email_report import email_report  # Import the email sending function
import yaml  # To load config for recipient and sender details


def test_email():
    print("--- Running Email Functionality Test ---")

    # Load configuration to get recipient and sender details
    config_path = Path(__file__).parent.parent / "config/config.yaml"
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(
            "Error: config.yaml not found. Please ensure it exists and is correctly configured."
        )
        return
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}")
        return

    # Get recipient(s) from config.yaml
    run_settings = config.get("run_settings", {})
    recipient_emails = run_settings.get("email_recipient_email")

    if not recipient_emails:
        print(
            "Error: No recipient emails configured in config.yaml under 'run_settings.email_recipient_email'."
        )
        print("Please configure at least one recipient email to test.")
        return

    # Get sender details from config.yaml
    email_sender_settings = config.get("email_settings", {})
    sender_email = email_sender_settings.get("sender_email")
    sender_password = email_sender_settings.get("sender_password")
    smtp_server = email_sender_settings.get("smtp_server")
    smtp_port = email_sender_settings.get("smtp_port")

    # Create a dummy report file for testing
    test_report_dir = Path(__file__).parent.parent / "reports"
    os.makedirs(test_report_dir, exist_ok=True)
    test_report_path = test_report_dir / "test_email_report.md"
    report_content = "# Test Email Report\n\nThis is a sample report to test the email sending functionality.\n\nDate: August 18, 2025\n"
    with open(test_report_path, "w") as f:
        f.write(report_content)
    print(f"Created dummy report file: {test_report_path}")

    # Call the email_report function
    print("\nAttempting to send test email...")
    success = email_report(
        report_path=str(test_report_path),
        report_content=report_content,
        recipient_emails=recipient_emails,
        project_name="Test Project",
        sprint_name="Test Sprint",
        sprint_day_number=1,
        sender_email=sender_email,
        sender_password=sender_password,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
    )

    if success:
        print("\nTest email sent successfully!")
    else:
        print("\nFailed to send test email. Check the logs above for details.")

    # Clean up the dummy report file
    # os.remove(test_report_path)
    # print(f"Cleaned up dummy report file: {test_report_path}")