# Standup Bot

A web application to connect to Jira and get a daily summary of the current sprint. This helps engineering managers run their daily stand-ups and identify risks in the sprint.

## Features

- Web-based UI for easy report generation.
- Dockerized for easy setup and deployment.
- Highly configurable through a `config.yaml` file.
- Generates reports in Markdown and PDF format.
- Can send reports via email.

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

This is the most secure and flexible method. Pass your Jira email and Personal Access Token (PAT) as environment variables to the `docker run` command. Make sure your local `JIRA_EMAIL` and `JIRA_API_TOKEN` environment variables are set.

```bash
docker run -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/reports:/app/reports \
  -e JIRA_EMAIL=$JIRA_EMAIL \
  -e JIRA_API_TOKEN=$JIRA_API_TOKEN \
  standup-bot
```

#### Option B: Editing `config.yaml`

If you prefer not to use environment variables, you can hardcode your credentials in the `config/config.yaml` file. **Note:** This is less secure. Do not commit this file with your credentials to a public repository.

1.  Open `config/config.yaml`.
2.  Under the `jira` section, fill in your `user` and `api_token`:

    ```yaml
jira:
  server: "https://your-company.atlassian.net"
  user: "your-email@example.com"
  api_token: "YOUR_JIRA_PAT"
```

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
