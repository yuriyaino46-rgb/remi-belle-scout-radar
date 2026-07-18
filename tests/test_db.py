from datetime import datetime, timezone

from remibelle_radar.classifier import classify
from remibelle_radar.db import Database
from remibelle_radar.models import CandidateInput, Radar


def test_dedup_uses_social_url_not_name(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    base = dict(radar=Radar.X, source_text="アイドル志望", discovered_at=datetime.now(timezone.utc))
    first = CandidateInput(display_name="A", source_url="https://x.com/shared/status/1", x_url="https://x.com/shared", **base)
    second = CandidateInput(display_name="別名", source_url="https://x.com/shared/status/2", x_url="https://x.com/shared", **base)
    assert db.upsert(classify(first))[1] is True
    assert db.upsert(classify(second))[1] is False


def test_same_name_different_social_urls_are_not_merged(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    base = dict(display_name="同名", radar=Radar.X, source_text="歌", discovered_at=datetime.now(timezone.utc))
    a = CandidateInput(source_url="https://x.com/a/status/1", x_url="https://x.com/a", **base)
    b = CandidateInput(source_url="https://x.com/b/status/1", x_url="https://x.com/b", **base)
    assert db.upsert(classify(a))[1] is True
    assert db.upsert(classify(b))[1] is True

