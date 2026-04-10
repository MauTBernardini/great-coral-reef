import random

from .base import BaseAgent


class RandomAgent(BaseAgent):
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_action(self, state, legal_actions):
        return self.rng.choice(legal_actions)
