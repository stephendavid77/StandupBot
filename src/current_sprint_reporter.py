import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import pytz
from reporter import Reporter  # Import the base Reporter class


class CurrentSprintReporter(Reporter):  # Inherit from Reporter
    """
    Generates reports for the current/active sprint from the analysis results.
    """

    def __init__(self, results, config, project_config):
        super().__init__(results, config, project_config)  # Call base class constructor

    def generate_daily_summary(self):
        """
        Generates a concise daily summary in Markdown format.
        """
        print("Generating daily summary...")
        if not self.results:
            print("No analysis results to report for daily summary.")
            return "No analysis results to report."

        r = self.results
        sprint_info = r["sprint_info"]
        metrics = r["metrics"]
        risks = r["risks"]

        # Get current time in EST
        est_timezone = pytz.timezone("America/New_York")
        now_est = datetime.now(est_timezone)
        generated_date = now_est.strftime("%Y-%m-%d")
        generated_time = now_est.strftime(
            "%H:%M:%S %Z%z"
        )  # %Z for timezone name, %z for UTC offset

        jira_board_link = self._get_jira_board_link()

        # Calculate days left in sprint
        sprint_end_datetime = datetime.strptime(
            sprint_info["end_date"], "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=timezone.utc)
        # Convert now_est to UTC for consistent comparison
        now_utc = now_est.astimezone(timezone.utc)
        days_left = (sprint_end_datetime - now_utc).days
        if days_left < 0:
            days_left = 0  # Sprint has ended

        report = f"# Daily Sprint Summary: {sprint_info['name']}\n\n"
        report += f"**Date Generated:** {generated_date}\n"
        report += f"**Time Generated (EST):** {generated_time}\n"
        report += f"**Days Left in Sprint:** {days_left} day(s)\n"
        report += f"**Jira Board Link:** [{jira_board_link}]({jira_board_link})\n\n"

        epics = self.results.get("epics", {})
        if epics:
            report += "## Epics in this Sprint\n"
            report += "| Epic Key | Epic Summary |\n"
            report += "|----------|--------------|\n"
            for key, data in epics.items():
                report += f"| [{key}]({data['url']}) | {data['summary']} |\n"
            report += "\n"

        if sprint_info["goal"]:
            report += f"**Goal:** {sprint_info['goal']}\n"
        start_date_only = datetime.strptime(
            sprint_info["start_date"].split("T")[0], "%Y-%m-%d"
        ).strftime("%Y-%m-%d")
        end_date_only = datetime.strptime(
            sprint_info["end_date"].split("T")[0], "%Y-%m-%d"
        ).strftime("%Y-%m-%d")
        report += f"**Duration:** {start_date_only} to {end_date_only}\n\n"

        report += "## Sprint Progress\n"
        report += f"- **{metrics['progress_pct']:.2f}% Complete** ({metrics['status_counts']['Done']} of {metrics['total_issues']} issues)\n"
        report += f"- **Story Points:** {metrics['story_points_done']} / {metrics['total_story_points']} SP done\n\n"

        report += "## Focus Items & Risks\n"

        has_risks = False
        if risks["blocker_issues"]["count"] > 0:
            formatted_keys = ", ".join(
                [
                    self._format_issue_link(key)
                    for key in risks["blocker_issues"]["keys"]
                ]
            )
            report += f"- **🔥 Blockers:** {risks['blocker_issues']['count']} issue(s) - {formatted_keys}\n"
            has_risks = True
        if risks["overdue_issues"]["count"] > 0:
            formatted_keys = ", ".join(
                [
                    self._format_issue_link(key)
                    for key in risks["overdue_issues"]["keys"]
                ]
            )
            report += f"- **⏰ Overdue:** {risks['overdue_issues']['count']} issue(s) - {formatted_keys}\n"
            has_risks = True
        if risks["stale_issues"]["count"] > 0:
            report += f"- **🗓️ Stale:** {risks['stale_issues']['count']} issue(s) need updates:\n"
            for key in risks["stale_issues"]["keys"]:
                report += f"  - {self._format_issue_link(key)}\n"
            has_risks = True

        if not has_risks:
            report += "-  No immediate risks identified.\n"
        print("Daily summary generated.")
        return report

    def generate_full_report(self):
        """
        Generates a detailed report including sprint hygiene and workload.
        """
        print("Generating full report...")
        daily_summary = self.generate_daily_summary()

        if not self.results:
            print("No analysis results to report for full report.")
            return daily_summary

        report = daily_summary
        hygiene = self.results["hygiene"]
        workload = self.results["workload"]

        report += "\n## Sprint Hygiene Details\n"
        if (
            not hygiene["unassigned_issues"]["is_issue"]
            and not hygiene["unestimated_issues"]["is_issue"]
            and not hygiene["issues_without_fix_versions"]["is_issue"]
        ):
            report += "-  Sprint hygiene looks good!\n"
        else:
            if hygiene["unassigned_issues"]["is_issue"]:
                formatted_keys = ", ".join(
                    [
                        self._format_issue_link(key)
                        for key in hygiene["unassigned_issues"]["keys"]
                    ]
                )
                report += f"- **Unassigned:** {hygiene['unassigned_issues']['count']} issues ({hygiene['unassigned_issues']['percentage']:.2f}%)"
                report += f" are unassigned. Keys: {formatted_keys}\n"
            if hygiene["unestimated_issues"]["is_issue"]:
                formatted_keys = ", ".join(
                    [
                        self._format_issue_link(key)
                        for key in hygiene["unestimated_issues"]["keys"]
                    ]
                )
                report += f"- **Unestimated:** {hygiene['unestimated_issues']['count']} issues ({hygiene['unestimated_issues']['percentage']:.2f}%)"
                report += f" have no story points. Keys: {formatted_keys}\n"
            if hygiene["issues_without_fix_versions"]["is_issue"]:
                formatted_keys = ", ".join(
                    [
                        self._format_issue_link(key)
                        for key in hygiene["issues_without_fix_versions"]["keys"]
                    ]
                )
                report += f"- **No Fix Version:** {hygiene['issues_without_fix_versions']['count']} issues ({hygiene['issues_without_fix_versions']['percentage']:.2f}%)"
                report += f" have no fix version. Keys: {formatted_keys}\n"

        report += self._generate_issues_without_fix_versions_table()

        report += "\n## Workload Summary\n"
        if not workload:
            report += "- No assigned issues with story points to analyze.\n"
        else:
            report += "| Assignee | Total Points |\n"
            report += "|----------|--------------|\n"
            for assignee, points in workload.items():
                report += f"| {assignee} | {points['total_points']} |\n"

        detailed_workload = self.results.get("detailed_workload", {})
        if detailed_workload:
            report += "\n## Detailed Workload Breakdown\n"
            for assignee, issues_list in detailed_workload.items():
                report += f"### {assignee}\n"
                report += "| Issue | Type | SP | Status | Days Assigned |\n"
                report += "|-------|------|----|--------|---------------|\n"
                for issue_data in issues_list:
                    report += f"| [{issue_data['issue_key']}]({issue_data['issue_link']}) | {issue_data['issue_type']} | {issue_data['story_points']} | {issue_data['current_status']} | {issue_data['days_assigned']} |\n"
                report += "\n"

        print("Full report generated.")
        return report

    def _generate_issues_without_fix_versions_table(self):
        """
        Generates a Markdown table of issues without fixVersions, excluding bugs.
        """
        print("Generating issues without fixVersions table...")
        table_content = "\n## Issues Without Fix Versions (Excluding Bugs)\n"

        issues_without_fix_versions = []
        all_issues = self.results.get(
            "all_issues", []
        )  # Assuming 'all_issues' contains the full issue objects

        for issue in all_issues:
            issue_type = issue.fields.issuetype.name
            fix_versions = issue.fields.fixVersions

            if issue_type.lower() != "bug" and (
                not fix_versions or len(fix_versions) == 0
            ):
                issues_without_fix_versions.append(issue)

        if not issues_without_fix_versions:
            table_content += "No issues found without fix versions (excluding bugs).\n"
        else:
            table_content += "| Issue ID | Issue Type | Fix Versions | Reported By |\n"
            table_content += "|----------|------------|--------------|-------------|\n"
            for issue in issues_without_fix_versions:
                issue_id = self._format_issue_link(issue.key)
                issue_type = issue.fields.issuetype.name
                fix_versions_str = "N/A"
                reporter_name = (
                    issue.fields.reporter.displayName
                    if issue.fields.reporter
                    else "Unassigned"
                )
                table_content += f"| {issue_id} | {issue_type} | {fix_versions_str} | {reporter_name} |\n"

        print("Issues without fixVersions table generated.")
        return table_content

    def export_report(self, report_content, filename="sprint_report", formats=["md"]):
        """
        Exports the report to a file in the specified formats.
        """
        reports_dir = Path(__file__).parent.parent / "reports"
        os.makedirs(reports_dir, exist_ok=True)

        print(f"Exporting report to {reports_dir.resolve()}...")
        for fmt in formats:
            if fmt == "md":
                file_path = reports_dir / f"{filename}.md"
                with open(file_path, "w") as f:
                    f.write(report_content)
                print(f"Report exported to {file_path.resolve()}")
            elif fmt == "pdf":
                md_file_path = reports_dir / f"{filename}.md"
                pdf_file_path = reports_dir / f"{filename}.pdf"
                if not md_file_path.exists():
                    with open(md_file_path, "w") as f:
                        f.write(report_content)

                try:
                    print(f"Attempting to export PDF to {pdf_file_path.resolve()}...")
                    subprocess.run(
                        [
                            str(Path(sys.executable).parent / "mdpdf"),
                            str(md_file_path),
                            "-o",
                            str(pdf_file_path),
                        ],
                        check=True,
                    )
                    print(f"Report exported to {pdf_file_path.resolve()}")
                except Exception as e:
                    print(f"\nError exporting to PDF: {e}")
                    print("Please ensure you have Google Chrome or Chromium installed.")
            else:
                print(f"Format '{fmt}' not supported yet.")
        print("Report export process complete.")
