import re

from .models import CandidateInput, ClassifiedCandidate, Priority

POSITIVE = {
    "元アイドル": 4,
    "またアイドル": 4,
    "アイドル志望": 3,
    "再挑戦": 3,
    "卒業": 2,
    "脱退": 2,
    "活動終了": 2,
    "オーディション": 2,
    "歌": 1,
    "ダンス": 1,
    "ライブ": 1,
    "ステージ": 1,
    "コンカフェ": 1,
    "被写体": 1,
}


def classify(candidate: CandidateInput) -> ClassifiedCandidate:
    text = " ".join(
        [candidate.source_text, candidate.age_text or "", candidate.affiliation_text or ""]
        + candidate.evidence
    )
    if _under_18(text):
        return _excluded(candidate, "18歳未満確認", "低")
    if _active_affiliation(text):
        return _excluded(candidate, "現役所属", "中")
    if _adult_activity_central(text):
        return _excluded(candidate, "過度に性的な活動が中心", "低")
    if "DM辞退" in text or "スカウトDMお断り" in text:
        return _excluded(candidate, "DM辞退", "低")

    score = sum(points for keyword, points in POSITIVE.items() if keyword in text)
    if candidate.source_is_self_post is True:
        score += 1
    linked = sum(bool(x) for x in (candidate.x_url, candidate.instagram_url, candidate.tiktok_url, candidate.showroom_url))
    score += min(linked, 2)

    # S is intentionally unreachable by keyword volume alone: it needs strong evidence,
    # a self-post, and multiple verified public links. It remains a lead, not a hiring judgment.
    if score >= 12 and candidate.source_is_self_post is True and linked >= 2 and len(candidate.evidence) >= 3:
        priority = Priority.S
    elif score >= 7:
        priority = Priority.A
    elif score >= 3:
        priority = Priority.B
    else:
        priority = Priority.REVIEW
    return ClassifiedCandidate(
        candidate=candidate,
        priority=priority,
        score=score,
        reason=" / ".join(k for k in POSITIVE if k in text) or "公開情報不足・人間による確認が必要",
    )


def _under_18(text: str) -> bool:
    ages = [int(x) for x in re.findall(r"(?<!\d)(1[0-7])\s*歳", text)]
    return bool(ages) or any(word in text for word in ("中学生", "高校1年", "高校2年"))


def _active_affiliation(text: str) -> bool:
    return any(word in text for word in ("現役アイドル", "所属中", "メンバーとして活動中"))


def _adult_activity_central(text: str) -> bool:
    return any(word in text for word in ("成人向け活動中心", "アダルト出演中心"))


def _excluded(candidate: CandidateInput, reason: str, review: str) -> ClassifiedCandidate:
    return ClassifiedCandidate(
        candidate=candidate,
        priority=Priority.REVIEW,
        score=0,
        reason=reason,
        excluded_reason=reason,
        review_priority=review,
    )

