from __future__ import annotations

from app.core.config import get_settings
from app.core.db import Database
from app.events.schemas import EventIn
from app.events.store import EventStore
from app.core.timeutil import utcnow
from app.core.security import hash_password, verify_password
from app.analysis.service import AnalysisService


def test_idempotency():
    """Test that events with same idempotency_key are not duplicated."""
    settings = get_settings()
    db = Database(settings.db_path)
    store = EventStore(db)
    
    # First insert
    event1 = EventIn(
        idempotency_key="test:idempotency:123",
        astronaut_id="astronaut_01",
        type="vital_sample",
        measured_at=utcnow(),
        source="sensor",
        payload={"resting_hr": 70},
    )
    record1, created1 = store.append(event1)
    assert created1 is True
    
    # Second insert with SAME idempotency_key but DIFFERENT id (new EventIn object)
    event2 = EventIn(
        idempotency_key="test:idempotency:123",
        astronaut_id="astronaut_01",
        type="vital_sample",
        measured_at=utcnow(),
        source="sensor",
        payload={"resting_hr": 70},
    )
    record2, created2 = store.append(event2)
    assert created2 is False, f"Expected created2=False, got {created2}"
    assert record1["id"] == record2["id"], f"IDs should match: {record1['id']} vs {record2['id']}"
    
    # Verify only one event in database
    count = db.query_one("SELECT COUNT(*) as c FROM events WHERE idempotency_key = ?", ("test:idempotency:123",))
    assert count["c"] == 1
    
    db.close()
    print("✓ Idempotency test passed")


def test_backfill_equivalence():
    """Test that backfilled data produces same analysis as original."""
    from app.sim.seed import seed
    from app.sim.sensors import generate_backfill
    from app.core.timeutil import utcnow
    from app.analysis.service import AnalysisService
    from app.events.store import EventStore
    
    settings = get_settings()
    seed(reset=True)
    db = Database(settings.db_path)
    analysis = AnalysisService(db, settings)
    store = EventStore(db)
    
    # Get initial Luca status (gray due to gap)
    bundle = analysis.bundle("en")
    luca_initial = bundle.snapshot("astronaut_03")
    assert luca_initial.level == "gray"
    assert luca_initial.coverage < 0.4
    
    # Backfill the missing days
    now = utcnow()
    from app.sim.sensors import generate_backfill
    backfill_events = generate_backfill("astronaut_03", [1, 2, 3], now)
    store.append_many(backfill_events)
    analysis.invalidate()
    
    # Get Luca status after backfill
    bundle = analysis.bundle("en")
    luca_after = bundle.snapshot("astronaut_03")
    
    # Should now be yellow with high coverage
    assert luca_after.level == "yellow"
    assert luca_after.coverage > 0.8
    assert luca_after.backfilled_recent
    
    db.close()
    print("✓ Backfill equivalence test passed")


def test_rule_tables():
    """Test that rule engine produces expected alerts."""
    from app.rules.engine import evaluate_rules
    from app.analysis.features import build_daily_features, env_daily_features
    from app.analysis.baseline import compute_baselines
    from app.core.config import load_rules, load_thresholds
    from app.core.timeutil import utcnow
    from datetime import date, timedelta
    
    settings = get_settings()
    db = Database(settings.db_path)
    from app.events.store import EventStore
    store = EventStore(db)
    events = store.list(limit=5000)
    
    today = date.today()
    frames = {
        "astronaut_01": build_daily_features(events, end=today, days=60, astronaut_id="astronaut_01"),
        "astronaut_02": build_daily_features(events, end=today, days=60, astronaut_id="astronaut_02"),
        "astronaut_03": build_daily_features(events, end=today, days=60, astronaut_id="astronaut_03"),
        "astronaut_04": build_daily_features(events, end=today, days=60, astronaut_id="astronaut_04"),
    }
    env_frame = env_daily_features(events, end=today, days=60)
    
    baselines = {}
    for aid, frame in frames.items():
        baselines[aid] = compute_baselines(frame)
    
    rules = load_rules()
    hits = evaluate_rules(rules, frames, baselines, env_frame, events, locale="en")
    
    # CO2 should be orange
    co2_hits = [h for h in hits if h.rule_id == "rule_co2_elevated"]
    assert len(co2_hits) == 1
    assert co2_hits[0].level == "orange"
    
    # Sleep deprivation for all should be yellow
    sleep_hits = [h for h in hits if h.rule_id == "rule_sleep_deprivation"]
    assert len(sleep_hits) == 4  # All 4 astronauts
    for h in sleep_hits:
        assert h.level == "yellow"
    
    db.close()
    print("✓ Rule tables test passed")


def test_password_hashing():
    """Test PBKDF2 password hashing and verification."""
    password = "test_password_123"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False
    assert verify_password("", hashed) is False
    
    # Hash should be deterministic with same salt? No, salt is random
    # But format should be correct
    parts = hashed.split("$")
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) == 210_000
    assert len(parts[2]) == 32  # 16 bytes hex
    assert len(parts[3]) == 64  # 32 bytes hex
    
    print("✓ Password hashing test passed")


def test_event_append_only():
    """Test that events table is append-only (no UPDATE/DELETE)."""
    settings = get_settings()
    db = Database(settings.db_path)
    
    # Try to update an event - should fail
    event_id = db.query_one("SELECT id FROM events LIMIT 1")["id"]
    try:
        db.execute("UPDATE events SET payload = '{}' WHERE id = ?", (event_id,))
        assert False, "UPDATE should have been blocked by trigger"
    except Exception as e:
        assert "append-only" in str(e)
    
    # Try to delete an event - should fail
    try:
        db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        assert False, "DELETE should have been blocked by trigger"
    except Exception as e:
        assert "append-only" in str(e)
    
    db.close()
    print("✓ Event append-only test passed")


if __name__ == "__main__":
    test_idempotency()
    test_backfill_equivalence()
    test_rule_tables()
    test_password_hashing()
    test_event_append_only()
    print("\n✅ All core tests passed!")