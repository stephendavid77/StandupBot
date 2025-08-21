import yaml
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"

def get_config():
    config_path = Path(__file__).parent.parent.parent / "config/config.yaml"
    if not config_path.exists():
        config_path = Path(__file__).parent.parent.parent / "config/config.yaml.sample"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
