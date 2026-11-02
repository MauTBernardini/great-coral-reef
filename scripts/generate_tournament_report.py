from __future__ import annotations

# HTML e CSS embutidos são mantidos legíveis como templates completos.
# ruff: noqa: E501
import argparse
import html
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DISPLAY_NAMES = {
    "branched_finger_coral": "Branched Finger Coral",
    "grooved_brain_coral": "Grooved Brain Coral",
    "gorgonian_sea_fan": "Gorgonian Sea Fan",
    "blacktip_reef_shark": "Blacktip Reef Shark",
    "mandarin_dragonet": "Mandarin Dragonet",
    "leafy_seadragon": "Leafy Seadragon",
    "sea_cucumber": "Sea Cucumber",
    "green_chromis": "Green Chromis",
    "moon_jelly": "Moon Jelly",
    "sandy_bed": "Sandy Bed",
    "rocky_reef": "Rocky Reef",
    "dark_overhang": "Dark Overhang",
    "seagrass_meadow": "Seagrass Meadow",
}


def display_name(value: str) -> str:
    return DISPLAY_NAMES.get(value, value.replace("_", " ").title())


def pct(value: float) -> str:
    return "—" if pd.isna(value) else f"{value * 100:.1f}%"


def num(value: float, digits: int = 1) -> str:
    return "—" if pd.isna(value) else f"{value:.{digits}f}"


def latest_paired_dir() -> Path:
    candidates = sorted((ROOT / "artifacts" / "tournaments").glob("paired_*"))
    if not candidates:
        raise FileNotFoundError("Nenhum torneio pareado encontrado.")
    return candidates[-1]


def latest_enriched_dir() -> Path:
    candidates = sorted((ROOT / "artifacts" / "tournaments").glob("enriched_*"))
    if not candidates:
        raise FileNotFoundError("Nenhuma amostra enriquecida encontrada.")
    return candidates[-1]


def load_enriched(directory: Path) -> dict[str, pd.DataFrame]:
    return {
        "games": pd.read_csv(directory / "enriched_games.csv"),
        "players": pd.read_csv(directory / "enriched_players.csv"),
        "events": pd.read_csv(directory / "card_events.csv"),
        "final_cards": pd.read_csv(directory / "final_card_scores.csv"),
        "curves": pd.read_csv(directory / "round_curves.csv"),
    }


def run_detailed_sample(games: int) -> tuple[pd.DataFrame, Path]:
    from reef_game.simulation.tournament import TournamentConfig, run_tournament

    config = TournamentConfig(
        games=games,
        corals_path=str(ROOT / "configs" / "corals.yaml"),
        soils_path=str(ROOT / "configs" / "soils.yaml"),
        fauna_path=str(ROOT / "configs" / "fauna.yaml"),
        instincts_path=str(ROOT / "configs" / "instincts.yaml"),
        upgrades_path=str(ROOT / "configs" / "upgrades.yaml"),
        balance_rules_path=str(ROOT / "configs" / "balance_rules.yaml"),
        climate_path=str(ROOT / "configs" / "climate.yaml"),
        version_path=str(ROOT / "configs" / "version.yaml"),
        output_dir=str(ROOT / "artifacts" / "tournaments"),
        agent_p1="greedy",
        agent_p2="longterm",
        seed_start=1000,
        max_rounds=50,
        show_progress=True,
        save_results=True,
        save_turn_states=False,
        save_turn_states_detail=False,
        randomize_seats=True,
    )
    frame = run_tournament(config)
    return frame, Path(frame.attrs["artifact_dir"])


def player_observations(results: pd.DataFrame) -> pd.DataFrame:
    observations = []
    for _, game in results.iterrows():
        winner = game.get("winner")
        for seat in (1, 2):
            agent = game[f"p{seat}_agent"]
            won = 0.0 if pd.isna(winner) else float(int(float(winner)) == seat)
            observations.append(
                {
                    "seed": int(game["seed"]),
                    "seat": seat,
                    "agent": agent,
                    "won": won,
                    "draw": float(pd.isna(winner)),
                    "score": float(game[f"p{seat}_score"]),
                    "rounds": float(game["rounds"]),
                    "turns": float(game["turns"]),
                    **{
                        column.removeprefix(f"p{seat}_"): game[column]
                        for column in results.columns
                        if column.startswith(f"p{seat}_")
                        and column not in {f"p{seat}_agent", f"p{seat}_score"}
                    },
                }
            )
    return pd.DataFrame(observations)


def numeric_card_stats(players: pd.DataFrame, prefix: str) -> pd.DataFrame:
    columns = [
        column
        for column in players
        if column.startswith(prefix)
        and column not in {"fauna_total", "coral_points_total", "fauna_points_total"}
        and not column.startswith("coral_points_z")
        and not column.startswith("fauna_points_z")
        and not column.startswith("fauna_z")
    ]
    baseline_win = players["won"].mean()
    baseline_score = players["score"].mean()
    rows = []
    for column in columns:
        counts = pd.to_numeric(players[column], errors="coerce").fillna(0)
        used = players[counts > 0]
        rows.append(
            {
                "card": column.removeprefix(prefix),
                "total": int(counts.sum()),
                "games_used": len(used),
                "usage": len(used) / len(players),
                "avg_count": counts.mean(),
                "win_rate": used["won"].mean() if len(used) else math.nan,
                "avg_score": used["score"].mean() if len(used) else math.nan,
                "win_lift": used["won"].mean() - baseline_win if len(used) else math.nan,
                "score_lift": used["score"].mean() - baseline_score if len(used) else math.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["total", "card"], ascending=[False, True])


def owned_card_stats(players: pd.DataFrame, column: str) -> pd.DataFrame:
    baseline_win = players["won"].mean()
    baseline_score = players["score"].mean()
    cards: dict[str, list[int]] = {}
    for index, value in players[column].fillna("").items():
        for card in {part for part in str(value).split(";") if part}:
            cards.setdefault(card, []).append(index)
    rows = []
    for card, indices in cards.items():
        used = players.loc[indices]
        rows.append(
            {
                "card": card,
                "total": len(used),
                "games_used": len(used),
                "usage": len(used) / len(players),
                "avg_count": 1.0,
                "win_rate": used["won"].mean(),
                "avg_score": used["score"].mean(),
                "win_lift": used["won"].mean() - baseline_win,
                "score_lift": used["score"].mean() - baseline_score,
            }
        )
    frame = pd.DataFrame(
        rows,
        columns=[
            "card",
            "total",
            "games_used",
            "usage",
            "avg_count",
            "win_rate",
            "avg_score",
            "win_lift",
            "score_lift",
        ],
    )
    if frame.empty:
        return frame
    return frame.sort_values(["total", "card"], ascending=[False, True])


def card_table(frame: pd.DataFrame, owned: bool = False) -> str:
    rows = []
    for _, item in frame.iterrows():
        lift_class = "positive" if item["win_lift"] >= 0 else "negative"
        rows.append(
            "<tr>"
            f"<td class='name'>{html.escape(display_name(item['card']))}</td>"
            f"<td>{int(item['total'])}</td>"
            f"<td>{int(item['games_used'])}</td>"
            f"<td>{pct(item['usage'])}</td>"
            + ("" if owned else f"<td>{num(item['avg_count'], 2)}</td>")
            + f"<td><span class='bar'><i style='width:{min(100, item['win_rate'] * 100):.1f}%'></i></span>{pct(item['win_rate'])}</td>"
            f"<td>{num(item['avg_score'])}</td>"
            f"<td class='{lift_class}'>{item['win_lift'] * 100:+.1f} pp</td>"
            f"<td class='{lift_class}'>{item['score_lift']:+.1f}</td>"
            "</tr>"
        )
    average_header = "" if owned else "<th>Média/jogo</th>"
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Carta/tile</th><th>Total</th><th>Jogos com uso</th><th>Uso</th>"
        f"{average_header}<th>Vitórias</th><th>Pontos médios</th>"
        "<th>Δ vitória</th><th>Δ pontos</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def agent_summary(players: pd.DataFrame) -> pd.DataFrame:
    return (
        players.groupby("agent")
        .agg(
            games=("seed", "count"),
            wins=("won", "sum"),
            win_rate=("won", "mean"),
            draws=("draw", "sum"),
            avg_score=("score", "mean"),
            median_score=("score", "median"),
        )
        .reset_index()
    )


def paired_metrics(paired: pd.DataFrame, metadata: dict) -> dict:
    summary = metadata["summary"]
    margins = paired["a_total_score"] - paired["b_total_score"]
    greedy_p1_win = (paired["game1_winner"] == "a").mean()
    greedy_p2_win = (paired["game2_winner"] == "a").mean()
    longterm_p1_win = (paired["game2_winner"] == "b").mean()
    longterm_p2_win = (paired["game1_winner"] == "b").mean()
    return {
        **summary,
        "margin_mean": margins.mean(),
        "margin_median": margins.median(),
        "margin_q25": margins.quantile(0.25),
        "margin_q75": margins.quantile(0.75),
        "greedy_p1_win": greedy_p1_win,
        "greedy_p2_win": greedy_p2_win,
        "longterm_p1_win": longterm_p1_win,
        "longterm_p2_win": longterm_p2_win,
    }


def section_for_category(
    title: str, players: pd.DataFrame, prefix: str | None = None, column: str | None = None
) -> str:
    overall = owned_card_stats(players, column) if column else numeric_card_stats(players, prefix)
    parts = [f"<section><h2>{title}</h2>", card_table(overall, owned=column is not None)]
    parts.append("<div class='agent-details'>")
    for agent in ("greedy", "longterm"):
        subset = players[players["agent"] == agent]
        stats = owned_card_stats(subset, column) if column else numeric_card_stats(subset, prefix)
        parts.append(
            f"<details><summary>Detalhamento: {display_name(agent)}</summary>"
            f"{card_table(stats, owned=column is not None)}</details>"
        )
    parts.append("</div></section>")
    return "".join(parts)


def card_efficiency_stats(
    events: pd.DataFrame, final_cards: pd.DataFrame, agent: str | None = None
) -> pd.DataFrame:
    if agent is not None:
        events = events[events["agent"] == agent]
        final_cards = final_cards[final_cards["agent"] == agent]
    events = events[events["category"].isin(["coral", "fauna"])]
    final_cards = final_cards[final_cards["category"].isin(["coral", "fauna"])]
    played = (
        events.groupby(["category", "card"])
        .agg(
            played=("copies", "sum"),
            printed_cost=("printed_cost", "first"),
            immediate_points=("immediate_points", "sum"),
        )
        .reset_index()
    )
    survivors = (
        final_cards.groupby(["category", "card"])
        .agg(
            surviving=("card", "size"),
            final_points=("final_points", "sum"),
            avg_final_points=("final_points", "mean"),
        )
        .reset_index()
    )
    frame = played.merge(survivors, on=["category", "card"], how="left").fillna(0)
    frame["avg_immediate_points"] = frame["immediate_points"] / frame["played"]
    frame["survival"] = frame["surviving"] / frame["played"]
    frame["immediate_points_per_cost"] = frame.apply(
        lambda row: row["avg_immediate_points"] / row["printed_cost"]
        if row["printed_cost"]
        else math.nan,
        axis=1,
    )
    frame["final_points_per_cost"] = frame.apply(
        lambda row: row["avg_final_points"] / row["printed_cost"]
        if row["printed_cost"]
        else math.nan,
        axis=1,
    )
    return frame.sort_values(
        ["category", "final_points_per_cost", "played"], ascending=[True, False, False]
    )


def efficiency_table(frame: pd.DataFrame) -> str:
    rows = []
    for _, item in frame.iterrows():
        rows.append(
            "<tr>"
            f"<td>{display_name(item['category'])}</td>"
            f"<td class='name'>{html.escape(display_name(item['card']))}</td>"
            f"<td>{int(item['played'])}</td><td>{int(item['surviving'])}</td>"
            f"<td>{pct(item['survival'])}</td><td>{int(item['printed_cost'])}</td>"
            f"<td>{num(item['avg_immediate_points'], 2)}</td>"
            f"<td>{num(item['immediate_points_per_cost'], 2)}</td>"
            f"<td>{num(item['avg_final_points'], 2)}</td>"
            f"<td>{num(item['final_points_per_cost'], 2)}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Tipo</th><th>Carta</th><th>Jogadas</th><th>Sobreviventes</th>"
        "<th>Sobrevivência</th><th>Custo impresso</th><th>Pontos imediatos/carta</th>"
        "<th>Pontos imediatos/custo</th><th>Pontos finais/carta</th>"
        "<th>Pontos finais/custo</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def card_efficiency_section(enriched: dict[str, pd.DataFrame]) -> str:
    events = enriched["events"]
    final_cards = enriched["final_cards"]
    parts = [
        "<section><h2>Eficiência de pontos por custo da carta</h2>",
        "<p>O custo é a soma impressa de Sol e Plâncton. Pontos imediatos medem a "
        "variação marginal de score quando a carta entra; pontos finais recalculam cada "
        "instância sobrevivente no encerramento.</p>",
        efficiency_table(card_efficiency_stats(events, final_cards)),
    ]
    for agent in ("greedy", "longterm"):
        parts.append(
            f"<details><summary>Eficiência: {display_name(agent)}</summary>"
            f"{efficiency_table(card_efficiency_stats(events, final_cards, agent))}</details>"
        )
    parts.append(
        "<p class='method'>Descontos de solo e Upgrades não são abatidos do custo impresso. "
        "Cartas de custo zero exibem eficiência por custo como —. O par de Staghorn divide "
        "o ganho marginal entre as duas cópias e não incorpora a sobretaxa no custo impresso.</p></section>"
    )
    return "".join(parts)


def svg_line_chart(series: dict[str, tuple[list, list]], y_label: str) -> str:
    width, height = 820, 300
    left, right, top, bottom = 62, 20, 24, 52
    colors = ["#007f78", "#ed6a5a", "#6c5ce7", "#e6a700", "#2471a3", "#8e5b3a"]
    all_x = [float(x) for xs, _ in series.values() for x in xs]
    all_y = [float(y) for _, ys in series.values() for y in ys if not pd.isna(y)]
    if not all_x or not all_y:
        return ""
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(0, min(all_y)), max(all_y)
    if y_max == y_min:
        y_max = y_min + 1
    plot_w, plot_h = width - left - right, height - top - bottom

    def sx(value):
        return left + (float(value) - x_min) / max(1, x_max - x_min) * plot_w

    def sy(value):
        return top + (y_max - float(value)) / (y_max - y_min) * plot_h

    parts = [f"<svg class='chart' viewBox='0 0 {width} {height}' role='img'>"]
    for index in range(5):
        value = y_min + (y_max - y_min) * index / 4
        y = sy(value)
        parts.append(
            f"<line x1='{left}' y1='{y:.1f}' x2='{width-right}' y2='{y:.1f}' class='gridline'/>"
            f"<text x='{left-8}' y='{y+4:.1f}' text-anchor='end'>{value:.1f}</text>"
        )
    for index in range(5):
        value = x_min + (x_max - x_min) * index / 4
        x = sx(value)
        parts.append(f"<text x='{x:.1f}' y='{height-25}' text-anchor='middle'>{value:.0f}</text>")
    parts.append(
        f"<text x='{width/2}' y='{height-5}' text-anchor='middle'>Rodada</text>"
        f"<text transform='translate(15 {height/2}) rotate(-90)' text-anchor='middle'>{html.escape(y_label)}</text>"
    )
    for index, (label, (xs, ys)) in enumerate(series.items()):
        color = colors[index % len(colors)]
        points = " ".join(
            f"{sx(x):.1f},{sy(y):.1f}" for x, y in zip(xs, ys, strict=True) if not pd.isna(y)
        )
        parts.append(f"<polyline points='{points}' fill='none' stroke='{color}' stroke-width='2.5'/>")
        parts.append(
            f"<rect x='{left + index * 125}' y='{height-18}' width='12' height='3' fill='{color}'/>"
            f"<text x='{left + 17 + index * 125}' y='{height-13}'>{html.escape(label)}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def turns_histogram(games: pd.DataFrame) -> str:
    counts = pd.cut(games["turns"], bins=8).value_counts(sort=False)
    maximum = max(counts.max(), 1)
    bars = []
    for interval, count in counts.items():
        height = 150 * count / maximum
        bars.append(
            "<div class='hist-col'>"
            f"<span>{int(count)}</span><i style='height:{height:.1f}px'></i>"
            f"<small>{interval.left:.0f}–{interval.right:.0f}</small></div>"
        )
    return "<div class='histogram'>" + "".join(bars) + "</div>"


def population_section(enriched: dict[str, pd.DataFrame]) -> str:
    players = enriched["players"]
    rows = []
    for agent in ("greedy", "longterm"):
        subset = players[players["agent"] == agent]
        for layer in range(3):
            corals = subset[f"corals_z{layer}"].mean()
            coral_points = subset[f"coral_points_z{layer}"].mean()
            fauna = subset[f"fauna_z{layer}"].mean()
            fauna_points = subset[f"fauna_points_z{layer}"].mean()
            rows.append(
                f"<tr><td>{display_name(agent)}</td><td>Camada {layer}</td>"
            f"<td>{num(corals, 2)}</td><td>{pct(corals / 256)}</td>"
                f"<td>{num(coral_points, 2)}</td><td>{num(coral_points / corals if corals else math.nan, 2)}</td>"
                f"<td>{num(fauna, 2)}</td><td>{num(fauna_points, 2)}</td></tr>"
            )
    strategy_rows = []
    for agent in ("greedy", "longterm"):
        subset = players[players["agent"] == agent]
        strategy_rows.append(
            f"<tr><td>{display_name(agent)}</td>"
            f"<td>{num(subset['corals_total'].mean(), 2)}</td>"
            f"<td>{num(subset['fauna_total'].mean(), 2)}</td>"
            f"<td>{pct(subset['habitat_fill'].mean())}</td>"
            f"<td>{num(subset['full_towers'].mean(), 2)}</td>"
            f"<td>{num(subset['surface_columns'].mean(), 2)}</td>"
            f"<td>{num(subset['ponds'].mean(), 2)}</td>"
            f"<td>{num(subset['coral_points_total'].mean(), 1)}</td>"
            f"<td>{num(subset['fauna_points_total'].mean(), 1)}</td>"
            f"<td>{num(subset['instinct_points'].mean(), 1)}</td></tr>"
        )
    curves = enriched["curves"]
    layer_series = {}
    for layer in range(3):
        grouped = curves.groupby("round")[f"corals_z{layer}"].mean()
        layer_series[f"Camada {layer}"] = (grouped.index.tolist(), grouped.tolist())
    return (
        "<section><h2>Povoamento e estratégia espacial</h2>"
        "<h3>Estado final por camada e por agente</h3><div class='table-wrap'><table><thead><tr>"
        "<th>Agente</th><th>Camada</th><th>Corais médios</th><th>Ocupação da camada</th>"
        "<th>Pontos de coral</th><th>Pontos/coral</th><th>Fauna média</th><th>Pontos de fauna</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        "<h3>Perfil estrutural final</h3><div class='table-wrap'><table><thead><tr>"
        "<th>Agente</th><th>Corais</th><th>Fauna</th><th>Habitat preenchido</th>"
        "<th>Torres completas</th><th>Colunas na superfície</th><th>Ponds</th>"
        "<th>Pontos de coral</th><th>Pontos de fauna</th><th>Pontos de Instinto</th>"
        "</tr></thead><tbody>" + "".join(strategy_rows) + "</tbody></table></div>"
        "<h3>Crescimento médio do recife</h3>"
        + svg_line_chart(layer_series, "Corais por jogador")
        + "<p class='method'>A ocupação da camada usa 16 posições possíveis. Pontos por camada são recalculados no estado final e incluem regras posicionais.</p></section>"
    )


def climate_and_duration_section(enriched: dict[str, pd.DataFrame]) -> str:
    curves = enriched["curves"]
    games = enriched["games"]
    common = curves.groupby("round").agg(
        temperature=("temperature", "mean"),
        ph=("ph", "mean"),
        occupancy=("occupancy", "mean"),
        turns_in_round=("turns_in_round", "mean"),
    )
    x = common.index.tolist()
    turn_stats = games["turns"].describe(percentiles=[0.25, 0.5, 0.75])
    round_stats = games["rounds"].describe(percentiles=[0.25, 0.5, 0.75])
    return (
        "<section><h2>Clima, duração e ritmo das partidas</h2>"
        "<div class='cards compact'>"
        f"<div class='metric'><b>{num(turn_stats['mean'])}</b><span>turnos médios</span></div>"
        f"<div class='metric'><b>{num(turn_stats['50%'])}</b><span>mediana de turnos</span></div>"
        f"<div class='metric'><b>{num(round_stats['mean'])}</b><span>rodadas médias</span></div>"
        f"<div class='metric'><b>{num(games['occupancy'].mean() * 100)}%</b><span>ocupação final</span></div>"
        "</div><h3>Distribuição de turnos por partida</h3>"
        + turns_histogram(games)
        + "<p class='method'>Intervalo interquartil: "
        f"{turn_stats['25%']:.0f}–{turn_stats['75%']:.0f} turnos; mínimo {turn_stats['min']:.0f}, máximo {turn_stats['max']:.0f}.</p>"
        "<div class='chart-grid'><div><h3>Temperatura média</h3>"
        + svg_line_chart({"Temperatura °C": (x, common["temperature"].tolist())}, "°C")
        + "</div><div><h3>pH médio</h3>"
        + svg_line_chart({"pH": (x, common["ph"].tolist())}, "pH")
        + "</div><div><h3>Ocupação do tabuleiro</h3>"
        + svg_line_chart({"Ocupação": (x, (common["occupancy"] * 100).tolist())}, "%")
        + "</div><div><h3>Turnos por rodada</h3>"
        + svg_line_chart({"Turnos": (x, common["turns_in_round"].tolist())}, "Turnos")
        + "</div></div><div class='note'>O pH permanece em 8,1 durante toda a amostra porque as cartas atuais usam ph_steps: 0. Hoje, somente a temperatura conduz as transições climáticas.</div></section>"
    )


def economy_section(enriched: dict[str, pd.DataFrame]) -> str:
    players = enriched["players"]
    rows = []
    for agent in ("greedy", "longterm"):
        subset = players[players["agent"] == agent]
        rows.append(
            f"<tr><td>{display_name(agent)}</td>"
            f"<td>{num(subset['produced_sun'].mean())}</td><td>{num(subset['produced_plankton'].mean())}</td>"
            f"<td>{num(subset['produced_o2'].mean())}</td><td>{num(subset['spent_sun'].mean())}</td>"
            f"<td>{num(subset['spent_plankton'].mean())}</td><td>{num(subset['final_sun'].mean())}</td>"
            f"<td>{num(subset['final_plankton'].mean())}</td><td>{num(subset['final_o2'].mean())}</td>"
            f"<td>{num(subset['hand_size'].mean())}</td><td>{num(subset['dead_turns'].mean())}</td></tr>"
        )
    curves = enriched["curves"]
    production_series = {}
    stock_series = {}
    for agent in ("greedy", "longterm"):
        grouped = curves[curves["agent"] == agent].groupby("round").mean(numeric_only=True)
        label = display_name(agent)
        production_series[f"{label} Sol"] = (grouped.index.tolist(), grouped["produced_sun"].tolist())
        production_series[f"{label} Plâncton"] = (
            grouped.index.tolist(),
            grouped["produced_plankton"].tolist(),
        )
        stock_series[f"{label} Sol"] = (grouped.index.tolist(), grouped["sun"].tolist())
        stock_series[f"{label} Plâncton"] = (grouped.index.tolist(), grouped["plankton"].tolist())
    correlation_fields = {
        "Corais": "corals_total",
        "Fauna": "fauna_total",
        "Preenchimento do habitat": "habitat_fill",
        "Pontos de Instinto": "instinct_points",
        "Sol produzido": "produced_sun",
        "Plâncton produzido": "produced_plankton",
        "Sol acumulado": "final_sun",
        "Plâncton acumulado": "final_plankton",
        "Torres completas": "full_towers",
        "Ponds": "ponds",
    }
    corr_rows = []
    for label, field in correlation_fields.items():
        corr = players[["score", field]].corr().iloc[0, 1]
        corr_rows.append(f"<tr><td>{label}</td><td>{corr:+.3f}</td></tr>")
    return (
        "<section><h2>Economia, produção e acúmulo de recursos</h2>"
        "<div class='table-wrap'><table><thead><tr><th>Agente</th><th>Sol produzido</th>"
        "<th>Plâncton produzido</th><th>O₂ produzido</th><th>Sol gasto</th><th>Plâncton gasto</th>"
        "<th>Sol final</th><th>Plâncton final</th><th>O₂ final</th><th>Mão final</th><th>Turnos mortos</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        "<div class='chart-grid'><div><h3>Produção acumulada por rodada</h3>"
        + svg_line_chart(production_series, "Recursos produzidos")
        + "</div><div><h3>Recursos armazenados por rodada</h3>"
        + svg_line_chart(stock_series, "Recursos disponíveis")
        + "</div></div><h3>Correlação exploratória com o score final</h3>"
        "<div class='table-wrap narrow'><table><thead><tr><th>Métrica</th><th>Correlação de Pearson</th>"
        "</tr></thead><tbody>" + "".join(corr_rows) + "</tbody></table></div>"
        "<p class='method'>Correlação próxima de +1 acompanha scores altos; próxima de −1 acompanha scores baixos. Não demonstra causalidade e mistura comportamento dos dois agentes.</p></section>"
    )


def balance_findings_section(enriched: dict[str, pd.DataFrame], paired_stats: dict) -> str:
    players = enriched["players"]
    games = enriched["games"]
    greedy = players[players["agent"] == "greedy"]
    longterm = players[players["agent"] == "longterm"]
    plankton_retention_g = greedy["final_plankton"].mean() / greedy["produced_plankton"].mean()
    plankton_retention_l = (
        longterm["final_plankton"].mean() / longterm["produced_plankton"].mean()
    )
    score_corr = players.corr(numeric_only=True)["score"]
    bottom_points_per_coral = players["coral_points_z0"].sum() / players["corals_z0"].sum()
    middle_points_per_coral = players["coral_points_z1"].sum() / players["corals_z1"].sum()
    top_points_per_coral = players["coral_points_z2"].sum() / players["corals_z2"].sum()
    return (
        "<section><h2>Sinais principais de balanceamento</h2><div class='findings'>"
        f"<article><b>Economia com forte excedente</b><p>O Plâncton final equivale a {pct(plankton_retention_g)} da produção acumulada do Greedy e {pct(plankton_retention_l)} da produção do LongTerm. O estoque médio final passa de 90 para ambos, sugerindo oferta excessiva ou poucos sumidouros.</p></article>"
        f"<article><b>O₂ praticamente sem consumo persistente</b><p>O₂ produzido e O₂ final são iguais na média ({num(greedy['final_o2'].mean())} Greedy; {num(longterm['final_o2'].mean())} LongTerm), enquanto somente {pct(players['habitat_fill'].mean())} da capacidade fica preenchida.</p></article>"
        f"<article><b>Expansão domina o score</b><p>A correlação do score com corais é {score_corr['corals_total']:+.3f}, com ponds {score_corr['ponds']:+.3f} e com fauna {score_corr['fauna_total']:+.3f}. O preenchimento do habitat tem correlação {score_corr['habitat_fill']:+.3f}.</p></article>"
        f"<article><b>Base mais eficiente</b><p>Pontos médios por coral: camada 0 = {bottom_points_per_coral:.2f}, camada 1 = {middle_points_per_coral:.2f}, camada 2 = {top_points_per_coral:.2f}. A estratégia vertical existe, mas o retorno unitário permanece maior na base.</p></article>"
        f"<article><b>Tabuleiro avançado, não saturado</b><p>A ocupação final média é {pct(games['occupancy'].mean())}, após {num(games['rounds'].mean())} rodadas e {num(games['turns'].mean())} turnos.</p></article>"
        f"<article><b>Dois eixos climáticos inativos/desiguais</b><p>P1 vence {pct(paired_stats['residual_first_player_winrate'])}; o pH fica fixo em {num(games['ph'].mean())}. Iniciativa e temperatura influenciam o jogo, enquanto o pH ainda não gera decisões.</p></article>"
        "</div></section>"
    )


def reproducibility_note(detailed: pd.DataFrame, enriched: dict[str, pd.DataFrame]) -> str:
    pivot = enriched["players"].pivot(index="seed", columns="player", values="score")
    matches = 0
    comparable = 0
    for _, game in detailed.iterrows():
        seed = int(game["seed"])
        if seed not in pivot.index:
            continue
        comparable += 1
        if int(game["p1_score"]) == int(pivot.loc[seed, 1]) and int(game["p2_score"]) == int(
            pivot.loc[seed, 2]
        ):
            matches += 1
    diverged = comparable - matches
    return (
        "<div class='note'><b>Alerta de reprodutibilidade:</b> "
        f"{matches} de {comparable} partidas repetiram exatamente os scores em duas "
        f"execuções independentes; {diverged} divergiram apesar das mesmas seeds e agentes. "
        "A causa provável é a ordem não determinística de desempates ao enumerar ações a "
        "partir de conjuntos. As médias agregadas são próximas, mas comparações individuais "
        "por seed devem ser tratadas com cautela.</div>"
    )


def render_report(
    paired: pd.DataFrame,
    paired_meta: dict,
    detailed: pd.DataFrame,
    detailed_dir: Path,
    enriched: dict[str, pd.DataFrame],
    enriched_dir: Path,
) -> str:
    players = player_observations(detailed)
    paired_stats = paired_metrics(paired, paired_meta)
    agents = agent_summary(players).set_index("agent")
    generated = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    css = """
    :root{--ink:#12343b;--muted:#5f7479;--paper:#f4f9f8;--card:#fff;--reef:#007f78;
      --coral:#ed6a5a;--line:#d8e7e4;--good:#087f5b;--bad:#c92a2a}
    *{box-sizing:border-box} body{margin:0;background:var(--paper);color:var(--ink);
      font:15px/1.5 Inter,Segoe UI,Arial,sans-serif} header{background:linear-gradient(135deg,#073b4c,#007f78);
      color:white;padding:48px max(24px,calc((100% - 1180px)/2)) 40px} header h1{margin:0 0 8px;font-size:38px}
    header p{margin:0;opacity:.86}.container{max-width:1180px;margin:auto;padding:28px 20px 64px}
    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:0 0 28px}
    .metric,section{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 5px 18px #12343b0a}
    .metric{padding:18px}.metric b{display:block;font-size:27px;color:var(--reef)}.metric span{color:var(--muted)}
    section{padding:22px;margin:18px 0}h2{margin:0 0 14px;font-size:23px}h3{margin:22px 0 8px}
    .note{padding:13px 16px;border-left:4px solid var(--coral);background:#fff5f3;border-radius:6px;margin:14px 0}
    .table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:9px 10px;
      border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th{background:#edf6f4;color:#31565c}
    th:first-child,td:first-child{text-align:left}.name{font-weight:600}.positive{color:var(--good);font-weight:600}
    .negative{color:var(--bad);font-weight:600}.bar{display:inline-block;width:58px;height:7px;background:#e2eeec;
      border-radius:5px;margin-right:7px;overflow:hidden}.bar i{display:block;height:100%;background:var(--reef)}
    details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;font-weight:700;color:var(--reef)}
    .method{color:var(--muted);font-size:13px}code{background:#e8f1ef;padding:2px 5px;border-radius:4px}
    .chart{width:100%;min-width:560px;background:#fbfdfd;border:1px solid var(--line);border-radius:10px}
    .chart text{font-size:11px;fill:var(--muted)}.gridline{stroke:#dfeae8;stroke-width:1}
    .chart-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:18px}
    .histogram{height:205px;display:flex;align-items:flex-end;gap:8px;padding:15px 10px 0;border-bottom:1px solid var(--line)}
    .hist-col{height:185px;flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;min-width:45px}
    .hist-col i{display:block;width:70%;background:linear-gradient(#16a39a,#007f78);border-radius:5px 5px 0 0}
    .hist-col span,.hist-col small{font-size:11px;color:var(--muted)}.compact{margin-top:12px}.narrow{max-width:560px}
    .findings{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}.findings article{padding:15px;background:#f5faf9;border:1px solid var(--line);border-radius:10px}.findings b{color:var(--reef)}.findings p{margin:5px 0 0}
    footer{text-align:center;color:var(--muted);margin-top:28px}@media(max-width:650px){header h1{font-size:30px}}
    """

    comparison_rows = "".join(
        [
            f"<tr><td>Greedy</td><td>{pct(paired_stats['a_winrate'])}</td><td>{num(paired_stats['a_avg_score'])}</td><td>{pct(paired_stats['greedy_p1_win'])}</td><td>{pct(paired_stats['greedy_p2_win'])}</td></tr>",
            f"<tr><td>LongTerm</td><td>{pct(paired_stats['b_winrate'])}</td><td>{num(paired_stats['b_avg_score'])}</td><td>{pct(paired_stats['longterm_p1_win'])}</td><td>{pct(paired_stats['longterm_p2_win'])}</td></tr>",
        ]
    )
    detailed_rows = "".join(
        f"<tr><td>{display_name(agent)}</td><td>{int(row.games)}</td><td>{int(row.wins)}</td><td>{pct(row.win_rate)}</td><td>{num(row.avg_score)}</td><td>{num(row.median_score)}</td></tr>"
        for agent, row in agents.iterrows()
    )

    categories = "".join(
        [
            section_for_category("Corais presentes no fim", players, prefix="coral_"),
            section_for_category("Fauna sobrevivente no fim", players, prefix="fauna_"),
            section_for_category("Solos colocados", players, prefix="soil_"),
            section_for_category("Instintos possuídos", players, column="instincts"),
            section_for_category("Upgrades possuídos", players, column="upgrades"),
        ]
    )

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Great Coral Reef — Relatório Greedy × LongTerm</title><style>{css}</style></head><body>
<header><h1>Greedy × LongTerm</h1><p>Relatório de torneio e desempenho das cartas · {generated}</p></header>
<main class="container">
<div class="cards">
  <div class="metric"><b>{int(paired_stats['paired_games'])}</b><span>partidas pareadas</span></div>
  <div class="metric"><b>{pct(paired_stats['a_winrate'])}</b><span>vitórias do Greedy</span></div>
  <div class="metric"><b>{pct(paired_stats['b_winrate'])}</b><span>vitórias do LongTerm</span></div>
  <div class="metric"><b>{paired_stats['a_avg_score']-paired_stats['b_avg_score']:+.1f}</b><span>vantagem média de pontos do Greedy</span></div>
  <div class="metric"><b>{pct(paired_stats['residual_first_player_winrate'])}</b><span>vitórias de P1</span></div>
</div>
<section><h2>Resumo executivo</h2>
<p>O Greedy liderou o confronto pareado por <b>{(paired_stats['a_winrate']-paired_stats['b_winrate'])*100:.1f} pontos percentuais</b>
e marcou <b>{paired_stats['a_avg_score']-paired_stats['b_avg_score']:.1f} pontos a mais por partida</b>. A posição inicial continua relevante:
P1 venceu {pct(paired_stats['residual_first_player_winrate'])} das partidas.</p>
<div class="note">Associação não implica causalidade: uma carta pode aparecer mais em vitórias porque é forte, porque um agente melhor a escolhe ou porque depende de uma posição de jogo já favorável.</div>
</section>
<section><h2>Comparação pareada</h2><div class="table-wrap"><table><thead><tr><th>Agente</th><th>Vitórias</th><th>Score médio</th><th>Vitórias como P1</th><th>Vitórias como P2</th></tr></thead><tbody>{comparison_rows}</tbody></table></div>
<p class="method">200 seeds, jogadas nas duas ordens. Margem agregada por seed (Greedy − LongTerm): média {num(paired_stats['margin_mean'])}, mediana {num(paired_stats['margin_median'])}, intervalo interquartil {num(paired_stats['margin_q25'])} a {num(paired_stats['margin_q75'])}.</p></section>
<section><h2>Amostra detalhada para cartas</h2><div class="table-wrap"><table><thead><tr><th>Agente</th><th>Partidas</th><th>Vitórias</th><th>% vitória</th><th>Pontos médios</th><th>Mediana</th></tr></thead><tbody>{detailed_rows}</tbody></table></div>
<p class="method">{len(detailed)} partidas com assentos aleatorizados ({len(players)} observações jogador-partida). Artefato: <code>{html.escape(str(detailed_dir))}</code>.</p>
{reproducibility_note(detailed, enriched)}</section>
{balance_findings_section(enriched, paired_stats)}
{climate_and_duration_section(enriched)}
{population_section(enriched)}
{economy_section(enriched)}
{card_efficiency_section(enriched)}
{categories}
<section><h2>Como ler as tabelas</h2><ul>
<li><b>Total:</b> número de cópias construídas/jogadas; para Instintos e Upgrades, número de partidas em que a carta foi possuída.</li>
<li><b>Jogos com uso:</b> observações jogador-partida com pelo menos uma cópia.</li>
<li><b>Vitórias:</b> percentual de vitórias entre as observações que usaram a carta; empates permanecem no denominador.</li>
<li><b>Pontos médios:</b> score final médio do jogador nas partidas em que usou a carta.</li>
<li><b>Δ vitória e Δ pontos:</b> diferença contra a média de toda a amostra exibida. Use como sinal exploratório, não como efeito causal.</li>
<li><b>Amostra enriquecida:</b> estados finais e curvas de {len(enriched['games'])} partidas em <code>{html.escape(str(enriched_dir))}</code>.</li>
</ul></section>
<footer>Great Coral Reef · ruleset climate-era-v1 · relatório gerado por scripts/generate_tournament_report.py</footer>
</main></body></html>"""


def render_four_player_report(
    enriched: dict[str, pd.DataFrame], enriched_dir: Path, metadata: dict
) -> str:
    games = enriched["games"]
    players = enriched["players"]
    game_count = len(games)
    player_count = int(metadata.get("player_count", players["player"].nunique()))
    soil_supply = int(metadata.get("soil_supply", games["soil_supply"].iloc[0]))
    board = metadata.get("board", {"width": 16, "height": 16, "max_layers": 3})
    board_capacity = board["width"] * board["height"] * board["max_layers"]
    generated = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime(
        "%d/%m/%Y %H:%M BRT"
    )

    agent_rows = []
    agent_metrics = {}
    for agent, subset in players.groupby("agent"):
        wins = int(subset["won"].sum())
        metrics = {
            "appearances": len(subset),
            "wins": wins,
            "game_win_rate": wins / game_count,
            "avg_score": subset["score"].mean(),
            "median_score": subset["score"].median(),
        }
        agent_metrics[agent] = metrics
        agent_rows.append(
            f"<tr><td>{html.escape(display_name(agent))}</td>"
            f"<td>{metrics['appearances']}</td><td>{wins}</td>"
            f"<td>{pct(metrics['game_win_rate'])}</td>"
            f"<td>{num(metrics['avg_score'])}</td>"
            f"<td>{num(metrics['median_score'])}</td></tr>"
        )

    seat_rows = []
    seat_rates = {}
    for seat, subset in players.groupby("player"):
        rate = subset["won"].mean()
        seat_rates[int(seat)] = rate
        seat_rows.append(
            f"<tr><td>P{int(seat)}</td><td>{pct(rate)}</td>"
            f"<td>{num(subset['score'].mean())}</td>"
            f"<td>{num(subset['score'].median())}</td></tr>"
        )

    supply_rows = "".join(
        f"<tr><td>{html.escape(display_name(soil_id))}</td><td>{quantity}</td>"
        f"<td>{pct(quantity / soil_supply)}</td></tr>"
        for soil_id, quantity in metadata.get("soil_supply_by_type", {}).items()
    )
    strategy_gap = (
        agent_metrics.get("greedy", {}).get("game_win_rate", math.nan)
        - agent_metrics.get("longterm", {}).get("game_win_rate", math.nan)
    )
    score_gap = (
        agent_metrics.get("greedy", {}).get("avg_score", math.nan)
        - agent_metrics.get("longterm", {}).get("avg_score", math.nan)
    )
    soil_remaining = games["soil_remaining"].mean()
    soil_used_rate = 1 - soil_remaining / soil_supply
    best_seat = max(seat_rates, key=seat_rates.get)
    seat_spread = max(seat_rates.values()) - min(seat_rates.values())

    categories = "".join(
        [
            section_for_category("Corais presentes no fim", players, prefix="coral_"),
            section_for_category("Fauna sobrevivente no fim", players, prefix="fauna_"),
            section_for_category("Solos colocados", players, prefix="soil_"),
            section_for_category("Instintos possuídos", players, column="instincts"),
            section_for_category("Upgrades possuídos", players, column="upgrades"),
        ]
    )
    css = """
    :root{--ink:#12343b;--muted:#5f7479;--paper:#f4f9f8;--card:#fff;--reef:#007f78;
      --coral:#ed6a5a;--line:#d8e7e4;--good:#087f5b;--bad:#c92a2a}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
      font:15px/1.5 Inter,Segoe UI,Arial,sans-serif}header{background:linear-gradient(135deg,#073b4c,#007f78);
      color:white;padding:48px max(24px,calc((100% - 1180px)/2)) 40px}header h1{margin:0 0 8px;font-size:38px}
    header p{margin:0;opacity:.86}.container{max-width:1180px;margin:auto;padding:28px 20px 64px}
    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:0 0 28px}
    .metric,section{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 5px 18px #12343b0a}
    .metric{padding:18px}.metric b{display:block;font-size:27px;color:var(--reef)}.metric span{color:var(--muted)}
    section{padding:22px;margin:18px 0}h2{margin:0 0 14px;font-size:23px}h3{margin:22px 0 8px}
    .note{padding:13px 16px;border-left:4px solid var(--coral);background:#fff5f3;border-radius:6px;margin:14px 0}
    .table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:9px 10px;
      border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th{background:#edf6f4;color:#31565c}
    th:first-child,td:first-child{text-align:left}.name{font-weight:600}.positive{color:var(--good);font-weight:600}
    .negative{color:var(--bad);font-weight:600}.bar{display:inline-block;width:58px;height:7px;background:#e2eeec;
      border-radius:5px;margin-right:7px;overflow:hidden}.bar i{display:block;height:100%;background:var(--reef)}
    details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;font-weight:700;color:var(--reef)}
    .method{color:var(--muted);font-size:13px}code{background:#e8f1ef;padding:2px 5px;border-radius:4px}
    .chart{width:100%;min-width:560px;background:#fbfdfd;border:1px solid var(--line);border-radius:10px}
    .chart text{font-size:11px;fill:var(--muted)}.gridline{stroke:#dfeae8;stroke-width:1}
    .chart-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:18px}
    .histogram{height:205px;display:flex;align-items:flex-end;gap:8px;padding:15px 10px 0;border-bottom:1px solid var(--line)}
    .hist-col{height:185px;flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;min-width:45px}
    .hist-col i{display:block;width:70%;background:linear-gradient(#16a39a,#007f78);border-radius:5px 5px 0 0}
    .hist-col span,.hist-col small{font-size:11px;color:var(--muted)}.compact{margin-top:12px}.narrow{max-width:560px}
    .findings{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}.findings article{padding:15px;background:#f5faf9;border:1px solid var(--line);border-radius:10px}.findings b{color:var(--reef)}.findings p{margin:5px 0 0}
    footer{text-align:center;color:var(--muted);margin-top:28px}@media(max-width:650px){header h1{font-size:30px}}
    """
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Great Coral Reef — Relatório 4 jogadores / 80 solos</title><style>{css}</style></head><body>
<header><h1>Torneio de quatro jogadores</h1><p>Greedy × LongTerm · tabuleiro 16×16×3 · 80 solos · {generated}</p></header>
<main class="container"><div class="cards">
<div class="metric"><b>{game_count}</b><span>partidas</span></div>
<div class="metric"><b>{player_count}</b><span>jogadores por partida</span></div>
<div class="metric"><b>{pct(games['occupancy'].mean())}</b><span>ocupação final</span></div>
<div class="metric"><b>{num(games['turns'].mean())}</b><span>turnos médios</span></div>
<div class="metric"><b>{num(soil_remaining)}</b><span>solos restantes</span></div>
<div class="metric"><b>{pct(games['winner'].isna().mean())}</b><span>empates</span></div></div>
<section><h2>Configuração analisada</h2><p>As partidas usam {player_count} jogadores,
dois Greedy e dois LongTerm com assentos aleatorizados, tabuleiro de {board['width']}×{board['height']}×{board['max_layers']}
({board_capacity} células) e suprimento compartilhado de {soil_supply} solos.</p>
<div class="table-wrap narrow"><table><thead><tr><th>Solo</th><th>Quantidade</th><th>Proporção</th></tr></thead><tbody>{supply_rows}</tbody></table></div></section>
<section><h2>Desempenho por estratégia</h2><div class="table-wrap"><table><thead><tr><th>Agente</th><th>Participações</th><th>Vitórias</th><th>% das partidas</th><th>Pontos médios</th><th>Mediana</th></tr></thead><tbody>{''.join(agent_rows)}</tbody></table></div>
<p class="method">Como existem duas cópias de cada estratégia por partida, a taxa exibida é vitórias da estratégia divididas pelas {game_count} partidas.</p></section>
<section><h2>Efeito do assento</h2><div class="table-wrap"><table><thead><tr><th>Assento</th><th>Vitórias</th><th>Pontos médios</th><th>Mediana</th></tr></thead><tbody>{''.join(seat_rows)}</tbody></table></div></section>
<section><h2>Sinais principais de balanceamento</h2><div class="findings">
<article><b>Uso do suprimento</b><p>{pct(soil_used_rate)} dos 80 solos foram usados; sobraram {num(soil_remaining)} em média.</p></article>
<article><b>Diferença entre estratégias</b><p>Greedy ficou {strategy_gap * 100:+.1f} pp em vitórias e {score_gap:+.1f} pontos médios em relação ao LongTerm.</p></article>
<article><b>Viés de posição</b><p>P{best_seat} teve a maior taxa de vitória ({pct(seat_rates[best_seat])}); a amplitude entre assentos foi {seat_spread * 100:.1f} pp.</p></article>
<article><b>Povoamento</b><p>O recife terminou com {pct(games['occupancy'].mean())} das {board_capacity} células ocupadas.</p></article>
</div><div class="note">Associação não implica causalidade: cartas e recursos podem acompanhar uma posição favorável sem serem sua causa.</div></section>
{climate_and_duration_section(enriched)}
{population_section(enriched)}
{economy_section(enriched)}
{card_efficiency_section(enriched)}
{categories}
<section><h2>Metodologia</h2><p>Foram analisadas {game_count} partidas e {len(players)} observações jogador-partida.
As curvas usam o último estado de cada rodada. Os percentuais de vitória associados a cartas mantêm empates e derrotas no denominador.</p>
<p class="method">Artefato: <code>{html.escape(str(enriched_dir))}</code>. Seeds a partir de {metadata.get('seed_start', 1000)}. Assentos aleatorizados: {metadata.get('randomize_seats', False)}.</p></section>
<footer>Great Coral Reef · relatório de 4 jogadores / 80 solos · scripts/generate_tournament_report.py</footer>
</main></body></html>"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera relatório HTML do torneio de quatro jogadores."
    )
    parser.add_argument("--games", type=int, default=100, help="Partidas do torneio.")
    parser.add_argument(
        "--enriched-dir",
        type=Path,
        help="Diretório com métricas espaciais, econômicas e curvas por rodada.",
    )
    parser.add_argument("--output", type=Path, help="Caminho do HTML de saída.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.enriched_dir:
        enriched_dir = args.enriched_dir.resolve()
    else:
        from collect_enriched_tournament import collect

        enriched_dir = collect(args.games).resolve()
    enriched = load_enriched(enriched_dir)
    metadata = json.loads((enriched_dir / "metadata.json").read_text(encoding="utf-8"))
    output = (args.output or (enriched_dir / "report.html")).resolve()
    output.write_text(
        render_four_player_report(enriched, enriched_dir, metadata),
        encoding="utf-8",
    )
    print(f"Tournament artifact: {enriched_dir}")
    print(f"HTML report: {output}")


if __name__ == "__main__":
    main()
