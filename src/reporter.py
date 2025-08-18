import os
from pathlib import Path
from md_to_pdf import md_to_pdf

class Reporter:
    """
    Generates reports from the analysis results.
    """
    def __init__(self, results):
        self.results = results

    def generate_daily_summary(self):
        """
        Generates a concise daily summary in Markdown format.
        """
        if not self.results:
            return "No analysis results to report."

        r = self.results
        sprint_info = r['sprint_info']
        metrics = r['metrics']
        risks = r['risks']

        report = f"# Daily Sprint Summary: {sprint_info['name']}\n\n"
        report += f"**Goal:** {sprint_info['goal'] if sprint_info['goal'] else 'Not set'}\n"
        report += f"**Duration:** {sprint_info['start_date']} to {sprint_info['end_date']}\n\n"

        report += "## Sprint Progress\n"
        report += f"- **{metrics['progress_pct']:.2f}% Complete** ({metrics['status_counts']['Done']} of {metrics['total_issues']} issues)\n"
        report += f"- **Story Points:** {metrics['story_points_done']} / {metrics['total_story_points']} SP done\n\n"

        report += "## Focus Items & Risks\n"
        if risks['blocker_issues']['count'] > 0:
            report += f"- **🔥 Blockers:** {risks['blocker_issues']['count']} issue(s) - {risks['blocker_issues']['keys']}\n"
        if risks['overdue_issues']['count'] > 0:
            report += f"- ** overdue:** {risks['overdue_issues']['count']} issue(s) - {risks['overdue_issues']['keys']}\n"
        if risks['stale_issues']['count'] > 0:
            report += f"- ** Stale:** {risks['stale_issues']['count']} issue(s) need updates.\n"
        
        if not any([risks['blocker_issues']['count'], risks['overdue_issues']['count'], risks['stale_issues']['count']]):
            report += "-  No immediate risks identified.\n"

        return report

    def generate_full_report(self):
        """
        Generates a detailed report including sprint hygiene and workload.
        """
        daily_summary = self.generate_daily_summary()
        
        if not self.results:
            return daily_summary

        report = daily_summary
        hygiene = self.results['hygiene']
        workload = self.results['workload']

        report += "\n## Sprint Hygiene Details\n"
        if not hygiene['unassigned_issues']['is_issue'] and not hygiene['unestimated_issues']['is_issue']:
            report += "-  Sprint hygiene looks good!\n"
        else:
            if hygiene['unassigned_issues']['is_issue']:
                report += f"- **Unassigned:** {hygiene['unassigned_issues']['count']} issues ({hygiene['unassigned_issues']['percentage']:.2f}%) are unassigned. Keys: {hygiene['unassigned_issues']['keys']}\n"
            if hygiene['unestimated_issues']['is_issue']:
                report += f"- **Unestimated:** {hygiene['unestimated_issues']['count']} issues ({hygiene['unestimated_issues']['percentage']:.2f}%) have no story points. Keys: {hygiene['unestimated_issues']['keys']}\n"

        report += "\n## Workload Summary\n"
        if not workload:
            report += "- No assigned issues with story points to analyze.\n"
        else:
            report += "| Assignee | Total Points |\n"
            report += "|----------|--------------|\n"
            for assignee, points in workload.items():
                report += f"| {assignee} | {points['total_points']} |\n"

        return report

    def export_report(self, report_content, filename='sprint_report', formats=['md']):
        """
        Exports the report to a file in the specified formats.
        """
        reports_dir = Path(__file__).parent.parent / 'reports'
        os.makedirs(reports_dir, exist_ok=True)

        for fmt in formats:
            if fmt == 'md':
                file_path = reports_dir / f"{filename}.md"
                with open(file_path, 'w') as f:
                    f.write(report_content)
                print(f"\nReport exported to {file_path.resolve()}")
            elif fmt == 'pdf':
                md_file_path = reports_dir / f"{filename}.md"
                pdf_file_path = reports_dir / f"{filename}.pdf"
                if not md_file_path.exists():
                    with open(md_file_path, 'w') as f:
                        f.write(report_content)
                
                try:
                    md_to_pdf(str(pdf_file_path), md_file_path=str(md_file_path))
                    print(f"Report exported to {pdf_file_path.resolve()}")
                except Exception as e:
                    print(f"\nError exporting to PDF: {e}")
                    print("Please ensure you have Google Chrome or Chromium installed.")
            else:
                print(f"Format '{fmt}' not supported yet.")
