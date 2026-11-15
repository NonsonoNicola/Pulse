from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = REPO_ROOT / "config"
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    mission_id: str
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    llm_timeout_s: float
    ground_base_url: str
    session_days: int
    quiet_hours_start: int
    quiet_hours_end: int

    @property
    def db_path(self) -> Path:
        return self.data_dir / "crewmd.db"

    @property
    def ground_db_path(self) -> Path:
        return self.data_dir / "ground.db"

    @property
    def booklet_dir(self) -> Path:
        return self.data_dir / "booklet"

    @property
    def mission_path(self) -> Path:
        return CONFIG_DIR / "missions" / f"{self.mission_id}.yaml"

    @property
    def baseline_tmp_dir(self) -> Path:
        return self.data_dir / "tmp"


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("CREWMD_DATA_DIR", REPO_ROOT / "data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "booklet").mkdir(parents=True, exist_ok=True)
    return Settings(
        repo_root=REPO_ROOT,
        data_dir=data_dir,
        mission_id=os.environ.get("CREWMD_MISSION", "leo_station"),
        llm_base_url=os.environ.get("CREWMD_LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
        llm_model=os.environ.get("CREWMD_LLM_MODEL", "medgemma:4b"),
        llm_api_key=os.environ.get("CREWMD_LLM_API_KEY", "local"),
        llm_timeout_s=float(os.environ.get("CREWMD_LLM_TIMEOUT", "45")),
        ground_base_url=os.environ.get("CREWMD_GROUND_URL", "http://127.0.0.1:8001"),
        session_days=int(os.environ.get("CREWMD_SESSION_DAYS", "30")),
        quiet_hours_start=int(os.environ.get("CREWMD_QUIET_START", "22")),
        quiet_hours_end=int(os.environ.get("CREWMD_QUIET_END", "7")),
    )


@lru_cache(maxsize=1)
def load_thresholds() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "thresholds.yaml")


@lru_cache(maxsize=1)
def load_symptoms() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "symptoms.yaml")


@lru_cache(maxsize=1)
def load_critical_phrases() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "rules" / "critical_phrases.yaml")


@lru_cache(maxsize=1)
def load_inventory() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "inventory.yaml")


@lru_cache(maxsize=1)
def load_gamification() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "gamification.yaml")


@lru_cache(maxsize=8)
def load_mission(mission_id: str) -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "missions" / f"{mission_id}.yaml")


@lru_cache(maxsize=1)
def load_signatures() -> list[dict[str, Any]]:
    return load_yaml(KNOWLEDGE_DIR / "signatures" / "signatures.yaml").get("signatures", [])


@lru_cache(maxsize=1)
def load_rules() -> list[dict[str, Any]]:
    return load_yaml(CONFIG_DIR / "rules" / "vitals.yaml").get("rules", [])


def mission_summary(mission_id: str) -> dict[str, Any]:
    mission = load_mission(mission_id)
    return {
        "id": mission.get("id", mission_id),
        "name": mission.get("name", mission_id),
        "habitat": mission.get("habitat", ""),
        "description": mission.get("description", ""),
        "gravity": mission.get("gravity", ""),
        "radiation": mission.get("radiation", ""),
        "environmental_risks": mission.get("environmental_risks", []),
        "medical_resources": mission.get("medical_resources", []),
        "link": mission.get("link", {}),
    }
