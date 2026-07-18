from datetime import datetime, timezone

from remibelle_radar.classifier import classify
from remibelle_radar.models import CandidateInput, Priority, Radar


def candidate(text: str, **kwargs) -> CandidateInput:
    return CandidateInput(display_name="test", radar=Radar.X, source_url="https://x.com/a/status/1", source_text=text, discovered_at=datetime.now(timezone.utc), **kwargs)


def test_broad_intake_keeps_low_information_candidate():
    assert classify(candidate("ライブに出たい")).priority in (Priority.B, Priority.REVIEW)


def test_confirmed_minor_is_excluded():
    assert classify(candidate("17歳、アイドル志望")).excluded_reason == "18歳未満確認"


def test_s_is_not_given_by_keywords_alone():
    item = classify(candidate("元アイドル またアイドル 再挑戦 アイドル志望 歌 ダンス ライブ ステージ"))
    assert item.priority != Priority.S


def test_active_affiliation_is_preserved_as_excluded():
    assert classify(candidate("現役アイドルとして活動中")).excluded_reason == "現役所属"

