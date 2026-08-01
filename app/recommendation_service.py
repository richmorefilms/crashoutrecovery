"""Topic clustering + collaborative filtering recommendations."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from app.db import get_conn, row_to_dict, utc_now_iso

STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "is",
        "are",
        "was",
        "be",
        "as",
        "at",
        "by",
        "from",
        "it",
        "this",
        "that",
        "your",
        "you",
        "my",
        "our",
        "their",
        "one",
        "small",
        "move",
        "clip",
        "video",
        "feed",
    }
)

TOPIC_HINTS = (
    "recovery",
    "motivation",
    "mentalhealth",
    "calm",
    "draft",
    "pause",
    "momentum",
    "creator",
    "safe",
    "spike",
    "account",
    "growth",
    "engagement",
    "audience",
    "viral",
    "community",
    "uplift",
    "breakthrough",
)

# Stigmatizing / negative free-token topics — never surface as cluster keys
BLOCKED_TOPIC_TOKENS = frozenset(
    {
        "addiction",
        "addict",
        "addicted",
        "sobriety",
        "relapse",
        "sad",
        "sadness",
        "depress",
        "depression",
        "depressed",
        "suicide",
        "suicidal",
        "trauma",
        "shame",
        "stigma",
        "drunk",
        "overdose",
        "withdraw",
        "withdrawal",
    }
)

# Creator Momentum Clusters — positive display galaxy (slug → copy + keyword map)
CREATOR_MOMENTUM_CLUSTERS: dict[str, dict[str, Any]] = {
    "growth_boosters": {
        "display_name": "Growth Boosters",
        "description": "Moves that compound reach, consistency, and forward momentum.",
        "keywords": ("growth", "boost", "scale", "expand", "momentum", "spike"),
    },
    "engagement_drivers": {
        "display_name": "Engagement Drivers",
        "description": "Hooks, replies, and prompts that spark real interaction.",
        "keywords": ("engagement", "comment", "reply", "interact", "hook"),
    },
    "audience_builders": {
        "display_name": "Audience Builders",
        "description": "Ideas that welcome new viewers and deepen loyalty.",
        "keywords": ("audience", "subscriber", "follow", "community", "fan"),
    },
    "trend_accelerators": {
        "display_name": "Trend Accelerators",
        "description": "Formats and moments riding what's rising right now.",
        "keywords": ("trend", "trending", "timely", "now", "wave"),
    },
    "high_impact_topics": {
        "display_name": "High-Impact Topics",
        "description": "High-signal themes that punch above their length.",
        "keywords": ("impact", "power", "bold", "strong", "clarity"),
    },
    "evergreen_creators": {
        "display_name": "Evergreen Creators",
        "description": "Timeless clips that keep working long after publish.",
        "keywords": ("evergreen", "creator", "craft", "archive", "classic"),
    },
    "viral_potential": {
        "display_name": "Viral Potential",
        "description": "Share-ready angles with breakout energy.",
        "keywords": ("viral", "share", "breakout", "explode", "clip"),
    },
    "community_sparks": {
        "display_name": "Community Sparks",
        "description": "Conversation starters that light up your circle.",
        "keywords": ("community", "together", "collab", "circle", "crew"),
    },
    "opportunity_zones": {
        "display_name": "Opportunity Zones",
        "description": "Open lanes where your next post can land clean.",
        "keywords": ("opportunity", "lane", "gap", "opening", "chance"),
    },
    "rising_niches": {
        "display_name": "Rising Niches",
        "description": "Emerging corners of the map with room to lead.",
        "keywords": ("niche", "rising", "emerging", "lane", "vertical"),
    },
    "creator_wins": {
        "display_name": "Creator Wins",
        "description": "Proof points, milestones, and celebrate-able progress.",
        "keywords": ("win", "wins", "milestone", "progress", "success"),
    },
    "accountability_themes": {
        "display_name": "Accountability Themes",
        "description": "Check-ins and commitments that keep the streak honest.",
        "keywords": ("account", "accountability", "checkin", "commit", "habit", "draft", "pause"),
    },
    "uplift_stories": {
        "display_name": "Uplift Stories",
        "description": "Forward-looking recovery energy without stigma or shame.",
        "keywords": ("recovery", "uplift", "hope", "rebuild", "safe"),
    },
    "motivation_mindset": {
        "display_name": "Motivation & Mindset",
        "description": "Fuel for focus, grit, and choosing the next small move.",
        "keywords": ("motivation", "mindset", "mentalhealth", "focus", "grit", "calm"),
    },
    "breakthrough_moments": {
        "display_name": "Breakthrough Moments",
        "description": "Turning-point clips that mark a clear level-up.",
        "keywords": ("breakthrough", "turnaround", "levelup", "shift", "aha"),
    },
}

_CREATOR_CLUSTER_SLUGS = tuple(CREATOR_MOMENTUM_CLUSTERS.keys())

# Direct topic → cluster slug (covers TOPIC_HINTS + common aliases)
TOPIC_TO_CREATOR_CLUSTER: dict[str, str] = {
    "recovery": "uplift_stories",
    "motivation": "motivation_mindset",
    "mentalhealth": "motivation_mindset",
    "calm": "motivation_mindset",
    "draft": "accountability_themes",
    "pause": "accountability_themes",
    "momentum": "growth_boosters",
    "creator": "evergreen_creators",
    "safe": "uplift_stories",
    "spike": "growth_boosters",
    "account": "accountability_themes",
    "growth": "growth_boosters",
    "engagement": "engagement_drivers",
    "audience": "audience_builders",
    "viral": "viral_potential",
    "community": "community_sparks",
    "uplift": "uplift_stories",
    "breakthrough": "breakthrough_moments",
}


def map_topic_to_creator_cluster(topic: str) -> str:
    """Map a raw topic token onto a Creator Momentum cluster slug."""
    t = str(topic or "").strip().lower()
    if not t:
        return "opportunity_zones"
    if t in TOPIC_TO_CREATOR_CLUSTER:
        return TOPIC_TO_CREATOR_CLUSTER[t]
    if t in CREATOR_MOMENTUM_CLUSTERS:
        return t
    for slug, meta in CREATOR_MOMENTUM_CLUSTERS.items():
        for kw in meta.get("keywords") or ():
            if kw == t or kw in t or t in kw:
                return slug
    # Stable fallback so free tokens still land in the positive galaxy
    idx = sum(ord(c) for c in t) % len(_CREATOR_CLUSTER_SLUGS)
    return _CREATOR_CLUSTER_SLUGS[idx]


def creator_cluster_meta(slug: str) -> dict[str, str]:
    meta = CREATOR_MOMENTUM_CLUSTERS.get(slug) or CREATOR_MOMENTUM_CLUSTERS["opportunity_zones"]
    return {
        "display_name": str(meta["display_name"]),
        "description": str(meta["description"]),
    }


def extract_topics(item: dict[str, Any]) -> list[str]:
    """Simple keyword topics from title + description (no ML)."""
    text = " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("description") or ""),
            str(item.get("channel") or ""),
            str(item.get("hashtag") or ""),
        ]
    ).lower()
    text = re.sub(r"[^a-z0-9\s#]", " ", text)
    tokens = [t.lstrip("#") for t in text.split() if t]
    topics: list[str] = []
    seen: set[str] = set()
    for hint in TOPIC_HINTS:
        if hint in text and hint not in seen:
            topics.append(hint)
            seen.add(hint)
    for tok in tokens:
        if len(tok) < 4 or tok in STOPWORDS or tok in seen:
            continue
        if tok in BLOCKED_TOPIC_TOKENS:
            continue
        if tok.isalpha() or tok.isalnum():
            topics.append(tok)
            seen.add(tok)
        if len(topics) >= 8:
            break
    if not topics:
        platform = str(item.get("platform") or "general").lower()
        topics = [platform if platform != "unknown" else "general"]
    return topics


def cluster_items_by_topic(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group items by shared topics."""
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        topics = extract_topics(item)
        item["topics"] = topics
        for topic in topics:
            clusters[topic].append(item)
    return dict(clusters)


def build_topic_graph(items: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """
    Topic co-occurrence graph.
    nodes: topics; edges: co-occurrence strength (normalized).
    """
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    topic_counts: dict[str, int] = defaultdict(int)
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        topics = sorted(set(extract_topics(raw)))
        for t in topics:
            topic_counts[t] += 1
        for i, a in enumerate(topics):
            for b in topics[i + 1 :]:
                pair_counts[(a, b)] += 1

    adjacency: dict[str, dict[str, float]] = {t: {} for t in topic_counts}
    for (a, b), count in pair_counts.items():
        # Strength relative to rarer topic frequency
        denom = max(1, min(topic_counts[a], topic_counts[b]))
        strength = round(count / denom, 4)
        adjacency[a][b] = strength
        adjacency[b][a] = strength
    return adjacency


def compute_similarity(
    user_history: set[str] | list[str],
    other_users_history: set[str] | list[str],
) -> float:
    """Jaccard similarity on item_ids (+ platforms when encoded as platform:id)."""
    a = {str(x) for x in (user_history or []) if x}
    b = {str(x) for x in (other_users_history or []) if x}
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return round(inter / union, 4) if union else 0.0


def _history_keys_for_user(user_id: int) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT item_id, platform FROM user_history
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
    keys: set[str] = set()
    for row in rows:
        d = row_to_dict(row)
        item_id = str(d.get("item_id") or "")
        platform = str(d.get("platform") or "")
        if item_id:
            keys.add(item_id)
            if platform:
                keys.add(f"{platform}:{item_id}")
                keys.add(platform)
    return keys


def _all_user_histories(exclude_user_id: int | None = None) -> dict[int, set[str]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, item_id, platform FROM user_history"
        ).fetchall()
    out: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        d = row_to_dict(row)
        uid = int(d["user_id"])
        if exclude_user_id is not None and uid == exclude_user_id:
            continue
        item_id = str(d.get("item_id") or "")
        platform = str(d.get("platform") or "")
        if item_id:
            out[uid].add(item_id)
            if platform:
                out[uid].add(f"{platform}:{item_id}")
                out[uid].add(platform)
    return dict(out)


def cache_topics_for_items(items: list[dict[str, Any]]) -> None:
    """Upsert TopicCache rows for items."""
    with get_conn() as conn:
        for raw in items or []:
            if not isinstance(raw, dict):
                continue
            item_id = str(raw.get("id") or "")
            if not item_id:
                continue
            topics = extract_topics(raw)
            payload = json.dumps(topics)
            existing = conn.execute(
                "SELECT id FROM topic_cache WHERE item_id = ?",
                (item_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE topic_cache SET topics = ? WHERE item_id = ?",
                    (payload, item_id),
                )
            else:
                conn.execute(
                    "INSERT INTO topic_cache (item_id, topics) VALUES (?, ?)",
                    (item_id, payload),
                )


def store_user_similarity(user_id: int, similar_user_id: int, score: float) -> None:
    with get_conn() as conn:
        existing = conn.execute(
            """
            SELECT id FROM user_similarity
            WHERE user_id = ? AND similar_user_id = ?
            """,
            (user_id, similar_user_id),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE user_similarity SET score = ? WHERE id = ?
                """,
                (score, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO user_similarity (user_id, similar_user_id, score)
                VALUES (?, ?, ?)
                """,
                (user_id, similar_user_id, score),
            )


def recommend_from_similar_users(user_id: int | str, *, limit: int = 12) -> list[dict[str, Any]]:
    """Find top similar users and recommend items they engaged with."""
    uid = int(user_id)
    mine = _history_keys_for_user(uid)
    others = _all_user_histories(exclude_user_id=uid)
    scored: list[tuple[int, float]] = []
    for other_id, hist in others.items():
        sim = compute_similarity(mine, hist)
        if sim > 0:
            scored.append((other_id, sim))
            store_user_similarity(uid, other_id, sim)
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:5]
    if not top:
        return []

    my_items = {k for k in mine if ":" not in k and k not in ("youtube", "tiktok", "ad")}
    recommended_ids: list[str] = []
    seen: set[str] = set()
    with get_conn() as conn:
        for other_id, _sim in top:
            rows = conn.execute(
                """
                SELECT item_id, platform FROM user_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 20
                """,
                (other_id,),
            ).fetchall()
            for row in rows:
                d = row_to_dict(row)
                item_id = str(d.get("item_id") or "")
                if not item_id or item_id in my_items or item_id in seen:
                    continue
                seen.add(item_id)
                recommended_ids.append(item_id)
                if len(recommended_ids) >= limit:
                    break
            if len(recommended_ids) >= limit:
                break

    # Map to feed cards from current unified feed when possible
    from app.feed_service import build_unified_all_response

    feed = build_unified_all_response(max_results=50, with_ads=False)
    by_id = {str(i.get("id")): i for i in (feed.get("items") or []) if isinstance(i, dict)}
    out: list[dict[str, Any]] = []
    for item_id in recommended_ids:
        if item_id in by_id:
            card = dict(by_id[item_id])
            card["source"] = "collaborative"
            out.append(card)
        else:
            out.append(
                {
                    "id": item_id,
                    "platform": "unknown",
                    "title": f"Recommended {item_id}",
                    "thumbnail": None,
                    "channel": "Similar users",
                    "source": "collaborative",
                }
            )
    return out


def _feed_items(max_results: int = 24) -> list[dict[str, Any]]:
    from app.feed_service import build_unified_all_response

    feed = build_unified_all_response(max_results=max_results, with_ads=False)
    return list(feed.get("items") or [])


def build_topics_response(*, max_results: int = 24) -> dict[str, Any]:
    items = _feed_items(max_results=max_results)
    cache_topics_for_items(items)
    clusters = cluster_items_by_topic(items)

    # Re-bucket into Creator Momentum Clusters (positive display galaxy)
    merged: dict[str, dict[str, Any]] = {}
    for topic, members in clusters.items():
        if str(topic).lower() in BLOCKED_TOPIC_TOKENS:
            continue
        slug = map_topic_to_creator_cluster(topic)
        bucket = merged.get(slug)
        if not bucket:
            meta = creator_cluster_meta(slug)
            bucket = {
                "id": f"topic_{slug}",
                "topic": slug,
                "display_name": meta["display_name"],
                "description": meta["description"],
                "count": 0,
                "items": [],
                "source_topics": [],
                "_seen": set(),
            }
            merged[slug] = bucket
        if topic not in bucket["source_topics"]:
            bucket["source_topics"].append(topic)
        for member in members:
            mid = str(member.get("id") or "")
            if mid and mid in bucket["_seen"]:
                continue
            if mid:
                bucket["_seen"].add(mid)
            if len(bucket["items"]) < 8:
                bucket["items"].append(member)

    cluster_items = []
    for slug, bucket in sorted(merged.items(), key=lambda kv: len(kv[1]["_seen"]), reverse=True):
        seen = bucket.pop("_seen", set())
        bucket["count"] = len(seen) if seen else len(bucket["items"])
        cluster_items.append(bucket)

    return {
        "ok": True,
        "platform": "unified",
        "lane": "topics",
        "title": "Topic Clusters",
        "items": cluster_items,
        "count": len(cluster_items),
        "meta": {
            "cluster_count": len(cluster_items),
            "item_count": len(items),
            "galaxy": "creator_momentum",
        },
    }


def build_graph_response(*, max_results: int = 24) -> dict[str, Any]:
    items = _feed_items(max_results=max_results)
    graph = build_topic_graph(items)
    nodes = [
        {"id": topic, "neighbors": neighbors}
        for topic, neighbors in sorted(graph.items(), key=lambda kv: kv[0])
    ]
    return {
        "ok": True,
        "platform": "unified",
        "lane": "topic_graph",
        "title": "Topic Graph",
        "items": nodes,
        "count": len(nodes),
        "meta": {"adjacency": graph, "node_count": len(nodes)},
    }


def build_similar_response(user_id: int | str, *, limit: int = 12) -> dict[str, Any]:
    items = recommend_from_similar_users(user_id, limit=limit)
    return {
        "ok": True,
        "platform": "unified",
        "lane": "similar",
        "title": "Similar Users Recommendations",
        "items": items,
        "count": len(items),
        "meta": {"user_id": int(user_id) if str(user_id).isdigit() else user_id},
    }


def recommend_all(user_id: int | str, *, max_results: int = 12) -> dict[str, Any]:
    """Combine topic clusters + personalized ranking + collaborative filtering."""
    from app.ranking_service import personalize_feed

    uid = int(user_id) if str(user_id).isdigit() else user_id
    base_items = _feed_items(max_results=max_results * 2)
    cache_topics_for_items(base_items)
    clusters = cluster_items_by_topic(base_items)
    personalized = personalize_feed(uid, base_items)
    collab = recommend_from_similar_users(uid, limit=max_results)

    # Merge unique items: collab first, then personalized
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in collab + personalized:
        iid = str(item.get("id") or "")
        if not iid or iid in seen:
            continue
        seen.add(iid)
        topics = extract_topics(item)
        card = dict(item)
        card["topics"] = topics
        merged.append(card)
        if len(merged) >= max_results:
            break

    top_topics = sorted(clusters.keys(), key=lambda t: len(clusters[t]), reverse=True)[:8]
    return {
        "ok": True,
        "platform": "unified",
        "lane": "recommendations",
        "title": "Recommended For You",
        "items": merged,
        "count": len(merged),
        "meta": {
            "user_id": uid,
            "top_topics": top_topics,
            "cluster_count": len(clusters),
            "collaborative_count": len(collab),
            "personalized_count": len(personalized),
        },
    }


def detect_fraudulent_behavior(user_id: int | str) -> dict[str, Any]:
    """
    Fraud signals: abnormal click velocity, repeated ad clicks,
    identical patterns across accounts.
    """
    uid = int(user_id)
    signals: list[str] = []
    with get_conn() as conn:
        clicks = conn.execute(
            """
            SELECT COUNT(*) AS c FROM ad_clicks
            WHERE creator_id = ?
              AND timestamp >= datetime('now', '-5 minutes')
            """,
            (uid,),
        ).fetchone()
        click_n = int(clicks["c"] if clicks else 0)
        if click_n >= 8:
            signals.append("abnormal_click_velocity")

        total_clicks = conn.execute(
            "SELECT COUNT(*) AS c FROM ad_clicks WHERE creator_id = ?",
            (uid,),
        ).fetchone()
        if int(total_clicks["c"] if total_clicks else 0) >= 20:
            # Same ad hammered repeatedly
            top = conn.execute(
                """
                SELECT ad_id, COUNT(*) AS c FROM ad_clicks
                WHERE creator_id = ?
                GROUP BY ad_id
                ORDER BY c DESC
                LIMIT 1
                """,
                (uid,),
            ).fetchone()
            if top and int(top["c"]) >= 10:
                signals.append("repeated_ad_clicks")

        hist = conn.execute(
            """
            SELECT item_id, platform FROM user_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
            """,
            (uid,),
        ).fetchall()
        pattern = tuple(
            (str(row_to_dict(r).get("item_id")), str(row_to_dict(r).get("platform")))
            for r in hist
        )
        if len(pattern) >= 5:
            others = conn.execute(
                """
                SELECT DISTINCT user_id FROM user_history
                WHERE user_id != ?
                """,
                (uid,),
            ).fetchall()
            for other in others:
                oid = int(other["user_id"])
                ohist = conn.execute(
                    """
                    SELECT item_id, platform FROM user_history
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                    """,
                    (oid,),
                ).fetchall()
                op = tuple(
                    (
                        str(row_to_dict(r).get("item_id")),
                        str(row_to_dict(r).get("platform")),
                    )
                    for r in ohist
                )
                if op and op == pattern:
                    signals.append("identical_patterns_across_accounts")
                    break

        for sig in signals:
            conn.execute(
                """
                INSERT INTO fraud_signals (user_id, signal, timestamp)
                VALUES (?, ?, ?)
                """,
                (uid, sig, utc_now_iso()),
            )

    return {
        "ok": True,
        "platform": "unified",
        "lane": "fraud",
        "title": "Fraud Detection",
        "items": [{"id": f"fraud_{uid}", "user_id": uid, "signals": signals}],
        "count": 1,
        "meta": {
            "user_id": uid,
            "fraudulent": bool(signals),
            "signals": signals,
        },
    }


def mark_user_fraudulent(user_id: int | str, *, reason: str | None = None) -> dict[str, Any]:
    uid = int(user_id)
    now = utc_now_iso()
    detection = detect_fraudulent_behavior(uid)
    signals = list((detection.get("meta") or {}).get("signals") or [])
    if reason and reason not in signals:
        signals.append(reason)
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT user_id FROM fraudulent_users WHERE user_id = ?",
            (uid,),
        ).fetchone()
        note = reason or (",".join(signals) if signals else "manual_mark")
        if existing:
            conn.execute(
                "UPDATE fraudulent_users SET marked_at = ?, reason = ? WHERE user_id = ?",
                (now, note, uid),
            )
        else:
            conn.execute(
                """
                INSERT INTO fraudulent_users (user_id, marked_at, reason)
                VALUES (?, ?, ?)
                """,
                (uid, now, note),
            )
        conn.execute(
            """
            INSERT INTO fraud_signals (user_id, signal, timestamp)
            VALUES (?, ?, ?)
            """,
            (uid, "marked_fraudulent", now),
        )
    return {
        "ok": True,
        "platform": "unified",
        "lane": "fraud",
        "title": "User Marked Fraudulent",
        "items": [{"user_id": uid, "marked_at": now, "signals": signals}],
        "count": 1,
        "meta": {"user_id": uid, "fraudulent": True, "reason": note},
    }

