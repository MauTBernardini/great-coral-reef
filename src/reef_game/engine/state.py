from .models import Cell, GameState


def get_cell(board, position) -> Cell:
    return board.cells[position]


def occupied_cells_count(state: GameState) -> int:
    return sum(1 for cell in state.board.cells.values() if cell.occupant is not None)


def board_capacity(state: GameState) -> int:
    return len(state.board.cells)
