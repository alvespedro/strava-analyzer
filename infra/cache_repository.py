import json
import time
from datetime import datetime, timezone
from pathlib import Path

from domain.models import Activity, BestEffort, Gear, SegmentEffort, Split

CACHE_FILE = Path("token.json")


class CacheRepository:
    def save_token(self, token_data: dict) -> None:
        current = self._load_raw()
        current.update(token_data)
        self._write(current)

    def load_token(self) -> dict | None:
        raw = self._load_raw()
        if not raw.get("access_token"):
            return None
        return {
            "access_token": raw["access_token"],
            "refresh_token": raw["refresh_token"],
            "expires_at": raw["expires_at"],
            "athlete_id": raw.get("athlete_id"),
        }

    def save_activities(self, activities: list[Activity]) -> None:
        raw = self._load_raw()
        raw["cached_at"] = int(time.time())
        raw["cached_activities"] = [self._activity_to_dict(a) for a in activities]
        self._write(raw)

    def load_activities(self) -> list[Activity] | None:
        raw = self._load_raw()
        if "cached_activities" not in raw:
            return None
        return [self._dict_to_activity(d) for d in raw["cached_activities"]]

    def save_gear_map(self, gear_map: dict[str, Gear]) -> None:
        raw = self._load_raw()
        raw["cached_gear"] = {k: self._gear_to_dict(v) for k, v in gear_map.items()}
        self._write(raw)

    def load_gear_map(self) -> dict[str, Gear]:
        raw = self._load_raw()
        cached = raw.get("cached_gear", {})
        return {k: self._dict_to_gear(v) for k, v in cached.items()}

    def is_cache_valid(self, max_age_hours: int = 24) -> bool:
        raw = self._load_raw()
        cached_at = raw.get("cached_at")
        if not cached_at or "cached_activities" not in raw:
            return False
        return (time.time() - cached_at) < max_age_hours * 3600

    def _load_raw(self) -> dict:
        if not CACHE_FILE.exists():
            return {}
        with open(CACHE_FILE) as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _activity_to_dict(self, a: Activity) -> dict:
        return {
            "id": a.id,
            "name": a.name,
            "start_date": a.start_date.isoformat(),
            "distance_km": a.distance_km,
            "moving_time_sec": a.moving_time_sec,
            "elevation_gain_m": a.elevation_gain_m,
            "avg_heartrate": a.avg_heartrate,
            "max_heartrate": a.max_heartrate,
            "avg_cadence": a.avg_cadence,
            "trainer": a.trainer,
            "gear_id": a.gear_id,
            "watts": a.watts,
            "achievement_count": a.achievement_count,
            "pr_count": a.pr_count,
            "calories": a.calories,
            "splits": [
                {"split_number": s.split_number, "distance_km": s.distance_km,
                 "pace_min_per_km": s.pace_min_per_km, "avg_heartrate": s.avg_heartrate}
                for s in a.splits
            ],
            "best_efforts": [
                {"name": be.name, "distance_m": be.distance_m,
                 "elapsed_sec": be.elapsed_sec, "pr_rank": be.pr_rank}
                for be in a.best_efforts
            ],
            "segment_efforts": [
                {"name": se.name, "distance_m": se.distance_m, "elapsed_sec": se.elapsed_sec,
                 "pr_rank": se.pr_rank, "avg_heartrate": se.avg_heartrate}
                for se in a.segment_efforts
            ],
        }

    def _dict_to_activity(self, d: dict) -> Activity:
        return Activity(
            id=d["id"],
            name=d["name"],
            start_date=datetime.fromisoformat(d["start_date"]),
            distance_km=d["distance_km"],
            moving_time_sec=d["moving_time_sec"],
            elevation_gain_m=d["elevation_gain_m"],
            avg_heartrate=d.get("avg_heartrate"),
            max_heartrate=d.get("max_heartrate"),
            avg_cadence=d.get("avg_cadence"),
            trainer=d.get("trainer", False),
            gear_id=d.get("gear_id"),
            watts=d.get("watts"),
            achievement_count=d.get("achievement_count", 0),
            pr_count=d.get("pr_count", 0),
            calories=d.get("calories"),
            splits=[Split(**s) for s in d.get("splits", [])],
            best_efforts=[BestEffort(**be) for be in d.get("best_efforts", [])],
            segment_efforts=[SegmentEffort(**se) for se in d.get("segment_efforts", [])],
        )

    def _gear_to_dict(self, g: Gear) -> dict:
        return {"id": g.id, "name": g.name, "total_distance_km": g.total_distance_km, "primary": g.primary}

    def _dict_to_gear(self, d: dict) -> Gear:
        return Gear(**d)
