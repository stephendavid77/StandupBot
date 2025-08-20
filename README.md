# Standup Bot

A web application to connect to Jira and get a daily summary of the current sprint. This helps engineering managers run their daily stand-ups and identify risks in the sprint.

## Features

-   **Web-based UI:** An intuitive interface for easy report generation.
-   **Dockerized:** For easy setup and deployment.
-   **Highly Configurable:** Use a `config.yaml` file to manage all your settings.
-   **Multiple Report Formats:** Generates reports in Markdown and PDF format.
-   **Email Integration:** Can send reports via email.
-   **Engaging Loading Screen:** While you wait, the UI displays an animated timer and cycles through a list of interesting facts.
-   **Graceful Fallbacks:** Provides a basic loading message even if JavaScript is disabled.

## Pre-requisites

To run this application, you will need to have Docker installed on your machine.

### Docker Installation (macOS)

1.  **Download Docker Desktop:** Go to the [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop) website and download the installer.
2.  **Install Docker Desktop:** Double-click the downloaded `.dmg` file and drag the Docker icon to your Applications folder.
3.  **Start Docker Desktop:** Open the Docker application from your Applications folder. You will see the Docker icon in your menu bar when it's running.

## Configuration

1.  **Create a `config.yaml` file:** Copy the `config/config.yaml.sample` file to `config/config.yaml`.

    ```bash
    cp config/config.yaml.sample config/config.yaml
    ```

2.  **Edit `config.yaml`:** Open the `config/config.yaml` file and fill in your Jira server URL, project details, and board IDs.

## Running the Application with Docker

### 1. Build the Docker Image

Open your terminal, navigate to the project's root directory, and run the following command to build the Docker image:

```bash
docker build -t standup-bot .
```

### 2. Run the Docker Container

To run the application, you need to provide your Jira credentials. You can do this in two ways:

#### Option A: Using Environment Variables (Recommended)

This is the most secure and flexible method. Pass your Jira and email credentials as environment variables to the `docker run` command. Make sure the following environment variables are set in your local terminal:

-   `JIRA_EMAIL`
-   `JIRA_API_TOKEN`
-   `EMAIL_SENDER_EMAIL` (only required if sending email)
-   `EMAIL_SENDER_PASSWORD` (only required if sending email)
-   `EMAIL_SMTP_SERVER` (only required if sending email)
-   `EMAIL_SMTP_PORT` (only required if sending email)

```bash
docker run -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/reports:/app/reports \
  -e JIRA_EMAIL=$JIRA_EMAIL \
  -e JIRA_API_TOKEN=$JIRA_API_TOKEN \
  -e EMAIL_SENDER_EMAIL=$EMAIL_SENDER_EMAIL \
  -e EMAIL_SENDER_PASSWORD=$EMAIL_SENDER_PASSWORD \
  -e EMAIL_SMTP_SERVER=$EMAIL_SMTP_SERVER \
  -e EMAIL_SMTP_PORT=$EMAIL_SMTP_PORT \
  standup-bot
```

#### Option B: Editing `config.yaml`

If you prefer not to use environment variables, you can hardcode your credentials in the `config/config.yaml` file. **Note:** This is less secure. Do not commit this file with your credentials to a public repository.

1.  Open `config/config.yaml`.
2.  Under the `jira` and `email_settings` sections, fill in your credentials.

3.  Run the container without the `-e` flags:

    ```bash
docker run -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/reports:/app/reports \
  standup-bot
```

## Accessing the Web UI

Once the container is running, open your web browser and navigate to:

[http://localhost:8000](http://localhost:8000)

You can now configure and run your reports from the web interface.

## Troubleshooting

-   **`WORKER TIMEOUT` Error:** If you see a worker timeout error in the logs, it means the report generation is taking longer than the default timeout. The current timeout is set to 3 minutes. If you need to increase it further, you can modify the `--timeout` value in the `CMD` instruction of the `Dockerfile`.

-   **`JiraError HTTP 503`:** This is a "Service Unavailable" error from the Jira server. It means Jira is temporarily down or overloaded. Check the [Atlassian Status Page](https://status.atlassian.com/) and try again later.

-   **`JSONDecodeError`:** If you encounter this error, it means the `interesting_facts.json` file has a syntax error. Please ensure the file contains valid JSON.

## CLI Usage (Optional)

This application can also be run as a CLI tool. The usage is the same as before.

### Running the Analysis

```bash
python src/main.py run
```

### Overriding Configuration with Flags

```bash
python src/main.py run --report-type full --export
```