import os
import logging
from pathlib import Path
import subprocess
import sys
from datetime import datetime
import pytz
from src.reporter import Reporter

class PreviousSprintReporter(Reporter):
    def __init__(self, results, config, project_config):
        super().__init__(results, config, project_config)

    def generate_previous_sprint_report(self):
        logging.info("Generating previous sprint report...")
        if not self.results:
            logging.warning("No analysis results to report for previous sprint.")
            return "No analysis results to report."

        r = self.results
        sprint_info = r["sprint_info"]
        metrics = r["metrics"]
        hygiene = r["hygiene"]
        risks = r["risks"]
        workload = r["workload"]
        detailed_workload = r.get("detailed_workload", {})
        epics = r.get("epics", {})
        issues_completed_after_sprint_end = r.get("issues_completed_after_sprint_end", [])
        issues_removed_from_sprint = r.get("issues_removed_from_sprint", [])

        est_timezone = pytz.timezone("America/New_York")
        now_est = datetime.now(est_timezone)
        generated_date = now_est.strftime("%Y-%m-%d")
        generated_time = now_est.strftime("%H:%M:%S %Z%z")

        jira_board_link = self._get_jira_board_link()

        report = f"# Previous Sprint Report: {sprint_info['name']}\n\n"
        report += f"**Date Generated:** {generated_date}\n"
        report += f"**Time Generated (EST):** {generated_time}\n"
        report += f"**Jira Board Link:** [{jira_board_link}]({jira_board_link})\n\n"
        report += f"**Goal:** {sprint_info['goal'] if sprint_info['goal'] else 'Not set'}\n"
        report += f"**Duration:** {sprint_info['start_date']} to {sprint_info['end_date']}\n\n"

        include_epics = self.config.get("run_settings", {}).get("include_epics", False)
        if include_epics:
            if epics:
                report += "## Epics in this Sprint\n"
                report += "| Epic Key | Epic Summary |\n"
                report += "|----------|--------------|\n"
                for key, data in epics.items():
                    report += f"| [{key}]({data['url']}) | {data['summary']} |\n"
                report += "\n"

        report += "## Sprint Performance Summary\n"
        report += f"- **Total Issues:** {metrics['total_issues']}\n"
        report += f"- **Issues Done:** {metrics['status_counts']['Done']}\n"
        report += f"- **Completion Percentage:** {metrics['progress_pct']:.2f}%\n"
        report += f"- **Story Points Done:** {metrics['story_points_done']} / {metrics['total_story_points']} SP\n"
        report += f"- **Sprint Velocity (Story Points Completed):** {metrics['story_points_done']} SP\n\n"

        report += "## Sprint Hygiene Details\n"
        if not hygiene["unassigned_issues"]["is_issue"] and not hygiene["unestimated_issues"]["is_issue"]:
            report += "-  Sprint hygiene looks good!\n"
        else:
            if hygiene["unassigned_issues"]["is_issue"]:
                formatted_keys = ", ".join([self._format_issue_link(key) for key in hygiene["unassigned_issues"]["keys"]])
                report += f"- **Unassigned:** {hygiene['unassigned_issues']['count']} issues ({hygiene['unassigned_issues']['percentage']:.2f}%) were unassigned. Keys: {formatted_keys}\n"
            if hygiene["unestimated_issues"]["is_issue"]:
                formatted_keys = ", ".join([self._format_issue_link(key) for key in hygiene["unestimated_issues"]["keys"]])
                report += f"- **Unestimated:** {hygiene['unestimated_issues']['count']} issues ({hygiene['unestimated_issues']['percentage']:.2f}%) had no story points. Keys: {formatted_keys}\n"

        report += "\n## Risks Identified\n"
        has_risks = False
        if risks["blocker_issues"]["count"] > 0:
            formatted_keys = ", ".join([self._format_issue_link(key) for key in risks["blocker_issues"]["keys"]])
            report += f"- **🔥 Blockers:** {risks['blocker_issues']['count']} issue(s) - {formatted_keys}\n"
            has_risks = True
        if risks["overdue_issues"]["count"] > 0:
            formatted_keys = ", ".join([self._format_issue_link(key) for key in risks["overdue_issues"]["keys"]])
            report += f"- **⏰ Overdue:** {risks['overdue_issues']['count']} issue(s) - {formatted_keys}\n"
            has_risks = True
        if risks["stale_issues"]["count"] > 0:
            report += f"- **🗓️ Stale:** {risks['stale_issues']['count']} issue(s) were stale:\n"
            for key in risks["stale_issues"]["keys"]:
                report += f"  - {self._format_issue_link(key)}\n"
            has_risks = True

        if not has_risks:
            report += "-  No significant risks identified during the sprint.\n"

        report += "\n## Workload Summary\n"
        if not workload:
            report += "- No assigned issues with story points to analyze.\n"
        else:
            report += "| Assignee | Total Points |\n"
            report += "|----------|--------------|\n"
            for assignee, points in workload.items():
                report += f"| {assignee} | {points['total_points']} |\n"

        if detailed_workload:
            report += "\n## Detailed Workload Breakdown\n"
            for assignee, issues_list in detailed_workload.items():
                report += f"### {assignee}\n"
                report += "| Issue | Type | SP | Status | Days Assigned |\n"
                report += "|-------|------|----|--------|---------------|\n"
                for issue_data in issues_list:
                    report += f"| [{issue_data['issue_key']}]({issue_data['issue_link']}) | {issue_data['issue_type']} | {issue_data['story_points']} | {issue_data['current_status']} | {issue_data['days_assigned']} |\n"
                report += "\n"

        report += "\n## Issues Completed After Sprint End\n"
        if issues_completed_after_sprint_end:
            for issue_key in issues_completed_after_sprint_end:
                report += f"- {self._format_issue_link(issue_key)}\n"
        else:
            report += "- No issues completed after the sprint end date.\n"

        report += "\n## Issues Removed from Sprint\n"
        if issues_removed_from_sprint:
            for issue_key in issues_removed_from_sprint:
                report += f"- {self._format_issue_link(issue_key)}\n"
        else:
            report += "- No issues identified as removed from the sprint.\n"

        report += f"\n--- End of Previous Sprint Report for {sprint_info['name']} ---\n"
        logging.info("Previous sprint report generated.")
        return report
