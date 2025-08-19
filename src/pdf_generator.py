import os
import subprocess


class PdfGenerator:
    def __init__(self):
        pass

    def generate_pdf(self, report_content, output_pdf_path):
        # md-to-pdf takes Markdown as input, so we'll write the report_content directly
        temp_md_file_path = output_pdf_path.parent / f"{output_pdf_path.stem}.md"

        with open(temp_md_file_path, "w") as f:
            f.write(report_content)

        try:
            print(f"Attempting to export PDF to {output_pdf_path.resolve()}...\n")
            # Execute md-to-pdf command
            # Assuming md-to-pdf is installed globally or in PATH
            subprocess.run(
                ["md-to-pdf", str(temp_md_file_path), "-o", str(output_pdf_path)],
                check=True,
            )
            print(f"Report exported to {output_pdf_path.resolve()}")
        except FileNotFoundError:
            print("\nError: 'md-to-pdf' command not found.")
            print("Please ensure Node.js and 'md-to-pdf' are installed globally.")
            print("Install Node.js: https://nodejs.org/")
            print("Install md-to-pdf: npm install -g md-to-pdf")
        except subprocess.CalledProcessError as e:
            print(
                f"\nError exporting to PDF: Command failed with exit code {e.returncode}"
            )
            print(f"Stderr: {e.stderr.decode()}")
        except Exception as e:
            print(f"\nAn unexpected error occurred during PDF export: {e}")
        finally:
            # Clean up the temporary Markdown file
            if temp_md_file_path.exists():
                os.remove(temp_md_file_path)
