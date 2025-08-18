from datetime import datetime, timezone
from collections import defaultdict

class SprintAnalyzer:
    """
    Analyzes sprint health and hygiene based on data from Jira.
    """
    def __init__(self, jira_client, config):
        self.jira_client = jira_client
        self.config = config

    def analyze(self, project_config):
        """
        Performs a full analysis for a given project configuration.
        """
        board_id = project_config['board_id']
        print(f"\nAnalyzing project: {project_config['project_key']} (Board ID: {board_id})")

        sprint = self.jira_client.get_active_sprint(board_id)
        if not sprint:
            return None

        issues = self.jira_client.get_sprint_issues(sprint.id)
        if not issues:
            print("No issues found in the active sprint.")
            return None

        guidelines = project_config.get('guidelines', self.config.get('guidelines', {}))

        analysis_results = {
            "sprint_info": {
                "name": sprint.name,
                "start_date": sprint.startDate,
                "end_date": sprint.endDate,
                "goal": sprint.goal,
            },
            "metrics": self._calculate_metrics(issues),
            "hygiene": self._check_sprint_hygiene(issues, guidelines),
            "risks": self._identify_risks(issues, guidelines),
            "workload": self._analyze_workload(issues)
        }
        return analysis_results

    def _calculate_metrics(self, issues):
        """
        Calculates key sprint metrics.
        """
        total_issues = len(issues)
        status_counts = {'To Do': 0, 'In Progress': 0, 'Done': 0}
        total_story_points = 0
        story_points_done = 0

        for issue in issues:
            status = issue.fields.status.name
            if status in status_counts:
                status_counts[status] += 1
            
            story_points = getattr(issue.fields, self.config.get('jira', {}).get('story_points_field', 'customfield_10016'), 0) or 0
            total_story_points += story_points
            if status == 'Done':
                story_points_done += story_points

        return {
            "total_issues": total_issues,
            "status_counts": status_counts,
            "total_story_points": total_story_points,
            "story_points_done": story_points_done,
            "progress_pct": (status_counts['Done'] / total_issues * 100) if total_issues > 0 else 0,
        }

    def _check_sprint_hygiene(self, issues, guidelines):
        """
        Checks for common sprint hygiene issues.
        """
        unassigned_issues = [i.key for i in issues if not i.fields.assignee]
        unestimated_issues = [i.key for i in issues if not getattr(i.fields, self.config.get('jira', {}).get('story_points_field', 'customfield_10016'), None)]

        unassigned_pct = len(unassigned_issues) / len(issues) * 100 if issues else 0
        unestimated_pct = len(unestimated_issues) / len(issues) * 100 if issues else 0

        return {
            "unassigned_issues": {
                "keys": unassigned_issues,
                "count": len(unassigned_issues),
                "percentage": unassigned_pct,
                "is_issue": unassigned_pct > guidelines.get('max_unassigned_pct', 10)
            },
            "unestimated_issues": {
                "keys": unestimated_issues,
                "count": len(unestimated_issues),
                "percentage": unestimated_pct,
                "is_issue": unestimated_pct > guidelines.get('max_unestimated_pct', 10)
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
        
        stale_issue_days = guidelines.get('stale_issue_days', 7)
        blocker_labels = guidelines.get('blocker_labels', ['blocker', 'impediment'])

        for issue in issues:
            if issue.fields.duedate:
                try:
                    duedate = datetime.strptime(issue.fields.duedate, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    if duedate < now and issue.fields.status.name != 'Done':
                        overdue_issues.append(issue.key)
                except (TypeError, ValueError):
                    pass # Ignore invalid date formats

            updated_date = datetime.strptime(issue.fields.updated, '%Y-%m-%dT%H:%M:%S.%f%z')
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
            "blocker_issues": {"keys": list(set(blocker_issues)), "count": len(set(blocker_issues))}
        }

    def _analyze_workload(self, issues):
        """
        Analyzes the distribution of story points across the team.
        """
        workload = defaultdict(lambda: {'total_points': 0})
        story_points_field = self.config.get('jira', {}).get('story_points_field', 'customfield_10016')

        for issue in issues:
            if not issue.fields.assignee:
                continue

            assignee = issue.fields.assignee.displayName
            story_points = getattr(issue.fields, story_points_field, 0) or 0

            workload[assignee]['total_points'] += story_points
        
        # Sort by total points descending
        sorted_workload = sorted(workload.items(), key=lambda item: item[1]['total_points'], reverse=True)
        return dict(sorted_workload)