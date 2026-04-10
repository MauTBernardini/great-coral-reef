import json
from pathlib import Path
from uuid import uuid4

from reef_game.simulation.tournament import TournamentConfig, run_tournament


def test_tournament_saves_results_with_version_metadata():
    root = Path(__file__).resolve().parents[1]
    output_root = root / "tests" / "_artifacts_tmp" / uuid4().hex
    config = TournamentConfig(
        games=2,
        corals_path=str(root / "configs" / "corals.yaml"),
        balance_rules_path=str(root / "configs" / "balance_rules.yaml"),
        climate_path=str(root / "configs" / "climate.yaml"),
        version_path=str(root / "configs" / "version.yaml"),
        output_dir=str(output_root / "tournaments"),
        show_progress=False,
        save_results=True,
    )

    df = run_tournament(config)

    artifact_dir = Path(df.attrs["artifact_dir"])
    results_path = artifact_dir / "results.csv"
    metadata_path = artifact_dir / "metadata.json"

    assert results_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["version"]["code_version"] == "0.1.0"
    assert metadata["tournament_config"]["games"] == 2
