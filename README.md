# Great Coral Reef

Engine determinística e simulador de um jogo de tabuleiro competitivo para dois
jogadores. O projeto separa as regras do jogo do conteúdo configurável para permitir
partidas reproduzíveis por seed, torneios automatizados e análises de balanceamento.

Versão atual: `0.1.0`

Ruleset: `climate-era-v1`

## Estado atual

O jogo usa um tabuleiro tridimensional de 4 x 4 x 3 camadas. Os jogadores constroem
solos e corais, abrigam fauna, produzem recursos e disputam pontos enquanto o clima
avança por três eras.

Estão implementados:

- recursos de Sol, Plâncton e O₂;
- 8 tipos de coral, com custos, produção e regras de pontuação próprias;
- 4 tipos de solo, com produção e efeitos sobre a coluna;
- 15 tipos de fauna, incluindo habitat, predadores, cardumes e movimento;
- 10 cartas de Instinto, usadas como objetivos secretos;
- 8 Upgrades com efeitos permanentes;
- ponds, formadas ao fechar ciclos de corais numa mesma camada;
- baralho climático com três eras e progressão de temperatura e pH;
- agentes `random`, `greedy` e `longterm`;
- partidas simples, torneios, torneios pareados e telemetria por turno.

Os textos completos dos eventos climáticos já estão configurados, mas atualmente o
motor aplica apenas suas alterações de temperatura e pH. Efeitos como branqueamento,
algas, cura e tempestades ainda não foram implementados.

## Requisitos

- Python 3.12.x
- pip

O projeto está fixado na série Python 3.12. Em sistemas com várias versões instaladas,
use explicitamente o interpretador 3.12.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Linux e macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Confira o ambiente ativo antes de executar o projeto:

```bash
python --version
# Python 3.12.x
```

## Uso

### Executar uma partida

```powershell
python scripts/run_single_game.py
```

### Executar um torneio

```powershell
python scripts/run_tournament.py --games 50 --p1 greedy --p2 longterm
```

Agentes aceitos: `random`, `greedy` e `longterm`.

Para reduzir o viés da ordem dos jogadores, é possível aleatorizar os assentos:

```powershell
python scripts/run_tournament.py --games 200 --p1 greedy --p2 longterm --randomize-seats
```

Para uma comparação controlada, cada seed pode ser jogada nas duas ordens:

```powershell
python scripts/run_tournament.py --games 200 --p1 greedy --p2 longterm --paired
```

Os resultados são gravados em `artifacts/tournaments/`. Dependendo das opções de
telemetria, os arquivos de estados detalhados podem ultrapassar 100 MB.

### Executar os testes

```powershell
python -m pytest -q
```

### Executar o lint

```powershell
python -m ruff check src scripts tests
```

## Fluxo de uma rodada

Durante seu turno, um jogador pode comprar cartas, colocar solo, construir coral,
jogar ou mover fauna, usar determinadas habilidades ou passar. Quando ambos passam:

1. uma nova rodada é iniciada;
2. solos, corais e fauna produzem recursos;
3. a manutenção de fauna é resolvida com o O₂ disponível;
4. uma carta de clima da era atual é aplicada;
5. temperatura, pH e transições de era são atualizados.

A partida termina ao atingir um limite climático, esgotar o baralho de clima ou
alcançar o limite configurado de rodadas. A pontuação combina corais, fauna e
Instintos.

## Estrutura do repositório

```text
configs/                  Conteúdo e parâmetros de balanceamento em YAML
notebooks/                Análises de torneios, fauna, cartas e estados
scripts/                  Entradas para partidas, torneios e sweeps
src/reef_game/agents/     Agentes automáticos
src/reef_game/content/    Carregamento das configurações
src/reef_game/engine/     Estado, regras, validação, produção e pontuação
src/reef_game/simulation/ Runner, telemetria, métricas e torneios
tests/                    Testes unitários e de integração
```

As principais configurações ficam em:

- `configs/balance_rules.yaml`: tabuleiro, recursos iniciais e limites climáticos;
- `configs/corals.yaml`: corais e quantidades do baralho;
- `configs/fauna.yaml`: fauna e habilidades;
- `configs/soils.yaml`: solos e suprimento;
- `configs/instincts.yaml`: objetivos secretos;
- `configs/upgrades.yaml`: melhorias permanentes;
- `configs/climate.yaml`: cartas e eras climáticas.

## Reprodutibilidade e artefatos

Montagem de baralhos, distribuição inicial e agentes aleatórios usam seeds explícitas.
Torneios exportam resultados agregados em CSV e, quando habilitado, telemetria em CSV
e JSONL. O diretório `artifacts/` contém saídas geradas e não é versionado pelo Git.

## Próximas frentes

- implementar os efeitos mecânicos descritos nas cartas climáticas;
- medir e reduzir a vantagem do primeiro jogador com torneios pareados;
- concluir habilidades ainda parciais, como Generalist Diet e a anêmona do Clownfish;
- melhorar a escolha estratégica de Instintos e Upgrades pelos agentes;
- atualizar o modelo de cópia de estado para reduzir o custo de simulações maiores;
- preparar uma interface compatível com Gymnasium ou PettingZoo.
