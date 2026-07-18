import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .classifier import classify
from .config import Settings
from .db import Database
from .models import Priority, Radar, RadarResult
from .sheets import SheetsSync
from .sources import SeedSource, Source, XSource


class RadarService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.database_path)
        self.db.initialize()

    def sources(self) -> list[Source]:
        s = self.settings
        return [
            XSource(s.x_bearer_token, s.request_timeout_seconds, s.radar_timezone, s.max_results_per_radar),
            SeedSource(Radar.TIKTOK, s.public_profile_seeds, s.radar_timezone),
            SeedSource(Radar.SHOWROOM, s.public_profile_seeds, s.radar_timezone),
        ]

    def run(self, sync_sheets: bool = True) -> list[RadarResult]:
        now = datetime.now(ZoneInfo(self.settings.radar_timezone))
        run_id = str(uuid.uuid4())
        results: list[RadarResult] = []
        for source in self.sources():
            result = RadarResult(radar=source.radar)
            try:
                candidates = source.discover()
                result.searched = len(candidates)
                for candidate in candidates:
                    try:
                        item = classify(candidate)
                        _, added = self.db.upsert(item)
                        if added:
                            result.added += 1
                            result.excluded += int(item.excluded_reason is not None)
                            result.s_count += int(item.priority == Priority.S)
                        else:
                            result.duplicates += 1
                    except Exception as exc:
                        result.failures += 1
                        result.errors.append(f"候補保存失敗: {type(exc).__name__}: {exc}")
                        result.unpersisted.append(candidate.source_url)
            except Exception as exc:
                result.failures += 1
                result.errors.append(f"{source.radar.value}取得失敗: {type(exc).__name__}: {exc}")
            self.db.save_log(run_id, now.isoformat(), result)
            results.append(result)

        if sync_sheets:
            try:
                self._sync_sheets()
                for result in results:
                    self.db.update_log(run_id, result, sheet_synced=True)
            except Exception as exc:
                for result in results:
                    result.failures += 1
                    result.errors.append(f"Google Sheets同期失敗: {type(exc).__name__}: {exc}")
                    self.db.update_log(run_id, result)
        self._write_report(run_id, now, results)
        return results

    def _sync_sheets(self) -> None:
        if not self.settings.google_spreadsheet_id or not self.settings.google_service_account_json:
            raise RuntimeError("GOOGLE_SPREADSHEET_ID / GOOGLE_SERVICE_ACCOUNT_JSON が未設定")
        SheetsSync(self.settings.google_spreadsheet_id, self.settings.google_service_account_json).sync(self.db)

    @staticmethod
    def _write_report(run_id: str, now: datetime, results: list[RadarResult]) -> None:
        path = Path("reports")
        path.mkdir(exist_ok=True)
        payload = {"run_id": run_id, "executed_at": now.isoformat(), "radars": [r.model_dump(mode="json") for r in results]}
        (path / f"{now.strftime('%Y%m%dT%H%M%S')}-{run_id[:8]}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
