from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    def choose_action(self, state, legal_actions):
        raise NotImplementedError

    def choose_instinct(self, state, player_id, options):
        """Escolhe 1 das cartas de Instinto oferecidas. Padrão: a primeira do baralho
        (que já vem embaralhado por seed, então varia entre partidas)."""
        return options[0] if options else None
