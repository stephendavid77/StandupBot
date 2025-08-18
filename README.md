# StandupBot

This tool connects to Jira to provide daily insights into the health of your team's sprints, helping engineering managers identify risks and ensure good sprint hygiene.

## Features

- **Configurable:** Set up your Jira projects, board IDs, health thresholds, and default run behavior via a simple `config.yaml`.
- **Secure:** Uses `keyring` to securely store your Jira Personal Access Token (PAT).
- **Sprint Analysis:**
  - Calculates key metrics (progress, story points).
  - Performs a "Sprint Hygiene Check" (unassigned issues, missing estimates).
  - Identifies risks (blockers, overdue issues, stale tickets).
- **Reporting:**
  - Generates concise daily summaries or full, detailed reports.
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
    - In the `run_settings` section of the config, you can set the default behavior for report type, exporting, and PDF generation.

4.  **Set your Jira Personal Access Token (PAT):**
    - For security, the tool is designed to fetch your Jira PAT from your system's keychain.
    - Run the following command to securely store your token. Replace the email and token with your own.
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

### Discovering Jira Fields

Use the `discover-fields` command to generate a `jira_fields.yml` file containing all available Jira fields and their IDs. This is useful for configuring custom fields in `config.yaml`.

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