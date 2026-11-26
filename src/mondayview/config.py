"""Load config files. Paths are relative to the repo root."""
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def _load(name):
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf-8"))


def settings():
    return _load("settings.yaml")


def families():
    return _load("families.yaml")


def taxonomy():
    return _load("taxonomy.yaml")["areas"]
