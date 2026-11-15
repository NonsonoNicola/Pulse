from __future__ import annotations

import json
import zipfile
from datetime import date, datetime
from pathlib import Path

from app.analysis.service import AstronautSnapshot
from app.core.db import Database
from app.core.timeutil import iso, parse_iso


def generate_booklet(astronaut_id: str, snapshot: AstronautSnapshot, events: list[dict], db: Database) -> Path:
    from app.core.config import get_settings

    data_dir = get_settings().data_dir
    booklet_dir = data_dir / "booklet" / astronaut_id
    booklet_dir.mkdir(parents=True, exist_ok=True)
    (booklet_dir / "tests").mkdir(parents=True, exist_ok=True)
    (booklet_dir / "reports").mkdir(parents=True, exist_ok=True)
    (booklet_dir / "images").mkdir(parents=True, exist_ok=True)
    (booklet_dir / "audio").mkdir(parents=True, exist_ok=True)

    # profile.md
    profile_md = f"""# {snapshot.name} — {snapshot.role_title}

**ID:** {astronaut_id}
**Color:** {snapshot.color}
**Current Level:** {snapshot.level}
**Confidence:** {snapshot.confidence}
**Coverage (3d):** {snapshot.coverage:.0%}
**Last Computed:** {snapshot.computed_at}

## Baseline Summary
"""
    for metric, baseline in snapshot.baselines.items():
        profile_md += f"- **{metric}**: {baseline.center:.1f} ± {baseline.spread:.1f} ({baseline.origin}, n={baseline.n_obs}, frozen={baseline.frozen})\n"

    (booklet_dir / "profile.md").write_text(profile_md, encoding="utf-8")

    # timeline.md
    timeline_md = f"# Timeline — {snapshot.name}\n\n"
    for event in sorted(events, key=lambda e: e["measured_at"], reverse=True)[:100]:
        try:
            measured = parse_iso(event["measured_at"])
            recorded = parse_iso(event["recorded_at"])
        except Exception:
            continue
        timeline_md += f"- **{measured.strftime('%Y-%m-%d %H:%M')}** ({event['type']}) "
        if event["quality"] != "ok":
            timeline_md += f"⚠️ *{event['quality']}* "
        payload = event.get("payload", {})
        if isinstance(payload, str):
            import json
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        if payload:
            key_vals = ", ".join(f"{k}={v}" for k, v in list(payload.items())[:3])
            timeline_md += f"— {key_vals}"
        timeline_md += "\n"

    (booklet_dir / "timeline.md").write_text(timeline_md, encoding="utf-8")

    # tests/
    today = date.today()
    test_rows = db.query("SELECT * FROM tests WHERE astronaut_id = ? ORDER BY date DESC", (astronaut_id,))
    for row in test_rows:
        test_date = row["date"]
        test_name = row["test"]
        why_en, _, why_it = row["why"].partition("||")
        test_md = f"""# {test_name} — {test_date}

**Minutes:** {row['minutes']}
**Status:** {row['status']}
**Why (EN):** {why_en}
**Why (IT):** {why_it}
**Created:** {row['created_at']}
**Completed:** {row['completed_at'] or '—'}
"""
        (booklet_dir / "tests" / f"{test_date}_{test_name}.md").write_text(test_md, encoding="utf-8")

    # reports/
    status_md = f"""# Status Report — {snapshot.name} ({today.isoformat()})

**Level:** {snapshot.level}
**Confidence:** {snapshot.confidence}
**Primary Reason:** {snapshot.primary_reason}

## Reasons
"""
    for reason in snapshot.reasons:
        status_md += f"- **{reason.get('rule_id', 'unknown')}** ({reason.get('level', '?')}): {reason.get('explanation', '')}\n"

    status_md += "\n## Deviations\n"
    for dev in snapshot.deviations[:8]:
        status_md += f"- **{dev.metric}**: {dev.direction} ({dev.z:+.1f}σ)\n"

    (booklet_dir / "reports" / f"{today.isoformat()}_status.md").write_text(status_md, encoding="utf-8")

    # Create zip
    zip_path = data_dir / "booklet" / f"booklet_{astronaut_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in booklet_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(booklet_dir)
                zf.write(file, arcname)

    import logging
    logging.warning(f"Booklet generated at: {zip_path}, exists: {zip_path.exists()}")
    return zip_path