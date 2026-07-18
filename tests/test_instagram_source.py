from remibelle_radar.models import Radar
from remibelle_radar.sources import InstagramSource


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Client:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, params):
        if url.endswith("/ig_hashtag_search"):
            return _Response({"data": [{"id": "hashtag-id"}]})
        return _Response({
            "data": [{
                "id": "media-id",
                "caption": "アイドル志望 歌とダンス",
                "permalink": "https://www.instagram.com/p/example/",
                "username": "candidate_name",
            }]
        })


def _source(token="token", user_id="user-id"):
    return InstagramSource(
        token, user_id, "v23.0", ["アイドル志望"], 10, "Asia/Tokyo", 30
    )


def test_instagram_source_is_safe_when_credentials_are_missing():
    assert _source(token=None).discover() == []


def test_instagram_source_maps_public_hashtag_media(monkeypatch):
    monkeypatch.setattr("remibelle_radar.sources.httpx.Client", _Client)

    candidates = _source().discover()

    assert len(candidates) == 1
    assert candidates[0].radar == Radar.INSTAGRAM
    assert candidates[0].instagram_url == "https://www.instagram.com/candidate_name/"
    assert candidates[0].instagram_status == "本人投稿から取得"

