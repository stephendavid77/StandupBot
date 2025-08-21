import logging
from datetime import datetime, timezone
from collections import defaultdict

class SprintAnalyzer:
    """
    Analyzes sprint health and hygiene based on data from Jira.
    """

    def __init__(self, jira_client, config, include_epics=False):
        self.jira_client = jira_client
        self.config = config
        self.include_epics = include_epics

    def analyze(self, project_config, sprint):
        """
        Performs a full analysis for a given project configuration and sprint.
        """
        project_key = project_config["project_key"]
        logging.info(f"Analyzing project: {project_key} (Sprint: {sprint.name})")

        logging.info(f"Fetching issues for sprint: {sprint.name}...")
        issues = self.jira_client.get_sprint_issues(sprint.id)
        if not issues:
            logging.warning(f"No issues found in sprint {sprint.name} for project {project_key}. Skipping analysis.")
            return None
        logging.info(f"Found {len(issues)} issues for sprint: {sprint.name}.")

        guidelines = project_config.get("guidelines", self.config.get("guidelines", {}))

        cancelled_statuses = guidelines.get("cancelled_statuses", [])
        if cancelled_statuses:
            initial_issue_count = len(issues)
            issues = [issue for issue in issues if issue.fields.status.name not in cancelled_statuses]
            logging.info(f"Filtered out {initial_issue_count - len(issues)} cancelled issues. Remaining issues: {len(issues)}.")

        logging.info("Calculating metrics...")
        metrics = self._calculate_metrics(issues)
        logging.info("Checking sprint hygiene...")
        hygiene = self._check_sprint_hygiene(issues, guidelines)
        fix_version_hygiene = self._check_fix_version_hygiene(issues, guidelines)
        hygiene.update(fix_version_hygiene)
        logging.info("Identifying risks...")
        risks = self._identify_risks(issues, guidelines)
        logging.info("Analyzing workload...")
        workload = self._analyze_workload(issues)

        epics = {}
        if self.include_epics:
            logging.info("Extracting epic information...")
            epics = self._extract_epics(issues)

        analysis_results = {
            "sprint_info": {"name": sprint.name, "start_date": sprint.startDate, "end_date": sprint.endDate, "goal": sprint.goal},
            "metrics": metrics,
            "hygiene": hygiene,
            "risks": risks,
            "workload": workload,
            "epics": epics,
            "all_issues": issues,
        }
        logging.info(f"Analysis complete for project: {project_key}.")
        return analysis_results

    def _calculate_metrics(self, issues):
        total_issues = len(issues)
        status_counts = {"To Do": 0, "In Progress": 0, "Done": 0}
        total_story_points = 0
        story_points_done = 0
        story_points_field_id = self.config.get("jira", {}).get("story_points_field", "customfield_10016")

        for issue in issues:
            status = issue.fields.status.name
            if status in status_counts:
                status_counts[status] += 1

            story_points = getattr(issue.fields, story_points_field_id, 0) or 0
            total_story_points += story_points
            if status == "Done":
                story_points_done += story_points

        return {
            "total_issues": total_issues,
            "status_counts": status_counts,
            "total_story_points": total_story_points,
            "story_points_done": story_points_done,
            "progress_pct": (status_counts["Done"] / total_issues * 100) if total_issues > 0 else 0,
        }

    def _check_sprint_hygiene(self, issues, guidelines):
        unassigned_issues = [i.key for i in issues if not i.fields.assignee]
        unestimated_issues = [i.key for i in issues if i.fields.issuetype.name != "Bug" and not getattr(i.fields, self.config.get("jira", {}).get("story_points_field", "customfield_10016"), None)]
        unassigned_pct = len(unassigned_issues) / len(issues) * 100 if issues else 0
        unestimated_pct = len(unestimated_issues) / len(issues) * 100 if issues else 0

        return {
            "unassigned_issues": {"keys": unassigned_issues, "count": len(unassigned_issues), "percentage": unassigned_pct, "is_issue": unassigned_pct > guidelines.get("max_unassigned_pct", 10)},
            "unestimated_issues": {"keys": unestimated_issues, "count": len(unestimated_issues), "percentage": unestimated_pct, "is_issue": unestimated_pct > guidelines.get("max_unestimated_pct", 10)},
        }

    def _check_fix_version_hygiene(self, issues, guidelines):
        issues_without_fix_versions = [i.key for i in issues if i.fields.issuetype.name.lower() != "bug" and not i.fields.fixVersions]
        total_non_bug_issues = len([i for i in issues if i.fields.issuetype.name.lower() != "bug"])
        fix_version_hygiene_pct = (len(issues_without_fix_versions) / total_non_bug_issues * 100) if total_non_bug_issues > 0 else 0

        return {
            "issues_without_fix_versions": {"keys": issues_without_fix_versions, "count": len(issues_without_fix_versions), "percentage": fix_version_hygiene_pct, "is_issue": fix_version_hygiene_pct > guidelines.get("max_issues_without_fix_versions_pct", 0)}
        }

    def _identify_risks(self, issues, guidelines):
        now = datetime.now(timezone.utc)
        overdue_issues = []
        stale_issues = []
        blocker_issues = []
        stale_issue_days = guidelines.get("stale_issue_days", 7)
        blocker_labels = guidelines.get("blocker_labels", ["blocker", "impediment"])

        for issue in issues:
            if issue.fields.duedate:
                try:
                    duedate = datetime.strptime(issue.fields.duedate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if duedate < now and issue.fields.status.name != "Done":
                        overdue_issues.append(issue.key)
                except (TypeError, ValueError):
                    pass

            updated_date = datetime.strptime(issue.fields.updated, "%Y-%m-%dT%H:%M:%S.%f%z")
            if (now - updated_date).days > stale_issue_days:
                stale_issues.append(f"{issue.key} (Last updated: {updated_date.strftime('%Y-%m-%d')})")

            if issue.fields.labels:
                for label in issue.fields.labels:
                    if label.lower() in [b.lower() for b in blocker_labels]:
                        blocker_issues.append(issue.key)
                        break

        return {
            "overdue_issues": {"keys": overdue_issues, "count": len(overdue_issues)},
            "stale_issues": {"keys": stale_issues, "count": len(stale_issues)},
            "blocker_issues": {"keys": list(dict.fromkeys(blocker_issues)), "count": len(list(dict.fromkeys(blocker_issues)))},
        }

    def _analyze_workload(self, issues):
        workload = defaultdict(lambda: {"total_points": 0})
        story_points_field_id = self.config.get("jira", {}).get("story_points_field", "customfield_10016")

        for issue in issues:
            if not issue.fields.assignee:
                continue
            assignee = issue.fields.assignee.displayName
            story_points = getattr(issue.fields, story_points_field_id, 0) or 0
            workload[assignee]["total_points"] += story_points

        sorted_workload = sorted(workload.items(), key=lambda item: item[1]["total_points"], reverse=True)
        return dict(sorted_workload)

    def _extract_epics(self, issues):
        epics = {}
        jira_browse_url = self.config.get("jira", {}).get("jira_browse_url")
        epic_link_field_id = self.config.get("jira", {}).get("epic_link_field")

        if not epic_link_field_id:
            logging.warning("'epic_link_field' not configured. Cannot extract epic information.")
            return {}

        for issue in issues:
            epic_key = getattr(issue.fields, epic_link_field_id, None)
            if epic_key:
                try:
                    epic_issue = self.jira_client._client.issue(epic_key)
                    epic_summary = epic_issue.fields.summary
                    epics[epic_key] = {"summary": epic_summary, "url": f"{jira_browse_url}{epic_key}"}
                except Exception as e:
                    logging.warning(f"Could not fetch epic details for {epic_key}: {e}")
        return epics
