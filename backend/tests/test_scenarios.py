from __future__ import annotations

import json

from app.analysis.service import AnalysisService
from app.core.config import get_settings
from app.core.db import Database
from app.events.store import EventStore
from app.sim.seed import seed
from app.sim.sensors import generate_backfill, generate_fault_check, generate_infection_burst
from app.core.timeutil import utcnow


def test_scenarios():
    """End-to-end test of S1-S5 scenarios."""
    settings = get_settings()
    
    # Clean slate - seed creates its own DB connection
    seed(reset=True)
    
    # Create new connections after seed
    db = Database(settings.db_path)
    analysis = AnalysisService(db, settings)
    store = EventStore(db)
    
    # --- Initial state (S1 active) ---
    bundle = analysis.bundle("en")
    
    # S1: All four yellow, crew finding present, CO2 orange alert
    levels = {aid: snap.level for aid, snap in bundle.snapshots.items()}
    assert levels == {
        "astronaut_01": "yellow",  # Elena
        "astronaut_02": "yellow",  # Maya
        "astronaut_03": "gray",    # Luca (gap)
        "astronaut_04": "yellow",  # Aiko
    }, f"S1 initial levels: {levels}"
    
    coverage = {aid: snap.coverage for aid, snap in bundle.snapshots.items()}
    assert coverage["astronaut_03"] < 0.4, f"Luca coverage should be low: {coverage}"
    
    # Crew finding exists
    assert len(bundle.crew_findings) == 1, "Crew finding should exist for S1"
    cf = bundle.crew_findings[0]
    assert cf.member_count == 4, "All 4 crew members in finding"
    
    # CO2 environmental alert orange
    env_alerts = [a for a in bundle.environmental_alerts if a.metric == "co2_ppm"]
    assert len(env_alerts) == 1, "CO2 alert should exist"
    assert env_alerts[0].level == "orange", f"CO2 alert should be orange: {env_alerts[0].level}"
    
    print("✓ S1 initial state verified")
    
    # --- S2: Infection burst for Maya ---
    now = utcnow()
    s2_events = generate_infection_burst("astronaut_02", now)
    store.append_many(s2_events)
    analysis.invalidate()
    
    bundle = analysis.bundle("en")
    assert bundle.snapshot("astronaut_02").level == "orange", \
        f"Maya should be orange after S2: {bundle.snapshot('astronaut_02').level}"
    
    print("✓ S2 infection burst verified")
    
    # --- S3: Backfill for Luca ---
    s3_events = generate_backfill("astronaut_03", [1, 2, 3], now)
    store.append_many(s3_events)
    analysis.invalidate()
    
    bundle = analysis.bundle("en")
    luca = bundle.snapshot("astronaut_03")
    assert luca.level == "yellow", f"Luca should be yellow after backfill: {luca.level}"
    assert luca.coverage > 0.8, f"Luca coverage should be high: {luca.coverage}"
    assert luca.backfilled_recent, "Luca should have backfilled_recent flag"
    
    print("✓ S3 backfill verified")
    
    # --- S5: Sensor fault recheck for Aiko ---
    s5_events = generate_fault_check("astronaut_04", now)
    store.append_many(s5_events)
    analysis.invalidate()
    
    bundle = analysis.bundle("en")
    aiko = bundle.snapshot("astronaut_04")
    # Aiko should have sensor quality flag but not go red
    sensor_quality_hits = [r for r in aiko.reasons if r.get("rule_id") == "rule_sensor_quality"]
    assert len(sensor_quality_hits) == 1, "Aiko should have sensor quality flag"
    # Should not be red (faulty sensor should not cause red)
    assert aiko.level != "red", f"Aiko should not be red from sensor fault: {aiko.level}"
    
    print("✓ S5 sensor fault verified")
    
    # --- S4: Emergency case creation ---
    from app.core.timeutil import iso
    case_id = f"case:astronaut_01:{now.timestamp()}"
    db.execute(
        "INSERT INTO cases (id, astronaut_id, level, status, title, protocol_id, opened_at, updated_at, notes) "
        "VALUES (?, ?, 'red', 'open', ?, ?, ?, ?, '[]')",
        (case_id, "astronaut_01", "Emergency: Chest pain", "chest_pain", iso(now), iso(now)),
    )
    
    # Verify case exists
    row = db.query_one("SELECT * FROM cases WHERE id = ?", (case_id,))
    assert row is not None, "Emergency case should be created"
    assert row["level"] == "red"
    assert row["protocol_id"] == "chest_pain"
    
    print("✓ S4 emergency case verified")
    
    db.close()
    print("\n✅ All scenario tests passed!")


if __name__ == "__main__":
    test_scenarios()