import importlib
import os
import logging
from pathlib import Path
import yaml
from jira import JIRA, JIRAError

class JiraClient:
    """
    A client to handle all interactions with the Jira API.
    """

    def __init__(self, config):
        self.config = config["jira"]
        self._client = self._connect()

    def _connect(self):
        """
        Connects to Jira using the credentials from the config.
        """
        server = self.config["server"]
        jira_email = os.getenv("JIRA_EMAIL") or self.config.get("user")
        api_token = os.getenv("JIRA_API_TOKEN") or self.config.get("api_token")

        logging.info(f"Attempting to connect to Jira server: {server}")

        if not jira_email:
            raise ConnectionError("Jira email not found.")

        if not api_token:
            logging.info("API token not found, attempting to retrieve from keyring...")
            try:
                import keyring
                api_token = keyring.get_password("StandupBot", jira_email)
                if not api_token:
                    raise ConnectionError(f"API token not found in keyring for user {jira_email}.")
                logging.info("API token retrieved from keyring.")
            except (ImportError, Exception) as e:
                raise ConnectionError(f"Could not retrieve API token from keyring: {e}")

        logging.info(f"Attempting Jira authentication for user: {jira_email}...")
        try:
            jira_options = {"server": server}
            jira = JIRA(options=jira_options, basic_auth=(jira_email, api_token))
            if not jira.myself():
                raise ConnectionError("Could not connect to Jira.")
            logging.info(f"Successfully connected to Jira at {server}")
            return jira
        except Exception as e:
            logging.error(f"Error connecting to Jira: {e}")
            raise

    def get_active_sprint(self, board_id):
        logging.info(f"Fetching active sprint for board ID: {board_id}...")
        try:
            sprints = self._client.sprints(board_id, state="active")
            if not sprints:
                logging.warning(f"No active sprint found for board ID '{board_id}'.")
                return None
            logging.info(f"Active sprint found: {sprints[0].name}")
            return sprints[0]
        except JIRAError as e:
            logging.error(f"Error fetching active sprint for board ID {board_id}: {e.text}")
            return None

    def get_last_closed_sprint(self, board_id):
        logging.info(f"Fetching last closed sprint for board ID: {board_id}...")
        try:
            closed_sprints = self._client.sprints(board_id, state="closed")
            if not closed_sprints:
                logging.warning(f"No closed sprints found for board ID '{board_id}'.")
                return None
            closed_sprints.sort(key=lambda s: s.endDate, reverse=True)
            last_closed_sprint = closed_sprints[0]
            logging.info(f"Last closed sprint found: {last_closed_sprint.name} (Ended: {last_closed_sprint.endDate})")
            return last_closed_sprint
        except JIRAError as e:
            logging.error(f"Error fetching closed sprints for board ID {board_id}: {e.text}")
            return None

    def get_sprint_issues(self, sprint_id):
        logging.info(f"Fetching issues for sprint ID: {sprint_id}...")
        return self.search_issues(f"sprint = {sprint_id}")

    def search_issues(self, jql, expand=None):
        logging.info(f"Executing JQL query: {jql}")
        # Ensure fixVersions and reporter are always expanded
        if expand:
            expand += ",fixVersions,reporter"
        else:
            expand = "fixVersions,reporter"

        # Get epic link field from config
        epic_link_field = self.config.get("epic_link_field")

        # Add epic link field to expand parameter if it exists
        if epic_link_field:
            expand += f",{epic_link_field}"

        try:
            issues = self._client.search_issues(jql, maxResults=False, expand=expand)
            logging.info(f"Found {len(issues)} issues for JQL: {jql}")
            return issues
        except Exception as e:
            logging.error(f"Error running JQL query '{jql}': {e}")
            return []

    def get_issues_not_in_sprint(self, project_key, sprint_id):
        logging.info(f"Fetching issues not in sprint for project {project_key} and sprint {sprint_id}...")
        jql = f"project = '{project_key}' AND status = 'In Progress' AND sprint != {sprint_id}"
        return self.search_issues(jql)

    def get_issue_changelog(self, issue_key):
        logging.info(f"Fetching changelog for issue: {issue_key}...")
        try:
            issue = self._client.issue(issue_key, expand="changelog")
            logging.info(f"Changelog fetched for issue: {issue_key}")
            return issue.changelog
        except JIRAError as e:
            logging.error(f"Error fetching changelog for issue {issue_key}: {e.text}")
            return None

    def get_all_fields(self):
        logging.info("Fetching all Jira fields...")
        try:
            fields = self._client.fields()
            logging.info(f"Found {len(fields)} Jira fields.")
            return fields
        except JIRAError as e:
            logging.error(f"Error fetching fields from Jira: {e.text}")
            return []

    def load_jira_fields(self):
        jira_fields_path = Path(__file__).parent.parent / "jira_fields.yml"
        jira_fields = {}
        if jira_fields_path.exists() and jira_fields_path.stat().st_size > 0:
            with open(jira_fields_path, "r") as f:
                jira_fields = yaml.safe_load(f) or {}

        reload_fields = self.config.get("reload_fields_from_file", False)
        if reload_fields or not jira_fields:
            logging.info("Reloading Jira fields from API...")
            try:
                fetched_fields = self.get_all_fields()
                jira_fields = {field["id"]: field["name"] for field in fetched_fields}
                with open(jira_fields_path, "w") as f:
                    yaml.dump(jira_fields, f, default_flow_style=False, sort_keys=True)
                logging.info(f"Successfully reloaded {len(jira_fields)} Jira fields.")
            except Exception as e:
                logging.error(f"Error reloading Jira fields from API: {e}. Using cached fields if available.")
                if not jira_fields:
                    logging.error("No cached Jira fields available. Exiting.")
                    exit(1)
        else:
            logging.info("Using cached Jira fields from jira_fields.yml.")
        return jira_fields
