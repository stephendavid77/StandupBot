import importlib
import os  # Added import os
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

        # 1. Try to get credentials from environment variables
        jira_email = os.getenv("JIRA_EMAIL")
        api_token = os.getenv("JIRA_API_TOKEN")

        # 2. If not found in environment variables, try config.yaml
        if not jira_email:
            jira_email = self.config.get("jira_email")
        if not api_token:
            api_token = self.config.get("api_token")

        print(f"Attempting to connect to Jira server: {server}")

        if not jira_email:
            raise ConnectionError(
                "Jira email not found in environment variables or config.yaml. Please set JIRA_EMAIL environment variable or 'jira_email' in config.yaml."
            )

        if not api_token:
            print(
                "API token not found in environment variables or config.yaml. Attempting to retrieve from keyring..."
            )
            try:
                import keyring

                # Try to use a non-interactive backend to prevent popups
                # Ordered by preference: secure encrypted file, then plaintext file, then null (no storage)
                non_interactive_backends = [
                    "keyrings.alt.file.EncryptedKeyring",
                    "keyrings.alt.file.PlaintextKeyring",
                    "keyrings.backends.null.Keyring",
                ]

                backend_set = False
                for backend_path in non_interactive_backends:
                    print(f"Attempting to use keyring backend: {backend_path}")
                    try:
                        os.environ["KEYRING_BACKEND"] = backend_path
                        importlib.reload(keyring)
                        current_keyring = keyring.get_keyring()
                        current_keyring_path = (
                            current_keyring.__class__.__module__
                            + "."
                            + current_keyring.__class__.__name__
                        )
                        print(f"Keyring reports using: {current_keyring_path}")

                        # Test if the backend is usable by attempting a dummy operation
                        try:
                            current_keyring.get_password("dummy_service", "dummy_user")
                            print(f"Successfully tested backend: {backend_path}")
                            backend_set = True
                            break
                        except keyring.errors.NoKeyringError:
                            print(
                                f"Backend {backend_path} is not available or not configured."
                            )
                            continue
                        except Exception as test_e:
                            print(f"Error testing backend {backend_path}: {test_e}")
                            continue

                    except Exception as e:
                        print(
                            f"Could not set or use keyring backend {backend_path}: {e}"
                        )
                        continue

                if not backend_set:
                    raise ConnectionError(
                        "Could not find a suitable non-interactive keyring backend. Please ensure 'keyrings.alt' and 'cryptography' are installed (`pip install keyrings.alt cryptography`) or provide 'api_token' in config.yaml."
                    )

                api_token = keyring.get_password("StandupBot", jira_email)
                if not api_token:
                    raise ConnectionError(
                        f'API token not found in keyring for user {jira_email}. Please set it using \'keyring.set_password("StandupBot", "{jira_email}", "YOUR_JIRA_PAT")\')'
                    )
                print("API token retrieved from keyring.")
            except ImportError:
                raise ConnectionError(
                    "Keyring library not found. Please install it (`pip install keyring`) or provide 'api_token' in config.yaml."
                )
            except Exception as e:
                raise ConnectionError(f"Error retrieving API token from keyring: {e}")

        print(
            f"API Token found. Attempting Jira authentication for user: {jira_email}..."
        )

        try:
            jira_options = {"server": server}
            jira = JIRA(options=jira_options, basic_auth=(jira_email, api_token))
            if not jira.myself():
                raise ConnectionError(
                    "Could not connect to Jira. Please check your email, API token, and server URL."
                )
            print(f"Successfully connected to Jira at {server}")
            return jira
        except Exception as e:
            print(f"Error connecting to Jira: {e}")
            raise

    def get_active_sprint(self, board_id):
        print(f"Fetching active sprint for board ID: {board_id}...")
        try:
            sprints = self._client.sprints(board_id, state="active")
            if not sprints:
                print(f"Warning: No active sprint found for board ID '{board_id}'.")
                return None
            print(f"Active sprint found: {sprints[0].name}")
            return sprints[0]
        except JIRAError as e:
            if e.status_code == 404:
                print(f"Warning: Board with ID '{board_id}' not found.")
                return None
            print(f"Error fetching active sprint for board ID {board_id}: {e.text}")
            return None

    def get_last_closed_sprint(self, board_id):
        print(f"Fetching last closed sprint for board ID: {board_id}...")
        try:
            # Fetch all closed sprints for the board
            closed_sprints = self._client.sprints(board_id, state="closed")
            if not closed_sprints:
                print(f"Warning: No closed sprints found for board ID '{board_id}'.")
                return None

            # Sort sprints by end date in descending order to get the most recent one
            # Jira API returns sprints sorted by ID by default, which might not be chronological
            closed_sprints.sort(key=lambda s: s.endDate, reverse=True)

            last_closed_sprint = closed_sprints[0]
            print(
                f"Last closed sprint found: {last_closed_sprint.name} (Ended: {last_closed_sprint.endDate})"
            )
            return last_closed_sprint
        except JIRAError as e:
            if e.status_code == 404:
                print(f"Warning: Board with ID '{board_id}' not found.")
                return None
            print(f"Error fetching closed sprints for board ID {board_id}: {e.text}")
            return None

    def get_future_sprints(self, board_id):
        print(f"Fetching future sprints for board ID: {board_id}...")
        try:
            sprints = self._client.sprints(board_id, state="future")
            print(f"Found {len(sprints)} future sprints.")
            return sprints
        except JIRAError as e:
            if e.status_code == 404:
                print(f"Warning: Board with ID '{board_id}' not found.")
                return []
            print(f"Error fetching future sprints for board ID {board_id}: {e.text}")
            return []

    def get_sprint_issues(self, sprint_id):
        print(f"Fetching issues for sprint ID: {sprint_id}...\n")
        return self.search_issues(f"sprint = {sprint_id}")

    def search_issues(self, jql, expand=None):
        print(f"Executing JQL query: {jql}")

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
            print(f"Found {len(issues)} issues for JQL: {jql}")
            return issues
        except Exception as e:
            print(f"Error running JQL query '{jql}': {e}")
            return []

    def get_issues_not_in_sprint(self, project_key, sprint_id):
        print(
            f"Fetching issues not in sprint for project {project_key} and sprint {sprint_id}...\n"
        )
        jql = f"project = '{project_key}' AND status = 'In Progress' AND sprint != {sprint_id}"
        return self.search_issues(jql)

    def get_issue_changelog(self, issue_key):
        print(f"Fetching changelog for issue: {issue_key}...\n")
        try:
            issue = self._client.issue(issue_key, expand="changelog")
            print(f"Changelog fetched for issue: {issue_key}")
            return issue.changelog
        except JIRAError as e:
            print(f"Error fetching changelog for issue {issue_key}: {e.text}")
            return None

    def get_all_fields(self):
        print("Fetching all Jira fields...\n")
        try:
            fields = self._client.fields()
            print(f"Found {len(fields)} Jira fields.")
            return fields
        except JIRAError as e:
            print(f"Error fetching fields from Jira: {e.text}")
            return []
