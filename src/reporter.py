import os
import logging
from pathlib import Path
import markdown2
from src.excel_generator import ExcelGenerator

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
        project_key = self.project_config.get("project_key")
        if jira_server and board_id and project_key:
            return f"{jira_server}/jira/software/c/projects/{project_key}/boards/{board_id}"
        return "N/A"

    def export_report(self, report_content, filename="sprint_report", formats=["md"]):
        """
        Exports the report to a file in the specified formats.
        Returns a tuple of (list of successful files, list of error messages).
        """
        reports_dir = Path(__file__).parent.parent / "reports"
        os.makedirs(reports_dir, exist_ok=True)
        successful_files = []
        error_messages = []

        logging.info(f"Exporting report to {reports_dir.resolve()}...")
        for fmt in formats:
            try:
                if fmt == "md":
                    file_path = reports_dir / f"{filename}.md"
                    with open(file_path, "w") as f:
                        f.write(report_content)
                    logging.info(f"Report exported to {file_path.resolve()}")
                    successful_files.append(str(file_path.resolve()))
                elif fmt == "html":
                    file_path = reports_dir / f"{filename}.html"
                    html_content = markdown2.markdown(report_content, extras=["tables", "fenced-code-blocks"])
                    with open(file_path, "w") as f:
                        f.write(html_content)
                    logging.info(f"Report exported to {file_path.resolve()}")
                    successful_files.append(str(file_path.resolve()))
                elif fmt == "excel":
                    file_path = reports_dir / f"{filename}.xlsx"
                    excel_generator = ExcelGenerator()
                    excel_generator.generate_excel(self.results, file_path)
                    logging.info(f"Report exported to {file_path.resolve()}")
                    successful_files.append(str(file_path.resolve()))
                else:
                    msg = f"Format '{fmt}' not supported yet."
                    logging.warning(msg)
                    error_messages.append(msg)
            except Exception as e:
                msg = f"Error exporting report to {fmt}: {e}"
                logging.error(msg)
                error_messages.append(msg)
        
        logging.info("Report export process complete.")
        return successful_files, error_messages