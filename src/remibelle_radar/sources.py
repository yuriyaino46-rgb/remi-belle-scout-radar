import json
import math
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from .models import CandidateInput, Radar

X_QUERIES = [
    '("アイドル志望" OR "元アイドル" OR "またアイドルになりたい" OR "再挑戦") -is:retweet',
    '("アイドル卒業" OR "アイドル脱退" OR "活動終了") (歌 OR ダンス OR ライブ) -is:retweet',
    '(コンカフェ OR 被写体) (アイドル OR オーディション) -is:retweet',
]


class Source(ABC):
    radar: Radar

    @abstractmethod
    def discover(self) -> list[CandidateInput]: ...


class XSource(Source):
    radar = Radar.X

    def __init__(self, bearer_token: str | None, timeout: float, timezone: str, limit: int):
        self.token = bearer_token
        self.timeout = timeout
        self.timezone = ZoneInfo(timezone)
        self.limit = min(limit, 100)

    def discover(self) -> list[CandidateInput]:
        if not self.token:
            return []
        output: list[CandidateInput] = []
        headers = {"Authorization": f"Bearer {self.token}"}
        per_query_limit = max(10, min(math.ceil(self.limit / len(X_QUERIES)), 100))
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            for query in X_QUERIES:
                if len(output) >= self.limit:
                    break
                response = client.get(
                    "https://api.x.com/2/tweets/search/recent",
                    params={"query": query, "max_results": per_query_limit,
                            "tweet.fields": "created_at,author_id,referenced_tweets",
                            "expansions": "author_id", "user.fields": "name,username,description,url"},
                )
                response.raise_for_status()
                payload = response.json()
                users = {u["id"]: u for u in payload.get("includes", {}).get("users", [])}
                for tweet in payload.get("data", []):
                    user = users.get(tweet.get("author_id"), {})
                    username = user.get("username")
                    if not username:
                        continue
                    profile = f"https://x.com/{username}"
                    output.append(CandidateInput(
                        display_name=user.get("name") or username, radar=self.radar,
                        source_url=f"{profile}/status/{tweet['id']}", source_text=tweet.get("text", ""),
                        source_is_self_post=not bool(tweet.get("referenced_tweets")), x_url=profile,
                        other_profile_url=user.get("url"), evidence=[user.get("description", "")],
                        discovered_at=datetime.now(self.timezone),
                    ))
                    if len(output) >= self.limit:
                        break
        return output[:self.limit]


class InstagramSource(Source):
    """Official Instagram Graph API hashtag search for public recent media."""

    radar = Radar.INSTAGRAM

    def __init__(
        self,
        access_token: str | None,
        instagram_user_id: str | None,
        api_version: str,
        hashtags: list[str],
        timeout: float,
        timezone: str,
        limit: int,
    ):
        self.access_token = access_token
        self.instagram_user_id = instagram_user_id
        self.api_version = api_version
        self.hashtags = hashtags
        self.timeout = timeout
        self.timezone = ZoneInfo(timezone)
        self.limit = min(limit, 50)

    def discover(self) -> list[CandidateInput]:
        if not self.access_token or not self.instagram_user_id or not self.hashtags:
            return []

        output: list[CandidateInput] = []
        seen_media: set[str] = set()
        per_hashtag = max(1, math.ceil(self.limit / len(self.hashtags)))
        base_url = f"https://graph.facebook.com/{self.api_version}"
        common = {
            "user_id": self.instagram_user_id,
            "access_token": self.access_token,
        }
        with httpx.Client(timeout=self.timeout) as client:
            for hashtag in self.hashtags:
                if len(output) >= self.limit:
                    break
                search = client.get(
                    f"{base_url}/ig_hashtag_search",
                    params={**common, "q": hashtag},
                )
                search.raise_for_status()
                matches = search.json().get("data", [])
                if not matches:
                    continue
                media_response = client.get(
                    f"{base_url}/{matches[0]['id']}/recent_media",
                    params={
                        **common,
                        "fields": "id,caption,media_type,permalink,timestamp,username",
                        "limit": per_hashtag,
                    },
                )
                media_response.raise_for_status()
                for media in media_response.json().get("data", []):
                    media_id = str(media.get("id") or "")
                    permalink = media.get("permalink")
                    if not media_id or not permalink or media_id in seen_media:
                        continue
                    seen_media.add(media_id)
                    username = media.get("username")
                    instagram_url = f"https://www.instagram.com/{username}/" if username else None
                    output.append(CandidateInput(
                        display_name=username or f"Instagram投稿 {media_id}",
                        radar=self.radar,
                        source_url=permalink,
                        source_text=media.get("caption") or "",
                        source_is_self_post=True,
                        instagram_url=instagram_url,
                        instagram_status="本人投稿から取得" if username else "投稿者未確認",
                        evidence=[f"Instagram公開ハッシュタグ #{hashtag}", permalink],
                        discovered_at=datetime.now(self.timezone),
                    ))
                    if len(output) >= self.limit:
                        break
        return output


class SeedSource(Source):
    """Public-profile seeds for TikTok/SHOWROOM reverse lookup and reproducible dry runs."""

    def __init__(self, radar: Radar, path: Path, timezone: str):
        self.radar = radar
        self.path = path
        self.timezone = ZoneInfo(timezone)

    def discover(self) -> list[CandidateInput]:
        if not self.path.exists():
            return []
        records = json.loads(self.path.read_text(encoding="utf-8"))
        now = datetime.now(self.timezone)
        return [CandidateInput.model_validate({**r, "radar": self.radar, "discovered_at": now})
                for r in records if r.get("radar") == self.radar.value]
