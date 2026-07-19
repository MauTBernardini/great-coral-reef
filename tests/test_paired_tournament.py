from pathlib import Path

from reef_game.simulation.tournament import (
    TournamentConfig,
    run_paired_tournament,
    summarize_paired,
)

ROOT = Path(__file__).resolve().parents[1]


def _config(p1, p2, games):
    return TournamentConfig(
        games=games,
        agent_p1=p1,
        agent_p2=p2,
        corals_path=str(ROOT / "configs" / "corals.yaml"),
        soils_path=str(ROOT / "configs" / "soils.yaml"),
        flora_path=str(ROOT / "configs" / "flora.yaml"),
        balance_rules_path=str(ROOT / "configs" / "balance_rules.yaml"),
        climate_path=str(ROOT / "configs" / "climate.yaml"),
        version_path=str(ROOT / "configs" / "version.yaml"),
        show_progress=False,
        save_results=False,
    )


def test_paired_runs_both_orderings_per_seed():
    df = run_paired_tournament(_config("greedy", "longterm", games=5))
    assert len(df) == 5
    for col in ("a_as_p1_score", "a_as_p2_score", "b_as_p1_score", "b_as_p2_score"):
        assert col in df.columns
    summary = summarize_paired(df)
    assert summary["paired_games"] == 10
    total = summary["a_winrate"] + summary["b_winrate"] + summary["draw_rate"]
    assert abs(total - 1.0) < 1e-9


def test_identical_agents_are_balanced_after_controlling_for_position():
    # greedy vs greedy: mesma habilidade -> winrates de A e B devem ficar ~parelhos,
    # mesmo que a posição sozinha decida cada jogo.
    df = run_paired_tournament(_config("greedy", "greedy", games=30))
    summary = summarize_paired(df)
    assert abs(summary["a_winrate"] - summary["b_winrate"]) < 0.15
