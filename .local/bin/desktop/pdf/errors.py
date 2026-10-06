"""Erreurs du moteur : le message est déjà lisible et traduit (affiché tel quel)."""


class OpError(Exception):
    pass


class PasswordError(OpError):
    """Mot de passe requis (wrong=False) ou incorrect (wrong=True)."""

    def __init__(self, msg, wrong=False):
        super().__init__(msg)
        self.wrong = wrong
