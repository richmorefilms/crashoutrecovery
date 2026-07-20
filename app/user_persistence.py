"""Map localStorage crashout_* blobs <-> structured SQLite tables."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.db import get_conn, utc_now_iso


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def load_recovery(user_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT streak_days, last_win_date, spike_history, tones, wins,
                   last_safe_move, last_safe_at
            FROM recovery WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return {
            "streak": 0,
            "lastWinDate": None,
            "history": [],
            "tones": [],
            "wins": 0,
            "lastSafeMove": None,
            "lastSafeAt": None,
        }
    return {
        "streak": int(row["streak_days"] or 0),
        "lastWinDate": row["last_win_date"],
        "history": _loads(row["spike_history"], []),
        "tones": _loads(row["tones"], []),
        "wins": int(row["wins"] or 0),
        "lastSafeMove": row["last_safe_move"],
        "lastSafeAt": row["last_safe_at"],
    }


def save_recovery(user_id: int, data: dict[str, Any] | None) -> None:
    data = data or {}
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO recovery (
                user_id, streak_days, last_win_date, spike_history, tones,
                wins, last_safe_move, last_safe_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                streak_days = excluded.streak_days,
                last_win_date = excluded.last_win_date,
                spike_history = excluded.spike_history,
                tones = excluded.tones,
                wins = excluded.wins,
                last_safe_move = excluded.last_safe_move,
                last_safe_at = excluded.last_safe_at
            """,
            (
                user_id,
                int(data.get("streak") or 0),
                data.get("lastWinDate"),
                _dumps(data.get("history") or []),
                _dumps(data.get("tones") or []),
                int(data.get("wins") or 0),
                data.get("lastSafeMove"),
                data.get("lastSafeAt"),
            ),
        )


def load_seeds(user_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT content, tone, created_at
            FROM seeds WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 40
            """,
            (user_id,),
        ).fetchall()
    return [
        {
            "seed": row["content"],
            "tone": row["tone"],
            "savedAt": row["created_at"],
        }
        for row in rows
    ]


def save_seeds(user_id: int, items: list[Any] | None) -> None:
    items = items or []
    with get_conn() as conn:
        conn.execute("DELETE FROM seeds WHERE user_id = ?", (user_id,))
        for item in items[:40]:
            if isinstance(item, str):
                content, tone, created = item, None, utc_now_iso()
            else:
                content = (item or {}).get("seed") or (item or {}).get("content") or ""
                tone = (item or {}).get("tone")
                created = (item or {}).get("savedAt") or (item or {}).get("created_at") or utc_now_iso()
            if not content:
                continue
            conn.execute(
                """
                INSERT INTO seeds (user_id, content, tone, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, content, tone, created),
            )


def load_market_packs(user_id: int) -> dict[str, list[Any]]:
    bundle: dict[str, list[Any]] = {"tone": [], "cta": [], "seed": []}
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT pack_name, pack_type, pack_payload, installed_at
            FROM market_packs WHERE user_id = ?
            ORDER BY datetime(installed_at) ASC, id ASC
            """,
            (user_id,),
        ).fetchall()
    for row in rows:
        payload = _loads(row["pack_payload"], None)
        pack_type = row["pack_type"] or "tone"
        if pack_type not in bundle:
            bundle[pack_type] = []
        if isinstance(payload, dict):
            entry = {**payload}
            entry.setdefault("id", row["pack_name"])
            entry.setdefault("installedAt", row["installed_at"])
            bundle[pack_type].append(entry)
        else:
            bundle[pack_type].append(
                {
                    "id": row["pack_name"],
                    "title": row["pack_name"],
                    "installedAt": row["installed_at"],
                }
            )
    return bundle


def save_market_packs(user_id: int, data: dict[str, Any] | None) -> None:
    data = data or {}
    with get_conn() as conn:
        conn.execute("DELETE FROM market_packs WHERE user_id = ?", (user_id,))
        for pack_type in ("tone", "cta", "seed"):
            for pack in data.get(pack_type) or []:
                if not isinstance(pack, dict):
                    continue
                pack_name = str(pack.get("id") or pack.get("title") or "")
                if not pack_name:
                    continue
                conn.execute(
                    """
                    INSERT INTO market_packs (user_id, pack_name, pack_type, pack_payload, installed_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, pack_name) DO UPDATE SET
                        pack_type = excluded.pack_type,
                        pack_payload = excluded.pack_payload,
                        installed_at = excluded.installed_at
                    """,
                    (
                        user_id,
                        pack_name,
                        pack_type,
                        _dumps(pack),
                        pack.get("installedAt") or utc_now_iso(),
                    ),
                )


def load_world_signals(user_id: int) -> dict[str, Any]:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT signal_date, signals, forecast
            FROM world_signals
            WHERE user_id = ?
            ORDER BY signal_date DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return {"today": [], "forecast": [], "burnout": [], "algoTip": "", "signalDate": today}
    signals = _loads(row["signals"], {})
    if not isinstance(signals, dict):
        signals = {"today": signals}
    return {
        "today": signals.get("today") or [],
        "forecast": _loads(row["forecast"], []),
        "burnout": signals.get("burnout") or [],
        "algoTip": signals.get("algoTip") or "",
        "signalDate": row["signal_date"],
    }


def save_world_signals(user_id: int, data: dict[str, Any] | None) -> None:
    data = data or {}
    signal_date = data.get("signalDate") or date.today().isoformat()
    signals_blob = {
        "today": data.get("today") or [],
        "burnout": data.get("burnout") or [],
        "algoTip": data.get("algoTip") or "",
    }
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO world_signals (user_id, signal_date, signals, forecast)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, signal_date) DO UPDATE SET
                signals = excluded.signals,
                forecast = excluded.forecast
            """,
            (
                user_id,
                signal_date,
                _dumps(signals_blob),
                _dumps(data.get("forecast") or []),
            ),
        )


def load_bundle(user_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        user = conn.execute(
            "SELECT tier FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        legacy = conn.execute(
            "SELECT data_key, value_json FROM user_data WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    recovery = load_recovery(user_id)
    seeds = load_seeds(user_id)
    packs = load_market_packs(user_id)
    signals = load_world_signals(user_id)

    # One-time lift from older blob table if structured rows are empty
    if legacy and recovery.get("wins", 0) == 0 and not seeds:
        blob: dict[str, Any] = {}
        for row in legacy:
            try:
                blob[row["data_key"]] = json.loads(row["value_json"])
            except json.JSONDecodeError:
                continue
        if blob:
            save_bundle(user_id, blob)
            recovery = load_recovery(user_id)
            seeds = load_seeds(user_id)
            packs = load_market_packs(user_id)
            signals = load_world_signals(user_id)
            with get_conn() as conn:
                user = conn.execute(
                    "SELECT tier FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()

    return {
        "crashout_recovery": recovery,
        "crashout_seeds": seeds,
        "crashout_market_packs": packs,
        "crashout_world_signals": signals,
        "tier": (user["tier"] if user else None) or "basic",
    }


def save_bundle(user_id: int, data: dict[str, Any]) -> None:
    if "crashout_recovery" in data:
        save_recovery(user_id, data.get("crashout_recovery"))
    if "crashout_seeds" in data:
        save_seeds(user_id, data.get("crashout_seeds"))
    if "crashout_market_packs" in data:
        save_market_packs(user_id, data.get("crashout_market_packs"))
    if "crashout_world_signals" in data:
        save_world_signals(user_id, data.get("crashout_world_signals"))
    # Intentionally ignore client "tier" writes — tier is server-controlled.
