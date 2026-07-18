import json
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from .db import Database

TABS = ["候補者マスター", "X Radar", "TikTok Radar", "SHOWROOM Radar", "対象外・保留", "実行ログ"]
CANDIDATE_HEADERS = [
    "DB ID", "表示名", "仮優先度", "スコア", "仮評価理由", "発見Radar", "発見日時",
    "本人投稿", "X URL", "Instagram ID", "Instagram URL", "Instagram確認状態",
    "TikTok URL", "SHOWROOM URL", "その他プロフィールURL", "情報源URL", "年齢情報",
    "所属情報", "公開根拠", "最終更新",
]
EXCLUDED_HEADERS = CANDIDATE_HEADERS + ["対象外・保留理由", "再確認優先度"]
LOG_HEADERS = ["日時", "Radar", "検索件数", "追加件数", "重複件数", "対象外件数", "失敗件数", "S級！！件数", "エラー内容", "未更新候補"]


class SheetsSync:
    def __init__(self, spreadsheet_id: str, credentials_path: Path):
        credentials = Credentials.from_service_account_file(
            credentials_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        self.api = build("sheets", "v4", credentials=credentials, cache_discovery=False).spreadsheets()
        self.spreadsheet_id = spreadsheet_id

    def sync(self, db: Database) -> None:
        self._ensure_tabs()
        active = db.rows("SELECT * FROM candidates WHERE excluded_reason IS NULL ORDER BY id")
        excluded = db.rows("SELECT * FROM candidates WHERE excluded_reason IS NOT NULL ORDER BY id")
        logs = db.rows("SELECT * FROM execution_logs ORDER BY id")
        values = {
            "候補者マスター": [CANDIDATE_HEADERS] + [self._candidate_row(r) for r in active],
            "X Radar": [CANDIDATE_HEADERS] + [self._candidate_row(r) for r in active if r["radar"] == "X Radar"],
            "TikTok Radar": [CANDIDATE_HEADERS] + [self._candidate_row(r) for r in active if r["radar"] == "TikTok Radar"],
            "SHOWROOM Radar": [CANDIDATE_HEADERS] + [self._candidate_row(r) for r in active if r["radar"] == "SHOWROOM Radar"],
            "対象外・保留": [EXCLUDED_HEADERS] + [self._candidate_row(r) + [r["excluded_reason"], r["review_priority"]] for r in excluded],
            "実行ログ": [LOG_HEADERS] + [[r["executed_at"], r["radar"], r["searched"], r["added"], r["duplicates"], r["excluded"], r["failures"], r["s_count"], _join_json(r["errors_json"]), _join_json(r["unpersisted_json"])] for r in logs],
        }
        self.api.values().batchClear(spreadsheetId=self.spreadsheet_id, body={"ranges": [f"'{t}'!A:V" for t in TABS]}).execute()
        self.api.values().batchUpdate(spreadsheetId=self.spreadsheet_id, body={
            "valueInputOption": "RAW", "data": [{"range": f"'{tab}'!A1", "values": rows} for tab, rows in values.items()]
        }).execute()

    def _ensure_tabs(self) -> None:
        metadata = self.api.get(spreadsheetId=self.spreadsheet_id, fields="sheets.properties").execute()
        existing = {s["properties"]["title"] for s in metadata.get("sheets", [])}
        requests = [
            {
                "addSheet": {
                    "properties": {
                        "title": tab,
                        "gridProperties": {"frozenRowCount": 1},
                    }
                }
            }
            for tab in TABS
            if tab not in existing
        ]
        if requests:
            self.api.batchUpdate(spreadsheetId=self.spreadsheet_id, body={"requests": requests}).execute()

    @staticmethod
    def _candidate_row(r: dict) -> list:
        instagram_id = (r["instagram_url"] or "").rstrip("/").rsplit("/", 1)[-1] if r["instagram_url"] else ""
        return [r["id"], r["display_name"], r["priority"], r["score"], r["reason"], r["radar"], r["discovered_at"], "本人" if r["source_is_self_post"] else "未確認", r["x_url"], instagram_id, r["instagram_url"] or "未確認", r["instagram_status"], r["tiktok_url"], r["showroom_url"], r["other_profile_url"], r["source_url"], r["age_text"], r["affiliation_text"], _join_json(r["evidence_json"]), r["updated_at"]]


def _join_json(value: str) -> str:
    return " / ".join(json.loads(value))
