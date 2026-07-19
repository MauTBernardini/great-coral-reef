from abc import ABC, abstractmethod


class BaseAgent(ABC):
    @abstractmethod
    def choose_action(self, state, legal_actions):
        raise NotImplementedError

    def choose_card(self, state, player_id, offer):
        """Escolhe 1 carta da oferta de pond (Instinto OU Upgrade). Padrão simples que
        alterna entre os tipos para exercitar ambos: pega Upgrade quando o jogador tem
        menos upgrades que instintos-extra; senão pega Instinto."""
        instincts = offer.get("instincts") or []
        upgrades = offer.get("upgrades") or []
        player = state.players[player_id]
        extra_instincts = max(0, len(player.instinct_cards) - 1)
        if upgrades and len(player.upgrade_cards) <= extra_instincts:
            return upgrades[0]
        if instincts:
            return instincts[0]
        return upgrades[0] if upgrades else None
