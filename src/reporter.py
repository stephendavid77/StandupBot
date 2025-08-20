import os
from pathlib import Path
from src.pdf_generator import PdfGenerator


class Reporter:
    """
    Base class for generating reports from the analysis results.
    Contains common utility methods.
    """

    def __init__(self, results, config, project_config):
        self.results = results
        self.config = config
        self.project_config = project_config
        self.jira_browse_url = config.get("jira", {}).get(
            "jira_browse_url", "https://macystech.atlassian.net/browse/"
        )

    def _format_issue_link(self, issue_key):
        return f"[{issue_key}]({self.jira_browse_url}{issue_key})"

    def _get_jira_board_link(self):
        jira_server = self.config.get("jira", {}).get("server")
        board_id = self.project_config.get("board_id")
        project_key = self.project_config.get("project_key")  # Get project_key
        if jira_server and board_id and project_key:
            return f"{jira_server}/jira/software/c/projects/{project_key}/boards/{board_id}"
        return "N/A"

    def export_report(self, report_content, filename="sprint_report", formats=["md"]):
        """
        Exports the report to a file in the specified formats.
        """
        reports_dir = Path(__file__).parent.parent / "reports"
        os.makedirs(reports_dir, exist_ok=True)
        exported_files = []

        print(f"Exporting report to {reports_dir.resolve()}...")
        for fmt in formats:
            if fmt == "md":
                file_path = reports_dir / f"{filename}.md"
                with open(file_path, "w") as f:
                    f.write(report_content)
                print(f"Report exported to {file_path.resolve()}")
                exported_files.append(str(file_path.resolve()))
            elif fmt == "pdf":
                pdf_file_path = reports_dir / f"{filename}.pdf"
                pdf_generator = PdfGenerator()
                pdf_generator.generate_pdf(report_content, pdf_file_path)
                exported_files.append(str(pdf_file_path.resolve()))
            else:
                print(f"Format '{fmt}' not supported yet.")
        print("Report export process complete.")
        return exported_files
