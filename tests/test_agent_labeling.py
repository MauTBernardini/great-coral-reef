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
        agent_p3="random",
        agent_p4="greedy",
        randomize_seats=randomize_seats,
        corals_path=str(ROOT / "configs" / "corals.yaml"),
        soils_path=str(ROOT / "configs" / "soils.yaml"),
        balance_rules_path=str(ROOT / "configs" / "balance_rules.yaml"),
        climate_path=str(ROOT / "configs" / "climate.yaml"),
        version_path=str(ROOT / "configs" / "version.yaml"),
        show_progress=False,
        save_results=False,
        max_rounds=5,
    )


def test_results_record_agent_per_seat():
    df = run_tournament(_config("greedy", "longterm", games=6, randomize_seats=False))
    assert all(f"p{pid}_agent" in df.columns for pid in range(1, 5))
    assert (df["p1_agent"] == "greedy").all()
    assert (df["p2_agent"] == "longterm").all()
    assert (df["p3_agent"] == "random").all()
    assert (df["p4_agent"] == "greedy").all()


def test_randomized_seats_preserve_all_four_participants():
    df = run_tournament(_config("greedy", "longterm", games=6, randomize_seats=True))
    for _, row in df.iterrows():
        assert sorted(row[f"p{pid}_agent"] for pid in range(1, 5)) == [
            "greedy",
            "greedy",
            "longterm",
            "random",
        ]

    by_agent = summarize_by_agent(df)
    assert set(by_agent) == {"greedy", "longterm", "random"}
    assert by_agent["greedy"]["games"] == 12
    assert by_agent["longterm"]["games"] == 6
    assert by_agent["random"]["games"] == 6
