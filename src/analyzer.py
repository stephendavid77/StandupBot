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
        print(f"\nAnalyzing project: {project_key} (Sprint: {sprint.name})")

        print(f"Fetching issues for sprint: {sprint.name}...")
        issues = self.jira_client.get_sprint_issues(sprint.id)
        if not issues:
            print(
                f"No issues found in sprint {sprint.name} for project {project_key}. Skipping analysis."
            )
            return None
        print(f"Found {len(issues)} issues for sprint: {sprint.name}.")

        guidelines = project_config.get("guidelines", self.config.get("guidelines", {}))

        # Filter out cancelled issues
        cancelled_statuses = guidelines.get("cancelled_statuses", [])
        if cancelled_statuses:
            initial_issue_count = len(issues)
            issues = [
                issue
                for issue in issues
                if issue.fields.status.name not in cancelled_statuses
            ]
            print(
                f"Filtered out {initial_issue_count - len(issues)} cancelled issues. Remaining issues: {len(issues)}."
            )

        print("Calculating metrics...")
        metrics = self._calculate_metrics(issues)
        print("Checking sprint hygiene...")
        hygiene = self._check_sprint_hygiene(issues, guidelines)
        fix_version_hygiene = self._check_fix_version_hygiene(issues, guidelines)
        hygiene.update(fix_version_hygiene)
        print("Identifying risks...")
        risks = self._identify_risks(issues, guidelines)
        print("Analyzing workload...")
        workload = self._analyze_workload(issues)

        epics = {}  # Initialize epics to an empty dict
        if self.include_epics:
            print("Extracting epic information...")
            epics = self._extract_epics(issues)

        print("Analyzing detailed workload...")
        detailed_workload = self._analyze_detailed_workload(issues)

        # New analyses for previous sprint report
        print("Analyzing issues completed after sprint end...")
        issues_completed_after_sprint_end = (
            self._analyze_issues_completed_after_sprint_end(
                issues, datetime.strptime(sprint.endDate.split("T")[0], "%Y-%m-%d")
            )
        )

        print("Analyzing issues removed from sprint...")
        issues_removed_from_sprint = self._analyze_issues_removed_from_sprint(
            sprint.id, project_key, issues
        )

        analysis_results = {
            "sprint_info": {
                "name": sprint.name,
                "start_date": sprint.startDate,
                "end_date": sprint.endDate,
                "goal": sprint.goal,
            },
            "metrics": metrics,
            "hygiene": hygiene,
            "risks": risks,
            "workload": workload,
            "epics": epics,
            "detailed_workload": detailed_workload,
            "issues_completed_after_sprint_end": issues_completed_after_sprint_end,
            "issues_removed_from_sprint": issues_removed_from_sprint,
            "all_issues": issues,
        }
        print(f"Analysis complete for project: {project_key}.")
        return analysis_results

    def _analyze_detailed_workload(self, issues):
        detailed_workload = defaultdict(list)
        story_points_field = self.config.get("jira", {}).get(
            "story_points_field", "customfield_10016"
        )
        jira_browse_url = self.config.get("jira", {}).get("jira_browse_url")
        now = datetime.now(timezone.utc)

        for issue in issues:
            if not issue.fields.assignee:
                continue

            assignee_name = issue.fields.assignee.displayName
            issue_key = issue.key
            issue_type = issue.fields.issuetype.name
            story_points = getattr(issue.fields, story_points_field, 0) or 0
            current_status = issue.fields.status.name

            # For "days assigned", using issue creation date as a proxy.
            # Getting exact "days assigned to current assignee" requires fetching changelog for each issue,
            # which can be very slow and API-intensive.
            created_date = datetime.strptime(
                issue.fields.created, "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            days_assigned = (now - created_date).days

            detailed_workload[assignee_name].append(
                {
                    "issue_key": issue_key,
                    "issue_link": f"{jira_browse_url}{issue_key}",
                    "issue_type": issue_type,
                    "story_points": story_points,
                    "current_status": current_status,
                    "days_assigned": days_assigned,
                }
            )
        return dict(detailed_workload)

    def _analyze_issues_completed_after_sprint_end(self, issues, sprint_end_date):
        completed_after_sprint = []
        for issue in issues:
            if issue.fields.resolutiondate:
                resolution_date = datetime.strptime(
                    issue.fields.resolutiondate.split("T")[0], "%Y-%m-%d"
                ).date()
                if resolution_date > sprint_end_date.date():
                    completed_after_sprint.append(issue.key)
        return completed_after_sprint

    def _analyze_issues_removed_from_sprint(
        self, sprint_id, project_key, issues_in_sprint
    ):
        removed_issues = []
        # Fetch all issues that were ever in this sprint
        # This JQL might not be perfect, as Jira's sprint field history is complex
        jql = f'project = "{project_key}" AND sprint = {sprint_id}'
        all_sprint_issues = self.jira_client.search_issues(jql)

        current_sprint_issue_keys = {issue.key for issue in issues_in_sprint}

        for issue in all_sprint_issues:
            # If an issue was in the sprint but is no longer in the current list
            # and is not resolved, consider it removed.
            if (
                issue.key not in current_sprint_issue_keys
                and issue.fields.status.statusCategory.name != "Done"
            ):
                removed_issues.append(issue.key)
        return removed_issues

    def _extract_epics(self, issues):
        epics = {}
        jira_browse_url = self.config.get("jira", {}).get("jira_browse_url")
        field_mappings = self.config.get("jira", {}).get("field_mappings", {})

        # Prioritize epic_link_field from config.yaml, then from jira_fields.yml (via field_mappings)
        epic_link_field_id = self.config.get("jira", {}).get("epic_link_field")
        if not epic_link_field_id:
            # Try to find 'Epic Link' or 'Epic Name' from the reloaded fields
            for field_id, field_name in field_mappings.items():
                if field_name == "Epic Link":
                    epic_link_field_id = field_id
                    break
                elif field_name == "Epic Name":  # Fallback if 'Epic Link' is not found
                    epic_link_field_id = field_id
                    print(
                        "Warning: Using 'Epic Name' field as 'Epic Link' was not found. This might not be the correct field for linking epics."
                    )
                    break

        if not epic_link_field_id:
            print(
                "Warning: 'epic_link_field' not configured in config.yaml and could not be determined from Jira fields. Cannot extract epic information."
            )
            return {}

        for issue in issues:
            epic_key = getattr(issue.fields, epic_link_field_id, None)
            if epic_key:
                try:
                    epic_issue = self.jira_client._client.issue(epic_key)
                    epic_summary = epic_issue.fields.summary
                    epics[epic_key] = {
                        "summary": epic_summary,
                        "url": f"{jira_browse_url}{epic_key}",
                    }
                except Exception as e:
                    print(f"Warning: Could not fetch epic details for {epic_key}: {e}")
        return epics

    def _calculate_metrics(self, issues):
        """
        Calculates key sprint metrics.
        """
        total_issues = len(issues)
        status_counts = {"To Do": 0, "In Progress": 0, "Done": 0}
        total_story_points = 0
        story_points_done = 0
        field_mappings = self.config.get("jira", {}).get("field_mappings", {})
        story_points_field_id = self.config.get("jira", {}).get("story_points_field")
        if not story_points_field_id:
            for field_id, field_name in field_mappings.items():
                if field_name == "Story point estimate" or field_name == "Story Points":
                    story_points_field_id = field_id
                    break
            if not story_points_field_id:
                print(
                    "Warning: 'story_points_field' not configured in config.yaml and could not be determined from Jira fields. Story points will not be calculated."
                )
                story_points_field_id = (
                    "customfield_10016"  # Fallback to a common default
                )

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
            "progress_pct": (status_counts["Done"] / total_issues * 100)
            if total_issues > 0
            else 0,
        }

    def _check_sprint_hygiene(self, issues, guidelines):
        """
        Checks for common sprint hygiene issues.
        """
        unassigned_issues = [i.key for i in issues if not i.fields.assignee]
        unestimated_issues = [
            i.key
            for i in issues
            if i.fields.issuetype.name != "Bug"
            and not getattr(
                i.fields,
                self.config.get("jira", {}).get(
                    "story_points_field", "customfield_10016"
                ),
                None,
            )
        ]

        unassigned_pct = len(unassigned_issues) / len(issues) * 100 if issues else 0
        unestimated_pct = len(unestimated_issues) / len(issues) * 100 if issues else 0

        return {
            "unassigned_issues": {
                "keys": unassigned_issues,
                "count": len(unassigned_issues),
                "percentage": unassigned_pct,
                "is_issue": unassigned_pct > guidelines.get("max_unassigned_pct", 10),
            },
            "unestimated_issues": {
                "keys": unestimated_issues,
                "count": len(unestimated_issues),
                "percentage": unestimated_pct,
                "is_issue": unestimated_pct > guidelines.get("max_unestimated_pct", 10),
            },
        }

    def _check_fix_version_hygiene(self, issues, guidelines):
        """
        Checks for issues without fix versions (excluding bugs).
        """
        issues_without_fix_versions = []
        for issue in issues:
            issue_type = issue.fields.issuetype.name
            fix_versions = issue.fields.fixVersions
            if issue_type.lower() != "bug" and (
                not fix_versions or len(fix_versions) == 0
            ):
                issues_without_fix_versions.append(issue.key)

        total_non_bug_issues = len(
            [i for i in issues if i.fields.issuetype.name.lower() != "bug"]
        )
        fix_version_hygiene_pct = (
            len(issues_without_fix_versions) / total_non_bug_issues * 100
            if total_non_bug_issues > 0
            else 0
        )

        return {
            "issues_without_fix_versions": {
                "keys": issues_without_fix_versions,
                "count": len(issues_without_fix_versions),
                "percentage": fix_version_hygiene_pct,
                "is_issue": fix_version_hygiene_pct
                > guidelines.get("max_issues_without_fix_versions_pct", 0),
            }
        }

    def _identify_risks(self, issues, guidelines):
        """
        Identifies potential risks in the sprint.
        """
        now = datetime.now(timezone.utc)
        overdue_issues = []
        stale_issues = []
        blocker_issues = []

        stale_issue_days = guidelines.get("stale_issue_days", 7)
        blocker_labels = guidelines.get("blocker_labels", ["blocker", "impediment"])

        for issue in issues:
            if issue.fields.duedate:
                try:
                    duedate = datetime.strptime(
                        issue.fields.duedate, "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                    if duedate < now and issue.fields.status.name != "Done":
                        overdue_issues.append(issue.key)
                except (TypeError, ValueError):
                    pass  # Ignore invalid date formats

            updated_date = datetime.strptime(
                issue.fields.updated, "%Y-%m-%dT%H:%M:%S.%f%z"
            )
            if (now - updated_date).days > stale_issue_days:
                stale_issues.append(
                    f"{issue.key} (Last updated: {updated_date.strftime('%Y-%m-%d')})"
                )

            if issue.fields.labels:
                for label in issue.fields.labels:
                    if label.lower() in [b.lower() for b in blocker_labels]:
                        blocker_issues.append(issue.key)
                        break

        return {
            "overdue_issues": {"keys": overdue_issues, "count": len(overdue_issues)},
            "stale_issues": {"keys": stale_issues, "count": len(stale_issues)},
            "blocker_issues": {
                "keys": list(set(blocker_issues)),
                "count": len(set(blocker_issues)),
            },
        }

    def _analyze_workload(self, issues):
        """
        Analyzes the distribution of story points across the team.
        """
        workload = defaultdict(lambda: {"total_points": 0})
        field_mappings = self.config.get("jira", {}).get("field_mappings", {})
        story_points_field_id = self.config.get("jira", {}).get("story_points_field")
        if not story_points_field_id:
            for field_id, field_name in field_mappings.items():
                if field_name == "Story point estimate" or field_name == "Story Points":
                    story_points_field_id = field_id
                    break
            if not story_points_field_id:
                print(
                    "Warning: 'story_points_field' not configured in config.yaml and could not be determined from Jira fields. Story points will not be calculated for workload analysis."
                )
                story_points_field_id = (
                    "customfield_10016"  # Fallback to a common default
                )

        for issue in issues:
            if not issue.fields.assignee:
                continue

            assignee = issue.fields.assignee.displayName
            story_points = getattr(issue.fields, story_points_field_id, 0) or 0

            workload[assignee]["total_points"] += story_points

        # Sort by total points descending
        sorted_workload = sorted(
            workload.items(), key=lambda item: item[1]["total_points"], reverse=True
        )
        return dict(sorted_workload)
