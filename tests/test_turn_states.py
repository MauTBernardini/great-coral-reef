import json
from pathlib import Path
from uuid import uuid4

from reef_game.engine.actions import PlaceCoralAction
from reef_game.engine.enums import PlayerId
from reef_game.engine.transitions import apply_action
from reef_game.simulation.telemetry import GameTelemetry
from reef_game.simulation.tournament import TournamentConfig, run_tournament


def test_snapshot_captures_full_per_player_state(soiled_state):
    tel = GameTelemetry()
    tel.record_state(soiled_state)
    state = apply_action(soiled_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))
    tel.record_state(state)

    snap = tel.states[-1]
    # ecossistema
    assert "temperature" in snap and "remaining_climate_cards" in snap and "current_era" in snap
    p1 = snap["players"][1]
    # recursos, produzido, usado
    assert p1["resources"]["sun"] == 8  # 10 - 2 do brain
    assert p1["spent"]["sun"] == 2
    assert set(p1["produced"]) == {"sun", "plankton"}
    # board do player e mao
    assert p1["board"] == [{"coral_id": "grooved_brain_coral", "position": [0, 0, 0]}]
    assert p1["corals_by_layer"][0] == 1
    assert p1["hand"] == [] and p1["hand_size"] == 0


def test_to_rows_is_long_format_per_player(initial_state):
    tel = GameTelemetry()
    tel.record_state(initial_state)
    tel.record_state(initial_state)
    rows = tel.to_rows()
    # 2 snapshots x 2 jogadores
    assert len(rows) == 4
    cols = set(rows[0])
    for expected in ("seed", "turn", "player", "sun", "plankton", "produced_sun",
                     "spent_sun", "score", "hand_size", "corals_z0", "temperature"):
        assert expected in cols


def test_produced_resources_accumulates_over_production_phases(initial_state):
    from reef_game.engine.enums import ResourceType
    from reef_game.engine.models import PlacedCoral
    from reef_game.engine.production import resolve_production

    top = initial_state.board.max_layers - 1
    for x in range(3):
        pos = (x, 0, top)
        initial_state.board.cells[pos].occupant = PlacedCoral(
            instance_id=f"e{x}", coral_id="elkhorn", owner=PlayerId.P1, position=pos
        )
    resolve_production(initial_state)
    resolve_production(initial_state)
    assert initial_state.players[PlayerId.P1].produced_resources[ResourceType.SUN] == 2


def test_tournament_writes_turn_state_files():
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

    turn_csv = artifact_dir / "turn_states.csv"
    turn_jsonl = artifact_dir / "turn_states.jsonl"
    assert turn_csv.exists()
    assert turn_jsonl.exists()

    lines = turn_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0
    first = json.loads(lines[0])
    assert "players" in first and "temperature" in first
    assert set(first["players"]) == {"1", "2"}  # JSON keys are strings
