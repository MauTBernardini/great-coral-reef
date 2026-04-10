from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import typer

from reef_game.simulation.tournament import TournamentConfig, run_tournament, summarize_tournament

app = typer.Typer()


@app.command()
def main(games: int = 50, p1: str = "random", p2: str = "greedy", no_progress: bool = False):
    config = TournamentConfig(
        games=games,
        corals_path=str(ROOT / "configs" / "corals.yaml"),
        balance_rules_path=str(ROOT / "configs" / "balance_rules.yaml"),
        climate_path=str(ROOT / "configs" / "climate.yaml"),
        version_path=str(ROOT / "configs" / "version.yaml"),
        output_dir=str(ROOT / "artifacts" / "tournaments"),
        agent_p1=p1,
        agent_p2=p2,
        show_progress=not no_progress,
    )
    df = run_tournament(config)
    print(df.head().to_string(index=False))
    print(summarize_tournament(df))
    if "artifact_dir" in df.attrs:
        print(f"Saved artifacts to: {df.attrs['artifact_dir']}")


if __name__ == "__main__":
    app()
