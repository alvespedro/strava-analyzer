from datetime import datetime, timedelta, timezone

from stravalib.client import Client

from domain.models import Activity, BestEffort, Gear, SegmentEffort, Split


def fetch_activities(access_token: str, days: int = 30) -> list[Activity]:
    client = Client(access_token=access_token)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    raw_activities = client.get_activities(after=cutoff, limit=200)

    activities = []
    for act in raw_activities:
        if str(act.type) != "Run":
            continue

        distance_km = float(act.distance) / 1000
        if distance_km < 0.1:
            continue

        activities.append(Activity(
            id=act.id,
            name=act.name,
            start_date=act.start_date_local.replace(tzinfo=timezone.utc),
            distance_km=round(distance_km, 3),
            moving_time_sec=int(act.moving_time.total_seconds()),
            elevation_gain_m=round(float(act.total_elevation_gain), 1),
            avg_heartrate=float(act.average_heartrate) if act.average_heartrate else None,
            max_heartrate=float(act.max_heartrate) if act.max_heartrate else None,
            avg_cadence=float(act.average_cadence) * 2 if act.average_cadence else None,
            trainer=bool(act.trainer),
            gear_id=str(act.gear_id) if act.gear_id else None,
            watts=float(act.average_watts) if act.average_watts else None,
            achievement_count=int(act.achievement_count or 0),
            pr_count=int(act.pr_count or 0),
        ))

    activities.sort(key=lambda a: a.start_date)
    return activities


def fetch_all_details(access_token: str, activities: list[Activity]) -> None:
    """Busca splits, best efforts e segmentos para cada atividade. Modifica in-place."""
    client = Client(access_token=access_token)
    for i, act in enumerate(activities, 1):
        print(f"  [{i}/{len(activities)}] {act.name[:40]}", end="\r")
        try:
            detail = client.get_activity(act.id)
            act.calories = float(detail.calories) if detail.calories else None

            # Splits por km
            act.splits = []
            for s in (detail.splits_metric or []):
                dist_km = float(s.distance) / 1000
                if dist_km < 0.05:
                    continue
                pace = (s.moving_time.total_seconds() / 60) / dist_km
                act.splits.append(Split(
                    split_number=s.split,
                    distance_km=round(dist_km, 3),
                    pace_min_per_km=pace,
                    avg_heartrate=float(s.average_heartrate) if s.average_heartrate else None,
                ))

            # Best efforts (apenas em atividades que tenham dados)
            act.best_efforts = []
            for be in (detail.best_efforts or []):
                act.best_efforts.append(BestEffort(
                    name=be.name,
                    distance_m=float(be.distance),
                    elapsed_sec=int(be.elapsed_time.total_seconds()),
                    pr_rank=be.pr_rank,
                ))

            # Segmentos (apenas outdoor; filtra os que têm PR ou top-10 por distância)
            act.segment_efforts = []
            if not act.trainer:
                for se in (detail.segment_efforts or []):
                    if se.pr_rank is not None:  # apenas segmentos com ranking registrado
                        act.segment_efforts.append(SegmentEffort(
                            name=se.name,
                            distance_m=float(se.distance),
                            elapsed_sec=int(se.elapsed_time.total_seconds()),
                            pr_rank=se.pr_rank,
                            avg_heartrate=float(se.average_heartrate) if se.average_heartrate else None,
                        ))
                # Ordena por PR rank (1 = melhor) e limita a 20
                act.segment_efforts.sort(key=lambda s: s.pr_rank or 999)
                act.segment_efforts = act.segment_efforts[:20]

        except Exception:
            pass
    print()


def resolve_gear_names(access_token: str, gear_ids: set[str]) -> dict[str, Gear]:
    """Resolve IDs de gear para objetos Gear. 1 call por ID único."""
    client = Client(access_token=access_token)
    result = {}
    for gear_id in gear_ids:
        try:
            g = client.get_gear(gear_id)
            result[gear_id] = Gear(
                id=gear_id,
                name=g.name,
                total_distance_km=round(float(g.distance) / 1000, 1),
                primary=bool(g.primary),
            )
        except Exception:
            pass
    return result
