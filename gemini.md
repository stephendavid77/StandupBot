# Gemini Context File for StandupBot Project

This file serves as a persistent context for the Gemini CLI agent to track progress and ongoing tasks for the StandupBot project.

---

## Project Overview

*   **Project Name:** StandupBot
*   **Goal:** Transform CLI tool into a sophisticated web application with user authentication, secure credential storage, and enhanced reporting features.

---

## Tech Stack

*   **Backend:** Flask (Python web framework)
*   **Database:** SQLite (local, file-based, managed with Flask-SQLAlchemy)
*   **Authentication:** Flask-Login (for user sessions and authentication)
*   **Password Hashing:** Werkzeug.security
*   **Jira Integration:** Python Jira library
*   **Email Sending:** Python's smtplib, email.mime
*   **Report Generation:**
    *   Markdown: markdown2 (Python library)
    *   HTML: markdown2 (Python library)
    *   Excel: openpyxl (Python library)
*   **Containerization:** Docker

---

## Application Flow

### 1. User Authentication

*   **Registration:** Users can register with first name, last name, username, and password. Data is stored in a local SQLite database.
*   **Login:** Registered users can log in with their username and password.
*   **Logout:** Users can log out, ending their session.

### 2. Report Generation

*   **Landing Page (`/`):**
    *   Requires user login.
    *   Allows selection of report type (Daily, Complete, Previous Sprint) with descriptions.
    *   Displays pre-configured projects from `config.yaml` with checkboxes for selection/deselection.
    *   Allows dynamic addition of new projects (Project Key, Board ID).
    *   Includes an engaging loading screen with animated timer and cycling interesting facts.
*   **Report Execution (`/run`):
    *   Receives selected report type, projects, and other options from the form.
    *   Connects to Jira using credentials (currently from `config.yaml` or environment variables).
    *   Performs sprint analysis and generates reports in Markdown, HTML, and Excel formats.
    *   Returns a summary of operations and paths to generated files.
*   **Results Page (`/result`):
    *   Displays a high-level summary of the report generation operation.
    *   Provides download links for generated `.md`, `.html`, and `.xlsx` files.
    *   (Planned) Will include email sending functionality.

### 3. Email Functionality (Planned)

*   **Email Form:** On the results page, users can choose to send the generated reports via email.
*   **Recipient Input:** Allows adding multiple recipient email addresses dynamically.
*   **Email Sending:** Sends the report content as an attachment.

### 4. File Management

*   Generated reports are stored in the `reports/` directory.
*   (Planned) Reports will be unique per session and automatically deleted after 30 minutes.

---

## Current Phase: Phase 2 - Onboarding & Secure Credential Storage

*   **Objective:** Implement user onboarding for Jira/Email credentials and store them securely.

---

## Recent Progress & Status

*   **Last Completed Major Task:** Phase 1 (Database Setup & User Authentication) is working.
*   **Current Task:** Implementing email functionality on the results page.
    *   `src/runner.py`: Email sending logic removed from `execute_run`.
    *   `app.py`: New `/send_email` route added.
    *   `templates/email_sent.html`: Created.
    *   `templates/result.html`: Email form added.
    *   `templates/loader.html`: Created as a separate module.
    *   `templates/index.html`: Updated to include `loader.html` and new UI elements.
    *   `src/controllers/auth_controller.py`: Authentication logic moved here.
    *   `src/controllers/main_controller.py`: Main app logic moved here.
    *   `src/models.py`: User model moved here.
    *   `src/utils/helpers.py`: `get_config` and `REPORTS_DIR` moved here.
    *   `src/services/jira_service.py`: `JiraClient` moved here.
    *   `src/services/email_service.py`: `email_report` moved here.
    *   `src/excel_generator.py`: Added for Excel report generation.
    *   `src/analyzer.py`: Restored missing methods and refactored to use logging.
    *   `src/reporter.py`: Updated for HTML/Excel export and improved error handling.
    *   `src/current_sprint_reporter.py`, `src/previous_sprint_reporter.py`: Restored report generation logic and refactored to use logging.

---

## Outstanding Issues / Debugging

*   **Issue:** Email is not being sent, and confirmation messages are not displayed in the UI.
*   **Last Reported Error:** `AttributeError: 'str' object has no attribute 'stem'` (from `app.py` line 127 in `send_email` function). This was fixed by converting `file_path_relative` to `Path` object.
*   **Current Debugging Focus:** The `send_email` function in `app.py` is still the focus. The error `AttributeError: 'str' object has no attribute 'stem'` was fixed, but the user is still reporting that email is not sent and no confirmation message is displayed. This implies the `email_report` function is failing or the `email_results` list is not being populated correctly.

---

## Next Steps

*   **Immediate Action:** Debug the email sending issue in the `/send_email` route in `app.py`.
*   **Subsequent Actions (Phase 2):**
    *   Implement secure credential storage (encryption).
    *   Integrate onboarding flow.
    *   Update `jira_service.py` and `email_service.py` to use DB credentials.

---

_Last Updated by Gemini: August 20, 2025 21:10 PM_
