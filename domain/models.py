from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Split:
    split_number: int
    distance_km: float
    pace_min_per_km: float
    avg_heartrate: float | None


@dataclass
class Gear:
    id: str
    name: str
    total_distance_km: float
    primary: bool


@dataclass
class GearUsage:
    gear: Gear
    run_count: int
    total_km: float


@dataclass
class BestEffort:
    name: str          # "400m", "1K", "5K", "10K", "Half-Marathon", etc.
    distance_m: float
    elapsed_sec: int
    pr_rank: int | None  # 1 = PR pessoal


@dataclass
class SegmentEffort:
    name: str
    distance_m: float
    elapsed_sec: int
    pr_rank: int | None
    avg_heartrate: float | None

    @property
    def pace_min_per_km(self) -> float:
        return (self.elapsed_sec / 60) / (self.distance_m / 1000)

    @property
    def pace_formatted(self) -> str:
        p = self.pace_min_per_km
        return f"{int(p)}:{int((p % 1) * 60):02d}"


@dataclass
class Activity:
    id: int
    name: str
    start_date: datetime
    distance_km: float
    moving_time_sec: int
    elevation_gain_m: float
    avg_heartrate: float | None
    max_heartrate: float | None
    avg_cadence: float | None
    trainer: bool = False
    gear_id: str | None = None
    watts: float | None = None
    achievement_count: int = 0
    pr_count: int = 0
    calories: float | None = None
    splits: list[Split] = field(default_factory=list)
    best_efforts: list[BestEffort] = field(default_factory=list)
    segment_efforts: list[SegmentEffort] = field(default_factory=list)

    @property
    def pace_min_per_km(self) -> float:
        return (self.moving_time_sec / 60) / self.distance_km

    @property
    def duration_formatted(self) -> str:
        h = self.moving_time_sec // 3600
        m = (self.moving_time_sec % 3600) // 60
        s = self.moving_time_sec % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @property
    def pace_formatted(self) -> str:
        total_min = self.pace_min_per_km
        m = int(total_min)
        s = int((total_min - m) * 60)
        return f"{m}:{s:02d}"


@dataclass
class Stats:
    total_runs: int
    total_distance_km: float
    total_time_sec: int
    avg_pace_min_per_km: float
    avg_heartrate: float | None
    avg_cadence: float | None
    longest_run: Activity
    fastest_run: Activity
    highest_elevation_run: Activity
    highest_hr_run: Activity | None
    pace_trend: str
    pace_slope: float
    pace_first: float
    pace_last: float
    weeks: dict
    trainer_runs: int
    outdoor_runs: int
    gear_usage: list[GearUsage]
    total_achievements: int
    total_prs: int
    avg_watts: float | None
    watts_trend: str | None
    watts_slope: float | None


@dataclass
class Projection:
    distance_km: float
    projected_time_sec: float
    pace_min_per_km: float
    based_on: Activity
    source: str = "riegel"  # "best_effort" | "riegel"

    @property
    def time_formatted(self) -> str:
        sec = int(self.projected_time_sec)
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @property
    def pace_formatted(self) -> str:
        m = int(self.pace_min_per_km)
        s = int((self.pace_min_per_km - m) * 60)
        return f"{m}:{s:02d}"

    @property
    def label(self) -> str:
        labels = {5.0: "5 km", 10.0: "10 km", 21.097: "Meia Maratona", 42.195: "Maratona"}
        return labels.get(self.distance_km, f"{self.distance_km:.1f} km")


@dataclass
class Report:
    athlete_name: str
    generated_at: datetime
    period_days: int
    period_start: datetime
    period_end: datetime
    activities: list[Activity]
    stats: Stats
    projections: list[Projection]
    gear_map: dict[str, Gear]
