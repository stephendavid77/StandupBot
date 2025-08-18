import keyring
from jira import JIRA, JIRAError

class JiraClient:
    """
    A client to handle all interactions with the Jira API.
    """
    def __init__(self, config):
        self.config = config['jira']
        self._client = self._connect()

    def _connect(self):
        """
        Connects to Jira using the credentials from the config.
        """
        server = self.config['server']
        user = self.config['user']
        
        pat = keyring.get_password('StandupBot', user)
        
        if not pat:
            pat = self.config.get('pat')

        if not pat:
            raise ConnectionError("Jira PAT not found in keyring or config.yaml. Please run the setup command.")

        try:
            jira_options = {'server': server}
            jira = JIRA(options=jira_options, basic_auth=(user, pat))
            if not jira.myself():
                 raise ConnectionError("Could not connect to Jira. Please check your credentials and server URL.")
            print(f"Successfully connected to Jira at {server}")
            return jira
        except Exception as e:
            print(f"Error connecting to Jira: {e}")
            raise

    def get_active_sprint(self, board_id):
        """
        Fetches the active sprint for a given board ID.
        """
        try:
            sprints = self._client.sprints(board_id, state='active')
            if not sprints:
                print(f"Warning: No active sprint found for board ID '{board_id}'.")
                return None
            return sprints[0]
        except JIRAError as e:
            if e.status_code == 404:
                print(f"Warning: Board with ID '{board_id}' not found.")
                return None
            print(f"Error fetching active sprint for board ID {board_id}: {e.text}")
            return None

    def get_future_sprints(self, board_id):
        """
        Fetches all future sprints for a given board ID.
        """
        try:
            sprints = self._client.sprints(board_id, state='future')
            return sprints
        except JIRAError as e:
            if e.status_code == 404:
                print(f"Warning: Board with ID '{board_id}' not found.")
                return []
            print(f"Error fetching future sprints for board ID {board_id}: {e.text}")
            return []

    def get_sprint_issues(self, sprint_id):
        """
        Fetches all issues for a given sprint ID.
        """
        return self.search_issues(f'sprint = {sprint_id}')

    def search_issues(self, jql, expand=None):
        """
        Runs a JQL query and returns the issues.
        """
        try:
            issues = self._client.search_issues(jql, maxResults=False, expand=expand)
            return issues
        except Exception as e:
            print(f"Error running JQL query '{jql}': {e}")
            return []

    def get_issues_not_in_sprint(self, project_key, sprint_id):
        """
        Fetches issues that are in progress but not in the active sprint.
        """
        jql = f"project = '{project_key}' AND status = 'In Progress' AND sprint != {sprint_id}"
        return self.search_issues(jql)

    def get_issue_changelog(self, issue_key):
        """
        Fetches the changelog for a specific issue.
        """
        try:
            issue = self._client.issue(issue_key, expand='changelog')
            return issue.changelog
        except JIRAError as e:
            print(f"Error fetching changelog for issue {issue_key}: {e.text}")
            return None

    def get_all_fields(self):
        """
        Retrieves all fields from Jira.
        """
        try:
            fields = self._client.fields()
            return fields
        except JIRAError as e:
            print(f"Error fetching fields from Jira: {e.text}")
            return []
