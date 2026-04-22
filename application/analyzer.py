from datetime import datetime, timedelta, timezone

from domain.calculators import compute_stats, compute_projections
from domain.models import Report
from infra.cache_repository import CacheRepository
from infra.strava_auth import get_valid_token
from infra.strava_fetcher import fetch_activities, fetch_all_details, resolve_gear_names
from infra.report_writer import write_report


def run_analysis(days: int = 30, force_refresh: bool = False, output_path: str = "report.md") -> None:
    cache = CacheRepository()

    print("Autenticando com o Strava...")
    token = get_valid_token(cache)

    if force_refresh or not cache.is_cache_valid():
        print(f"Buscando atividades dos últimos {days} dias...")
        activities = fetch_activities(token, days=days)
        print(f"{len(activities)} corridas encontradas.")

        print(f"Buscando detalhes ({len(activities)} chamadas à API): splits, best efforts, segmentos...")
        fetch_all_details(token, activities)

        gear_ids = {a.gear_id for a in activities if a.gear_id}
        if gear_ids:
            print(f"Resolvendo {len(gear_ids)} tênis...")
            gear_map = resolve_gear_names(token, gear_ids)
        else:
            gear_map = {}

        cache.save_activities(activities)
        cache.save_gear_map(gear_map)
        print("Dados salvos em cache.")
    else:
        activities = cache.load_activities()
        gear_map = cache.load_gear_map()
        print(f"{len(activities)} corridas carregadas do cache local.")

    if not activities:
        print("Nenhuma corrida encontrada no período.")
        return

    print("Calculando estatísticas e projeções...")
    stats = compute_stats(activities, gear_map)
    projections = compute_projections(activities)

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days)

    report = Report(
        athlete_name="Atleta",
        generated_at=datetime.now(timezone.utc),
        period_days=days,
        period_start=period_start,
        period_end=period_end,
        activities=activities,
        stats=stats,
        projections=projections,
        gear_map=gear_map,
    )

    print(f"Gerando relatório em {output_path}...")
    write_report(report, output_path)
    print(f"Pronto! Abra {output_path} e compartilhe com seu agente de IA.")
