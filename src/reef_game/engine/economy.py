"""Resource-cost modifiers from coral abilities and soil tiles.

Kept in one place so validation (affordability) and execution (deduction) always
agree on what a placement actually costs.
"""

from .enums import ResourceType

GROOVED_BRAIN_ID = "grooved_brain_coral"


def effective_cost(state, coral, position) -> dict:
    """The real resource cost to place ``coral`` at ``position``.

    Sun discounts (stack, floored at 0):
      * Grooved Brain Coral: the coral placed directly on top of it costs 1 Sun less.
      * Rocky Reef soil: corals built in that column cost 1 Sol less (per its
        ``coral_cost_reduction``).
    """
    values = dict(coral.cost.values)
    x, y, z = position
    sun_reduction = 0

    if z > 0:
        below = state.board.cells.get((x, y, z - 1))
        below_is_brain = (
            below is not None
            and below.occupant is not None
            and below.occupant.coral_id == GROOVED_BRAIN_ID
        )
        if below_is_brain:
            sun_reduction += 1

    base = state.board.cells.get((x, y, 0))
    if base is not None and base.soil is not None:
        soil = state.available_soils.get(base.soil.soil_id)
        if soil is not None:
            sun_reduction += soil.coral_cost_reduction

    if sun_reduction and ResourceType.SUN in values:
        values[ResourceType.SUN] = max(0, values[ResourceType.SUN] - sun_reduction)

    return values
