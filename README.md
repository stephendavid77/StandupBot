# Standup Bot

A CLI tool to connect to Jira and get a daily summary of the current sprint. This helps engineering managers run their daily stand-ups and identify risks in the sprint.

## Getting Started

### Prerequisites

- Python 3.9+
- Pip
- Git

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/StandupBot.git
    cd StandupBot
    ```

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

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## Project Structure

- `config/`: Contains the `config.yaml` for setup.
- `src/main.py`: The main CLI entry point.
- `src/jira_client.py`: Handles all communication with the Jira API.
- `src/analyzer.py`: Contains the logic for analyzing sprint data.
- `src/reporter.py`: Generates the reports from the analysis results.
- `requirements.txt`: Lists all Python dependencies.
- `reports/`: (New) Directory where generated reports are saved.