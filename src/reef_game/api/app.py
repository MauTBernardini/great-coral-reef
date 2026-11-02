from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from reef_game.engine.enums import ActionType
from reef_game.engine.models import MAX_HAND_SIZE, STARTING_HAND_SIZE

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
PROJECT_ROOT = Path(os.environ.get("REEF_GAME_ROOT", PACKAGE_DIR.parents[2])).resolve()
CONFIG_DIR = PROJECT_ROOT / "configs"
TOURNAMENT_DIR = PROJECT_ROOT / "artifacts" / "tournaments"

CARD_SOURCES: dict[str, tuple[str, str, str, str]] = {
    "coral": ("corals.yaml", "corals", "coral_id", "Corais"),
    "fauna": ("fauna.yaml", "fauna", "fauna_id", "Fauna"),
    "soil": ("soils.yaml", "soils", "soil_id", "Solos"),
    "instinct": ("instincts.yaml", "instincts", "instinct_id", "Instintos"),
    "upgrade": ("upgrades.yaml", "upgrades", "upgrade_id", "Melhorias"),
    "climate": ("climate.yaml", "deck", "card_id", "Clima"),
}

CARD_TYPE_ALIASES = {
    "corals": "coral",
    "faunas": "fauna",
    "soils": "soil",
    "solos": "soil",
    "instincts": "instinct",
    "upgrades": "upgrade",
    "climates": "climate",
}

GAME_RULES = [
    {
        "id": "flow",
        "title": "Fluxo da partida",
        "summary": "Os jogadores alternam ações até o encerramento determinado pelo clima.",
        "items": [
            "Cada jogador começa com uma mão de cartas e recursos iniciais.",
            "Em seu turno, escolha uma ação válida e resolva todos os seus efeitos.",
            "Ao fim da rodada, o clima altera pH, temperatura e condições do recife.",
            "A partida termina pelas condições de fim configuradas no cenário.",
        ],
    },
    {
        "id": "construction",
        "title": "Construção do recife",
        "summary": "Solos sustentam corais; corais criam habitat, produção e pontos.",
        "items": [
            "Respeite custos, requisitos de camada e espaços disponíveis no tabuleiro.",
            "A posição e a camada influenciam ocupação, produção e pontuação.",
            "Melhorias podem modificar limites, custos ou eficiência do recife.",
        ],
    },
    {
        "id": "fauna",
        "title": "Fauna e instintos",
        "summary": "A fauna recompensa habitats adequados e combinações estratégicas.",
        "items": [
            "Cartas de fauna exigem condições específicas do recife.",
            "Instintos alteram decisões e criam efeitos táticos ou permanentes.",
            "Leia os campos de requisitos e efeitos de cada carta no catálogo.",
        ],
    },
    {
        "id": "climate",
        "title": "Clima e ambiente",
        "summary": "pH e temperatura pressionam o ecossistema durante a partida.",
        "items": [
            "Cartas climáticas formam a curva ambiental de cada partida.",
            "Mudanças ambientais podem reduzir produção ou afetar a sobrevivência.",
            "Estratégias resilientes equilibram crescimento, diversidade e recursos.",
        ],
    },
    {
        "id": "scoring",
        "title": "Pontuação e vitória",
        "summary": "Vence quem obtiver mais pontos após a resolução do fim da partida.",
        "items": [
            "Some os pontos de cartas, camadas, fauna e demais bônus ativos.",
            "Os critérios de desempate seguem a configuração do motor de jogo.",
            "Relatórios de torneio mostram médias e taxas de vitória por estratégia.",
        ],
    },
]

app = FastAPI(
    title="Great Coral Reef API",
    version="0.1.0",
    description="Catálogo de cartas, regras e resultados de torneios do Great Coral Reef.",
)


def _load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"Configuração indisponível: {filename}")
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _normalize_type(card_type: str) -> str:
    normalized = card_type.casefold().strip()
    normalized = CARD_TYPE_ALIASES.get(normalized, normalized)
    if normalized not in CARD_SOURCES:
        raise HTTPException(status_code=404, detail=f"Tipo de carta desconhecido: {card_type}")
    return normalized


def _card_summary(card_type: str, card: dict[str, Any]) -> dict[str, Any]:
    _, _, id_field, label = CARD_SOURCES[card_type]
    identifier = str(card.get(id_field, card.get("id", "")))
    return {
        "id": identifier,
        "type": card_type,
        "type_label": label,
        "name": card.get("name", identifier.replace("_", " ").title()),
        "cost": card.get("cost"),
        "points": card.get("points", card.get("victory_points")),
        "description": card.get("description", card.get("effect", "")),
        "data": card,
    }


@lru_cache(maxsize=1)
def _all_cards() -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for card_type, (filename, collection_key, _, _) in CARD_SOURCES.items():
        raw_cards = _load_yaml(filename).get(collection_key, [])
        result[card_type] = [_card_summary(card_type, card) for card in raw_cards]
    return result


def _safe_tournament_directory(tournament_id: str) -> Path:
    root = TOURNAMENT_DIR.resolve()
    candidate = (root / tournament_id).resolve()
    if candidate.parent != root or not candidate.is_dir():
        raise HTTPException(status_code=404, detail="Torneio não encontrado")
    return candidate


def _tournament_metadata(directory: Path) -> dict[str, Any] | None:
    metadata_path = directory / "metadata.json"
    if not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    files = sorted(path.name for path in directory.iterdir() if path.is_file())
    reports = [name for name in files if name.casefold().endswith(".html")]
    version = metadata.get("version")
    if isinstance(version, dict):
        version = version.get("code_version", version.get("ruleset_version"))
    config = metadata.get("config", metadata.get("tournament_config", {}))
    return {
        "id": directory.name,
        "mode": metadata.get("mode", "tournament"),
        "saved_at": metadata.get(
            "saved_at", metadata.get("saved_at_utc", metadata.get("created_at"))
        ),
        "version": version,
        "config": config,
        "agents": [
            agent
            for agent in (
                config.get("agent_p1", metadata.get("summary", {}).get("agent_a")),
                config.get("agent_p2", metadata.get("summary", {}).get("agent_b")),
            )
            if agent
        ],
        "summary": metadata.get("summary", {}),
        "files": files,
        "report_url": (
            f"/api/tournaments/{directory.name}/report" if reports else None
        ),
    }


@app.get("/api/health", tags=["Sistema"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "great-coral-reef"}


@app.get("/api/game", tags=["Jogo"])
def game_information() -> dict[str, Any]:
    cards = _all_cards()
    balance = _load_yaml("balance_rules.yaml")
    return {
        "name": "Great Coral Reef",
        "version": app.version,
        "description": app.description,
        "starting_hand_size": STARTING_HAND_SIZE,
        "max_hand_size": MAX_HAND_SIZE,
        "actions": [action.value for action in ActionType],
        "card_counts": {card_type: len(items) for card_type, items in cards.items()},
        "total_cards": sum(len(items) for items in cards.values()),
        "rules_sections": len(GAME_RULES),
        "player_count": balance.get("players", {}).get("count", 4),
        "board": balance.get("board", {}),
    }


@app.get("/api/cards/types", tags=["Cartas"])
def card_types() -> list[dict[str, Any]]:
    cards = _all_cards()
    return [
        {"id": card_type, "label": source[3], "count": len(cards[card_type])}
        for card_type, source in CARD_SOURCES.items()
    ]


@app.get("/api/cards", tags=["Cartas"])
def list_cards(
    card_type: str | None = Query(default=None, alias="type"),
    search: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    cards_by_type = _all_cards()
    if card_type:
        normalized = _normalize_type(card_type)
        cards = list(cards_by_type[normalized])
    else:
        cards = [card for group in cards_by_type.values() for card in group]

    if search:
        needle = search.casefold().strip()
        cards = [
            card
            for card in cards
            if needle in json.dumps(card, ensure_ascii=False).casefold()
        ]
    return {"total": len(cards), "items": cards[:limit]}


@app.get("/api/cards/{card_type}/{card_id}", tags=["Cartas"])
def get_card(card_type: str, card_id: str) -> dict[str, Any]:
    normalized = _normalize_type(card_type)
    for card in _all_cards()[normalized]:
        if card["id"].casefold() == card_id.casefold():
            return card
    raise HTTPException(status_code=404, detail="Carta não encontrada")


@app.get("/api/rules", tags=["Regras"])
def list_rules() -> dict[str, Any]:
    return {
        "sections": GAME_RULES,
        "actions": [action.value for action in ActionType],
        "limits": {"starting_hand": STARTING_HAND_SIZE, "max_hand": MAX_HAND_SIZE},
    }


@app.get("/api/rules/{section_id}", tags=["Regras"])
def get_rule(section_id: str) -> dict[str, Any]:
    for section in GAME_RULES:
        if section["id"] == section_id:
            return section
    raise HTTPException(status_code=404, detail="Seção de regra não encontrada")


@app.get("/api/tournaments", tags=["Torneios"])
def list_tournaments() -> dict[str, Any]:
    if not TOURNAMENT_DIR.is_dir():
        return {"total": 0, "items": []}
    items = [
        metadata
        for directory in TOURNAMENT_DIR.iterdir()
        if directory.is_dir() and (metadata := _tournament_metadata(directory)) is not None
    ]
    items.sort(key=lambda item: (item.get("saved_at") or "", item["id"]), reverse=True)
    return {"total": len(items), "items": items}


@app.get("/api/tournaments/{tournament_id}", tags=["Torneios"])
def get_tournament(
    tournament_id: str,
    sample_rows: int = Query(default=5, ge=0, le=50),
) -> dict[str, Any]:
    directory = _safe_tournament_directory(tournament_id)
    metadata = _tournament_metadata(directory)
    if metadata is None:
        raise HTTPException(status_code=404, detail="Metadados do torneio não encontrados")

    samples: dict[str, list[dict[str, str]]] = {}
    if sample_rows:
        for csv_path in sorted(directory.glob("*.csv")):
            try:
                with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                    samples[csv_path.name] = list(csv.DictReader(stream))[:sample_rows]
            except (OSError, csv.Error, UnicodeDecodeError):
                samples[csv_path.name] = []
    return {**metadata, "samples": samples}


@app.get("/api/tournaments/{tournament_id}/report", tags=["Torneios"])
def tournament_report(tournament_id: str) -> FileResponse:
    directory = _safe_tournament_directory(tournament_id)
    reports = sorted(directory.glob("*.html"))
    if not reports:
        raise HTTPException(status_code=404, detail="Relatório HTML não encontrado")
    return FileResponse(reports[0], media_type="text/html")


@app.get("/api/tournaments/{tournament_id}/files/{filename}", tags=["Torneios"])
def tournament_file(tournament_id: str, filename: str) -> FileResponse:
    directory = _safe_tournament_directory(tournament_id)
    path = (directory / filename).resolve()
    if path.parent != directory or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(path, filename=path.name)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
