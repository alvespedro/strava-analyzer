from pathlib import Path

from domain.models import Gear, Projection, Report, Stats


def _fmt_pace(pace_min_per_km: float) -> str:
    m = int(pace_min_per_km)
    s = int((pace_min_per_km - m) * 60)
    return f"{m}:{s:02d}"


def _fmt_time(total_sec: int) -> str:
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    if h > 0:
        return f"{h}h {m:02d}min"
    return f"{m}min {s:02d}s"


def _trend_pt(trend: str | None) -> str:
    return {"improving": "Melhorando", "regressing": "Piorando", "stable": "Estável"}.get(trend or "", "—")


def _gear_short_name(gear_id: str | None, gear_map: dict[str, Gear]) -> str:
    if not gear_id or gear_id not in gear_map:
        return "—"
    name = gear_map[gear_id].name
    return name[:20] if len(name) > 20 else name


def _build_report(report: Report) -> str:
    stats: Stats = report.stats
    gear_map = report.gear_map
    lines = []

    lines += [
        "# Relatório de Treinos Strava",
        f"**Atleta:** {report.athlete_name}",
        f"**Gerado em:** {report.generated_at.strftime('%d/%m/%Y %H:%M')}",
        f"**Período analisado:** {report.period_start.strftime('%d/%m/%Y')} a {report.period_end.strftime('%d/%m/%Y')} ({report.period_days} dias)",
        "",
        "---",
        "",
    ]

    # Seção 1: Estatísticas Gerais
    total_calories = sum(a.calories for a in report.activities if a.calories)
    lines += [
        "## 1. Estatísticas Gerais",
        f"- Total de corridas: **{stats.total_runs}**",
        f"- Distância total: **{stats.total_distance_km:.2f} km**",
        f"- Tempo total: **{_fmt_time(stats.total_time_sec)}**",
        f"- Distância média por corrida: **{stats.total_distance_km / stats.total_runs:.2f} km**",
        f"- Pace médio: **{_fmt_pace(stats.avg_pace_min_per_km)}/km**",
    ]
    if stats.avg_heartrate:
        lines.append(f"- FC média: **{stats.avg_heartrate:.0f} bpm**")
    if stats.avg_cadence:
        lines.append(f"- Cadência média: **{stats.avg_cadence:.0f} spm**")
    if stats.avg_watts:
        lines.append(f"- Potência média: **{stats.avg_watts:.0f} W**")
    if total_calories:
        lines.append(f"- Calorias totais estimadas: **{total_calories:.0f} kcal**")
    lines += [
        f"- Conquistas totais: **{stats.total_achievements}**",
        f"- Recordes pessoais (PRs): **{stats.total_prs}**",
        "",
    ]

    # Seção 2: Tendência de Pace
    pace_delta = stats.pace_last - stats.pace_first
    pace_delta_str = f"{abs(pace_delta):.2f} min/km {'mais rápido' if pace_delta < 0 else 'mais lento'}"
    lines += [
        "## 2. Tendência de Pace",
        f"- Direção: **{_trend_pt(stats.pace_trend)}**",
        f"- Pace na primeira corrida do período: **{_fmt_pace(stats.pace_first)}/km**",
        f"- Pace na última corrida do período: **{_fmt_pace(stats.pace_last)}/km**",
        f"- Variação: **{pace_delta_str}**",
        f"- Coeficiente angular: `{stats.pace_slope:.5f}` (negativo = ficando mais rápido)",
        "",
        "> **Nota:** O pace de treino reflete condições como calor, elevação e fadiga acumulada,",
        "> não apenas a evolução de condicionamento. Interprete com esse contexto.",
        "",
    ]

    # Seção 3: Esteira vs Rua
    total = stats.total_runs
    lines += [
        "## 3. Esteira vs Rua",
        f"- Corridas ao ar livre: **{stats.outdoor_runs}** ({stats.outdoor_runs/total*100:.1f}%)",
        f"- Corridas na esteira: **{stats.trainer_runs}** ({stats.trainer_runs/total*100:.1f}%)",
        "",
    ]

    # Seção 4: Tênis Utilizados
    if stats.gear_usage:
        lines += [
            "## 4. Tênis Utilizados",
            "",
            "| Tênis | Corridas | Km neste período | Total acumulado |",
            "|-------|----------|-----------------|-----------------|",
        ]
        for gu in stats.gear_usage:
            primary_tag = " ⭐" if gu.gear.primary else ""
            lines.append(f"| {gu.gear.name}{primary_tag} | {gu.run_count} | {gu.total_km:.1f} km | {gu.gear.total_distance_km:.0f} km |")
        lines.append("")

    # Seção 5: Projeções de Prova (híbrido: best effort + Riegel)
    if report.projections:
        riegel_baseline = max(report.activities, key=lambda a: a.distance_km)
        lines += [
            "## 5. Projeções de Prova",
            f"*Riegel baseado na corrida mais longa: {riegel_baseline.distance_km:.2f} km em "
            f"{riegel_baseline.duration_formatted} ({riegel_baseline.pace_formatted}/km) — "
            f"{riegel_baseline.start_date.strftime('%d/%m/%Y')}*",
            "",
            "| Prova | Tempo | Pace | Fonte |",
            "|-------|-------|------|-------|",
        ]
        for p in report.projections:
            source_label = "✅ Best Effort (direto)" if p.source == "best_effort" else "📐 Riegel (estimado)"
            lines.append(f"| {p.label} | {p.time_formatted} | {p.pace_formatted}/km | {source_label} |")
        lines += [
            "",
            "*Best Effort = tempo real registrado pelo Strava nessa distância (mais preciso).*",
            "*Riegel = projeção pela fórmula T2 = T1 × (D2/D1)^1.06 a partir do longão.*",
            "",
        ]

    # Seção 6: Potência de Corrida
    if stats.avg_watts:
        lines += [
            "## 6. Potência de Corrida",
            f"- Potência média: **{stats.avg_watts:.0f} W**",
        ]
        if stats.watts_trend:
            lines += [
                f"- Tendência: **{_trend_pt(stats.watts_trend)}**",
                f"- Coeficiente angular: `{stats.watts_slope:.3f}` W/corrida (positivo = ficando mais forte)",
            ]
        lines.append("")

    # Seção 7: Log de Corridas
    lines += [
        "## 7. Log de Corridas",
        "",
        "| Data | Nome | Dist. | Duração | Pace | FC | Elevação | Watts | Tênis | Conquistas |",
        "|------|------|-------|---------|------|----|----------|-------|-------|------------|",
    ]
    for act in sorted(report.activities, key=lambda a: a.start_date, reverse=True):
        hr = f"{act.avg_heartrate:.0f}" if act.avg_heartrate else "—"
        watts = f"{act.watts:.0f}W" if act.watts else "—"
        shoe = _gear_short_name(act.gear_id, gear_map)
        ach = str(act.achievement_count) if act.achievement_count else "—"
        surface = "🏠" if act.trainer else "🌳"
        lines.append(
            f"| {act.start_date.strftime('%d/%m/%Y')} {surface}"
            f"| {act.name[:30]}"
            f"| {act.distance_km:.2f} km"
            f"| {act.duration_formatted}"
            f"| {act.pace_formatted}/km"
            f"| {hr} bpm"
            f"| {act.elevation_gain_m:.0f} m"
            f"| {watts}"
            f"| {shoe}"
            f"| {ach} |"
        )
    lines.append("")

    # Seção 8: Breakdown Semanal
    lines += ["## 8. Breakdown Semanal", "", "| Semana | Corridas | Distância | Pace Médio | FC Média |", "|--------|----------|-----------|------------|----------|"]
    for week_label, data in stats.weeks.items():
        hr = f"{data['avg_hr']:.0f} bpm" if data["avg_hr"] else "—"
        lines.append(f"| {week_label} | {data['runs']} | {data['distance_km']:.2f} km | {_fmt_pace(data['avg_pace'])}/km | {hr} |")
    lines.append("")

    # Seção 9: Corridas Notáveis
    lines += [
        "## 9. Corridas Notáveis",
        f"- **Mais longa:** {stats.longest_run.name} — {stats.longest_run.distance_km:.2f} km ({stats.longest_run.start_date.strftime('%d/%m/%Y')})",
        f"- **Mais rápida (pace):** {stats.fastest_run.name} — {stats.fastest_run.pace_formatted}/km ({stats.fastest_run.start_date.strftime('%d/%m/%Y')})",
        f"- **Maior elevação:** {stats.highest_elevation_run.name} — {stats.highest_elevation_run.elevation_gain_m:.0f} m ({stats.highest_elevation_run.start_date.strftime('%d/%m/%Y')})",
    ]
    if stats.highest_hr_run:
        lines.append(f"- **FC máxima registrada:** {stats.highest_hr_run.name} — {stats.highest_hr_run.max_heartrate:.0f} bpm ({stats.highest_hr_run.start_date.strftime('%d/%m/%Y')})")
    lines.append("")

    # Seção 10: Carga de Treino
    total_weeks = max(len(stats.weeks), 1)
    weeks_with_runs = sum(1 for w in stats.weeks.values() if w["runs"] > 0)
    km_per_week = stats.total_distance_km / total_weeks
    lines += [
        "## 10. Carga de Treino",
        f"- Média de km/semana: **{km_per_week:.2f} km**",
        f"- Semanas com pelo menos uma corrida: **{weeks_with_runs}/{total_weeks}**",
        "",
    ]

    # Seção 11: Best Efforts Pessoais
    all_best_efforts: dict[str, tuple] = {}  # name → (elapsed_sec, activity)
    for act in report.activities:
        for be in act.best_efforts:
            if be.name not in all_best_efforts or be.elapsed_sec < all_best_efforts[be.name][0]:
                all_best_efforts[be.name] = (be.elapsed_sec, be, act)

    if all_best_efforts:
        STANDARD_ORDER = ["400m", "1/2 mile", "1K", "1 mile", "2 mile", "5K", "10K", "Half-Marathon", "Marathon"]
        ordered = sorted(
            all_best_efforts.items(),
            key=lambda x: STANDARD_ORDER.index(x[0]) if x[0] in STANDARD_ORDER else 99,
        )
        lines += [
            "## 11. Best Efforts Pessoais (melhores tempos do período)",
            "",
            "| Distância | Tempo | Pace | PR? | Corrida |",
            "|-----------|-------|------|-----|---------|",
        ]
        for name, (elapsed_sec, be, act) in ordered:
            dist_km = be.distance_m / 1000
            pace = (elapsed_sec / 60) / dist_km
            pr_tag = "🏆 PR" if be.pr_rank == 1 else f"Top {be.pr_rank}" if be.pr_rank else "—"
            t = int(elapsed_sec)
            h, rem = divmod(t, 3600)
            m, s = divmod(rem, 60)
            time_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
            lines.append(f"| {name} | {time_str} | {_fmt_pace(pace)}/km | {pr_tag} | {act.name} ({act.start_date.strftime('%d/%m/%Y')}) |")
        lines.append("")

    # Seção 12: Segmentos Notáveis (apenas corridas outdoor com PR)
    acts_with_segs = [
        a for a in sorted(report.activities, key=lambda a: a.start_date, reverse=True)
        if a.segment_efforts
    ]
    if acts_with_segs:
        lines += ["## 12. Segmentos Notáveis (corridas outdoor)", ""]
        for act in acts_with_segs:
            pr_segs = [s for s in act.segment_efforts if s.pr_rank == 1]
            top_segs = act.segment_efforts[:5] if not pr_segs else pr_segs[:10]
            if not top_segs:
                continue
            lines += [
                f"### {act.start_date.strftime('%d/%m/%Y')} — {act.name} ({act.distance_km:.2f} km)",
                "",
                "| Segmento | Distância | Tempo | Pace | FC | Ranking |",
                "|----------|-----------|-------|------|----|---------|",
            ]
            for seg in top_segs:
                fc = f"{seg.avg_heartrate:.0f} bpm" if seg.avg_heartrate else "—"
                rank = "🏆 PR" if seg.pr_rank == 1 else f"Top {seg.pr_rank}"
                t = int(seg.elapsed_sec)
                h, rem = divmod(t, 3600)
                m_val, s_val = divmod(rem, 60)
                time_str = f"{h}:{m_val:02d}:{s_val:02d}" if h else f"{m_val}:{s_val:02d}"
                lines.append(
                    f"| {seg.name[:40]} | {seg.distance_m/1000:.2f} km "
                    f"| {time_str} | {seg.pace_formatted}/km | {fc} | {rank} |"
                )
            lines.append("")

    # Seção 13: Splits por Km
    activities_with_splits = [a for a in sorted(report.activities, key=lambda a: a.start_date, reverse=True) if a.splits]
    if activities_with_splits:
        lines += ["## 13. Splits por Km", ""]
        for act in activities_with_splits:
            surface = "Esteira" if act.trainer else "Rua"
            lines += [
                f"### {act.start_date.strftime('%d/%m/%Y')} — {act.name} ({act.distance_km:.2f} km · {surface})",
                "",
                "| km | Distância | Pace | FC Média |",
                "|----|-----------|------|----------|",
            ]
            for s in act.splits:
                hr = f"{s.avg_heartrate:.0f} bpm" if s.avg_heartrate else "—"
                lines.append(f"| {s.split_number} | {s.distance_km:.2f} km | {_fmt_pace(s.pace_min_per_km)}/km | {hr} |")
            lines.append("")

    # Seção 14: Notas e Limitações
    no_hr = sum(1 for a in report.activities if not a.avg_heartrate)
    no_cad = sum(1 for a in report.activities if not a.avg_cadence)
    no_splits = sum(1 for a in report.activities if not a.splits)
    lines += [
        "## 14. Notas e Limitações",
        f"- Atividades sem dados de FC: {no_hr}",
        f"- Atividades sem dados de cadência: {no_cad}",
        f"- Atividades sem splits: {no_splits}",
        "- Sessões em esteira não sincronizadas com GPS podem estar ausentes.",
        "- Projeções de Riegel assumem esforço aeróbico consistente entre as distâncias.",
        "- Potência de corrida requer sensor compatível (ex: Garmin Running Power).",
    ]

    return "\n".join(lines)


def write_report(report: Report, output_path: str = "report.md") -> None:
    content = _build_report(report)
    Path(output_path).write_text(content, encoding="utf-8")
