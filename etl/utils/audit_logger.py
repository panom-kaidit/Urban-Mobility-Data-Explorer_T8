import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import pandas as pd


class AuditLogger:
    """Write ETL audit outputs to file."""

    def __init__(self, log_dir: str | Path) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def write_summary(self, summary: dict[str, Any]) -> Path:
        output_path = self.log_dir / "cleaning_summary.json"
        clean_summary = self._make_json_ready(summary)

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(clean_summary, file, indent=2)

        return output_path

    def write_removed_records(self, removed_records: pd.DataFrame) -> Path:
        output_path = self.log_dir / "removed_records.csv"
        self._write_csv(removed_records, output_path)
        return output_path

    def write_suspicious_records(self, suspicious_records: pd.DataFrame) -> Path:
        output_path = self.log_dir / "suspicious_records.csv"
        self._write_csv(suspicious_records, output_path)
        return output_path

    def _write_csv(self, data: pd.DataFrame, output_path: Path) -> None:
        data.to_csv(output_path, index=False)

    def _make_json_ready(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._make_json_ready(asdict(value))

        if isinstance(value, dict):
            return {
                str(key): self._make_json_ready(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [self._make_json_ready(item) for item in value]

        if hasattr(value, "item"):
            return value.item()

        return value
