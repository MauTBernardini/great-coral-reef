from pathlib import Path

from reef_game.simulation.tournament import (
    TournamentConfig,
    run_tournament,
    summarize_by_agent,
)

ROOT = Path(__file__).resolve().parents[1]


def _config(p1, p2, games, randomize_seats):
    return TournamentConfig(
        games=games,
        agent_p1=p1,
        agent_p2=p2,
        randomize_seats=randomize_seats,
        corals_path=str(ROOT / "configs" / "corals.yaml"),
        soils_path=str(ROOT / "configs" / "soils.yaml"),
        flora_path=str(ROOT / "configs" / "flora.yaml"),
        balance_rules_path=str(ROOT / "configs" / "balance_rules.yaml"),
        climate_path=str(ROOT / "configs" / "climate.yaml"),
        version_path=str(ROOT / "configs" / "version.yaml"),
        show_progress=False,
        save_results=False,
    )


def test_results_record_agent_per_seat():
    df = run_tournament(_config("greedy", "longterm", games=6, randomize_seats=False))
    assert "p1_agent" in df.columns and "p2_agent" in df.columns
    # cadeiras fixas: P1 sempre greedy, P2 sempre longterm
    assert (df["p1_agent"] == "greedy").all()
    assert (df["p2_agent"] == "longterm").all()


def test_randomized_seats_put_each_agent_in_both_seats():
    df = run_tournament(_config("greedy", "longterm", games=30, randomize_seats=True))
    # ambos os agentes aparecem em ambas as cadeiras
    assert set(df["p1_agent"]) == {"greedy", "longterm"}
    assert set(df["p2_agent"]) == {"greedy", "longterm"}

    by_agent = summarize_by_agent(df)
    assert set(by_agent) == {"greedy", "longterm"}
    for agent in ("greedy", "longterm"):
        assert by_agent[agent]["games_as_p1"] > 0
        assert by_agent[agent]["games_as_p2"] > 0
        # cada agente joga em ~todas as partidas (uma cadeira por partida)
        assert by_agent[agent]["games"] == 30
