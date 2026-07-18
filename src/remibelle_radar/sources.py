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
