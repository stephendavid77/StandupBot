# StandupBot

This tool connects to Jira to provide daily insights into the health of your team's sprints, helping engineering managers identify risks and ensure good sprint hygiene.

## Features

- **Configurable:** Set up your Jira projects, board IDs, health thresholds, and default run behavior via a simple `config.yaml`.
- **Secure:** Uses `keyring` to securely store your Jira Personal Access Token (PAT).
- **Sprint Analysis:**
  - Calculates key metrics (progress, story points).
  - Performs a "Sprint Hygiene Check" (unassigned issues, missing estimates, issues without fix versions).
  - Identifies risks (blockers, overdue issues, stale tickets).
  - Filters out "Cancelled" issues from analysis.
- **Reporting:**
  - Generates concise daily summaries or full, detailed reports.
  - Includes "Issues Without Fix Versions" table and reflects this in sprint hygiene details.
  - Provides clear sprint duration (dates only), graceful goal display, and days left in sprint.
  - Jira board links are now in the updated format (e.g., `https://your-jira.atlassian.net/jira/software/c/projects/PROJECT_KEY/boards/BOARD_ID`).
  - CLI-based for easy integration and overrides.
  - Reports are now generated in the `/reports` folder in the project root.
- **Jira Field Discovery:**
  - A new command `discover-fields` helps you find all available Jira fields and their IDs, making it easier to configure custom fields like "Story Points".

## Setup

1.  **Clone the repository (or download the files).**

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the application:**
    - Copy `config/config.yaml.sample` to `config/config.yaml`.
    - Edit `config/config.yaml` with your Jira server URL, email, project details, and board IDs.
    - **Important:** You will need to provide the numeric ID for each Jira board. You can find this in the URL when viewing a board (e.g., `.../boards/123`).
    - **Jira Custom Fields**: Ensure that `story_points_field` and `epic_link_field` in your `config.yaml` are set to the correct custom field IDs for your Jira instance. For `epic_link_field`, this should typically be the field that links an issue to its Epic (e.g., `customfield_10014` for "Epic Link"), not the Epic's name. Refer to the "Jira Field Management" section for more details on how field IDs are handled.
    - In the `run_settings` section of the config, you can set the default behavior for report type, exporting, and PDF generation.

4.  **Set your Jira Personal Access Token (PAT):**
    - The tool will attempt to retrieve your Jira PAT from your system's keyring.
    - If you prefer to hardcode your PAT, you can add `api_token: "YOUR_JIRA_PAT"` under the `jira` section in your `config.yaml`.
    - To securely store your token in the keyring, run the following command. Replace the email and token with your own.
    ```bash
    python -c "import keyring; keyring.set_password('StandupBot', 'your-email@example.com', 'YOUR_JIRA_PAT')"
    ```

## Usage

The primary entry point is `src/main.py`.

### Running the Analysis

Simply run the `run` command. The default behavior will be controlled by the `run_settings` in your `config.yaml`.

```bash
python src/main.py run
```

### Overriding Configuration with Flags

You can override the settings from your config file by using command-line flags.

-   **Change report type:**
    ```bash
    python src/main.py run --report-type full
    ```

-   **Enable or disable exporting:**
    ```bash
    python src/main.py run --export
    python src/main.py run --no-export
    ```

-   **Skip or include PDF generation:**
    ```bash
    python src/main.py run --skip-pdf
    python src/main.py run --no-skip-pdf
    ```

### Jira Field Management

This tool now manages Jira field IDs more robustly using `jira_fields.yml`.

-   **`jira_fields.yml`**: This file, located in the project root, acts as a cache for your Jira instance's field IDs and their corresponding names. The application will automatically load field mappings from this file.
-   **Automatic Reloading**:
    -   If `jira_fields.yml` is empty or does not exist, the application will automatically fetch all fields from your Jira instance and populate `jira_fields.yml` on the first run.
    -   You can force a reload of these fields from the Jira API by setting `reload_fields_from_file: true` under the `jira` section in your `config.yaml`. This is useful if your Jira instance's custom field IDs change.
-   **`discover-fields` command**: You can still use the `discover-fields` command to manually generate or refresh `jira_fields.yml`. This is particularly useful for inspecting available fields or for initial setup.

```bash
python src/main.py discover-fields
```

## Project Structure

- `config/`: Contains the `config.yaml` for setup.
- `src/main.py`: The main CLI entry point.
- `src/jira_client.py`: Handles all communication with the Jira API.
- `src/analyzer.py`: Contains the logic for analyzing sprint data.
- `src/reporter.py`: Generates the reports from the analysis results.
- `requirements.txt`: Lists all Python dependencies.
- `reports/`: (New) Directory where generated reports are saved.

# Sprint Health Guidelines (under 'guidelines' section):
#   Configurable thresholds for various sprint health metrics:
#     max_overdue_days: Maximum days an issue can be overdue before being flagged.
#     max_unestimated_pct: Maximum percentage of unestimated issues allowed in a sprint.
#     max_unassigned_pct: Maximum percentage of unassigned issues allowed in a sprint.
#     max_tasks_per_dev: Maximum number of tasks (issues) assigned to a single developer.
#     max_blocked_pct: Maximum percentage of blocked issues allowed in a sprint.
#     max_in_progress_days: Maximum days an issue can be in "In Progress" status.
#     min_completed_pct: Minimum percentage of issues that should be completed by a certain point in the sprint.
#     max_scope_change_pct: Maximum percentage of scope change (added/removed issues) allowed in a sprint.
#     max_carried_over_pct: Maximum percentage of issues carried over from previous sprints.
#     max_critical_bugs_open: Maximum number of critical bugs allowed to be open.
#     max_reopened_pct: Maximum percentage of reopened issues allowed.
#     max_review_pending_days: Maximum days an issue can be in "Review Pending" status.
#     max_no_update_days: Maximum days an issue can go without any updates.
#     max_issues_without_fix_versions_pct: Maximum percentage of non-bug issues allowed without a fix version.
