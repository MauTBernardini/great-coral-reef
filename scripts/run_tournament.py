from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import typer

from reef_game.simulation.tournament import (
    TournamentConfig,
    run_paired_tournament,
    run_tournament,
    summarize_by_agent,
    summarize_paired,
    summarize_tournament,
)

app = typer.Typer()


@app.command()
def main(
    games: int = 50,
    p1: str = "random",
    p2: str = "greedy",
    no_progress: bool = False,
    paired: bool = False,
    randomize_seats: bool = False,
):
    config = TournamentConfig(
        games=games,
        corals_path=str(ROOT / "configs" / "corals.yaml"),
        soils_path=str(ROOT / "configs" / "soils.yaml"),
        flora_path=str(ROOT / "configs" / "flora.yaml"),
        balance_rules_path=str(ROOT / "configs" / "balance_rules.yaml"),
        climate_path=str(ROOT / "configs" / "climate.yaml"),
        version_path=str(ROOT / "configs" / "version.yaml"),
        output_dir=str(ROOT / "artifacts" / "tournaments"),
        agent_p1=p1,
        agent_p2=p2,
        show_progress=not no_progress,
        randomize_seats=randomize_seats,
    )

    if paired:
        # Comparação justa A(p1) vs B(p2): cada seed jogado nas duas ordens.
        df = run_paired_tournament(config)
        s = summarize_paired(df)
        print(f"Comparação posição-controlada: {s['agent_a']} (A) vs {s['agent_b']} (B)")
        print(f"  jogos (2x seeds): {s['paired_games']}")
        print(
            f"  winrate A={s['a_winrate']:.1%}  B={s['b_winrate']:.1%}  "
            f"empate={s['draw_rate']:.1%}"
        )
        print(f"  score medio A={s['a_avg_score']:.1f}  B={s['b_avg_score']:.1f}")
        print(
            f"  seeds em que A>B: {s['seeds_a_better']:.1%}  B>A: {s['seeds_b_better']:.1%}"
        )
        print(
            f"  (efeito de posicao residual: 1o jogador vence "
            f"{s['residual_first_player_winrate']:.1%})"
        )
    else:
        df = run_tournament(config)
        print(f"Agentes: P1={p1}  P2={p2}  (randomize_seats={randomize_seats})")
        print(df.head().to_string(index=False))
        print("Resumo por posicao:", summarize_tournament(df))
        print("Resumo por AGENTE:", summarize_by_agent(df))

    if "artifact_dir" in df.attrs:
        print(f"Saved artifacts to: {df.attrs['artifact_dir']}")


if __name__ == "__main__":
    app()
