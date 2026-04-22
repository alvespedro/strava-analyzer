import statistics
from collections import defaultdict
from datetime import datetime, timedelta

from domain.models import Activity, BestEffort, Gear, GearUsage, Projection, Split, Stats


def _format_week_label(week_start: datetime) -> str:
    week_end = week_start + timedelta(days=6)
    return f"{week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')}"


def calculate_pace_trend(activities: list[Activity]) -> tuple[str, float, float, float]:
    """
    Regressão linear sobre pace (min/km) vs índice de corrida.
    Slope negativo = ficando mais rápido.
    Retorna (trend, slope, pace_first, pace_last).
    """
    sorted_acts = sorted(activities, key=lambda a: a.start_date)
    x = list(range(len(sorted_acts)))
    y = [a.pace_min_per_km for a in sorted_acts]

    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
    den = sum((xi - mean_x) ** 2 for xi in x)
    slope = num / den if den != 0 else 0.0

    THRESHOLD = 0.02
    trend = "improving" if slope < -THRESHOLD else "regressing" if slope > THRESHOLD else "stable"
    return trend, slope, y[0], y[-1]


def calculate_watts_trend(activities: list[Activity]) -> tuple[str, float]:
    """
    Regressão linear sobre watts vs índice de corrida.
    Slope positivo = ficando mais forte.
    Retorna (trend, slope).
    """
    sorted_acts = sorted(activities, key=lambda a: a.start_date)
    acts_with_watts = [a for a in sorted_acts if a.watts]
    if len(acts_with_watts) < 3:
        return "stable", 0.0

    x = list(range(len(acts_with_watts)))
    y = [a.watts for a in acts_with_watts]

    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
    den = sum((xi - mean_x) ** 2 for xi in x)
    slope = num / den if den != 0 else 0.0

    THRESHOLD = 0.5
    trend = "improving" if slope > THRESHOLD else "regressing" if slope < -THRESHOLD else "stable"
    return trend, slope


def riegel_projection(baseline: Activity, target_km: float) -> Projection | None:
    """
    T2 = T1 * (D2/D1)^1.06
    Retorna None se baseline < 30% do target (projeção pouco confiável).
    """
    if baseline.distance_km < target_km * 0.3:
        return None
    projected_sec = baseline.moving_time_sec * (target_km / baseline.distance_km) ** 1.06
    return Projection(
        distance_km=target_km,
        projected_time_sec=projected_sec,
        pace_min_per_km=(projected_sec / 60) / target_km,
        based_on=baseline,
    )


def _best_effort_for_distance(activities: list[Activity], distance_m: float) -> BestEffort | None:
    """Retorna o melhor tempo registrado para uma distância padrão em todas as atividades."""
    candidates = []
    for act in activities:
        for be in act.best_efforts:
            if abs(be.distance_m - distance_m) < 50:  # tolerância de 50m
                candidates.append((be, act))
    if not candidates:
        return None
    best_be, _ = min(candidates, key=lambda x: x[0].elapsed_sec)
    return best_be


def compute_projections(activities: list[Activity]) -> list[Projection]:
    """
    Sistema híbrido: usa best efforts diretos quando disponíveis,
    cai no Riegel com o longão como baseline para distâncias sem dados.
    """
    TARGETS_KM = [5.0, 10.0, 21.097, 42.195]
    TARGETS_M = {5.0: 5000, 10.0: 10000, 21.097: 21097, 42.195: 42195}

    riegel_baseline = max(activities, key=lambda a: a.distance_km)
    projections = []

    for target_km in TARGETS_KM:
        be = _best_effort_for_distance(activities, TARGETS_M[target_km])
        if be:
            # Fonte direta: best effort registrado pelo Strava
            pace = (be.elapsed_sec / 60) / target_km
            # Encontrar a atividade dona desse best effort para popular based_on
            act_owner = next(
                (a for a in activities if any(
                    abs(b.distance_m - TARGETS_M[target_km]) < 50 and b.elapsed_sec == be.elapsed_sec
                    for b in a.best_efforts
                )),
                riegel_baseline,
            )
            projections.append(Projection(
                distance_km=target_km,
                projected_time_sec=float(be.elapsed_sec),
                pace_min_per_km=pace,
                based_on=act_owner,
                source="best_effort",
            ))
        else:
            p = riegel_projection(riegel_baseline, target_km)
            if p:
                projections.append(p)

    return projections


def _group_by_week(activities: list[Activity]) -> dict:
    weeks: dict[datetime, list[Activity]] = defaultdict(list)
    for act in activities:
        monday = act.start_date - timedelta(days=act.start_date.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        weeks[monday].append(act)
    result = {}
    for monday in sorted(weeks.keys()):
        acts = weeks[monday]
        hr_values = [a.avg_heartrate for a in acts if a.avg_heartrate]
        result[_format_week_label(monday)] = {
            "runs": len(acts),
            "distance_km": round(sum(a.distance_km for a in acts), 2),
            "avg_pace": statistics.mean(a.pace_min_per_km for a in acts),
            "avg_hr": round(statistics.mean(hr_values), 1) if hr_values else None,
        }
    return result


def _build_gear_usage(activities: list[Activity], gear_map: dict[str, Gear]) -> list[GearUsage]:
    gear_groups: dict[str, list[Activity]] = defaultdict(list)
    for a in activities:
        if a.gear_id:
            gear_groups[a.gear_id].append(a)
    usage = []
    for gear_id, acts in gear_groups.items():
        gear = gear_map.get(gear_id)
        if not gear:
            continue
        usage.append(GearUsage(
            gear=gear,
            run_count=len(acts),
            total_km=round(sum(a.distance_km for a in acts), 2),
        ))
    return sorted(usage, key=lambda u: u.total_km, reverse=True)


def compute_stats(activities: list[Activity], gear_map: dict[str, Gear]) -> Stats:
    hr_values = [a.avg_heartrate for a in activities if a.avg_heartrate]
    cadence_values = [a.avg_cadence for a in activities if a.avg_cadence]
    watts_values = [a.watts for a in activities if a.watts]

    trend, slope, pace_first, pace_last = calculate_pace_trend(activities)

    if len(watts_values) >= 3:
        watts_trend, watts_slope = calculate_watts_trend(activities)
        avg_watts = round(statistics.mean(watts_values), 1)
    else:
        watts_trend, watts_slope, avg_watts = None, None, None

    return Stats(
        total_runs=len(activities),
        total_distance_km=round(sum(a.distance_km for a in activities), 2),
        total_time_sec=sum(a.moving_time_sec for a in activities),
        avg_pace_min_per_km=statistics.mean(a.pace_min_per_km for a in activities),
        avg_heartrate=round(statistics.mean(hr_values), 1) if hr_values else None,
        avg_cadence=round(statistics.mean(cadence_values), 1) if cadence_values else None,
        longest_run=max(activities, key=lambda a: a.distance_km),
        fastest_run=min(activities, key=lambda a: a.pace_min_per_km),
        highest_elevation_run=max(activities, key=lambda a: a.elevation_gain_m),
        highest_hr_run=max((a for a in activities if a.max_heartrate), key=lambda a: a.max_heartrate, default=None),
        pace_trend=trend,
        pace_slope=slope,
        pace_first=pace_first,
        pace_last=pace_last,
        weeks=_group_by_week(activities),
        trainer_runs=sum(1 for a in activities if a.trainer),
        outdoor_runs=sum(1 for a in activities if not a.trainer),
        gear_usage=_build_gear_usage(activities, gear_map),
        total_achievements=sum(a.achievement_count for a in activities),
        total_prs=sum(a.pr_count for a in activities),
        avg_watts=avg_watts,
        watts_trend=watts_trend,
        watts_slope=watts_slope,
    )
