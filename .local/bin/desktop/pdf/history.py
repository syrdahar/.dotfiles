"""Historique annuler / rétablir par instantanés (pur Python : pas de cycle avec des objets Qt)."""
import copy


class History:
    def __init__(self, state, on_change=None):
        self.states, self.pos, self.clean = [copy.deepcopy(state)], 0, 0
        self.on_change = on_change or (lambda: None)

    def push(self, state):
        self.states = self.states[: self.pos + 1] + [copy.deepcopy(state)]
        self.pos += 1
        if self.clean > self.pos:
            self.clean = -1
        self.on_change()

    def undo(self):
        if not self.can_undo():
            return None
        self.pos -= 1
        self.on_change()
        return copy.deepcopy(self.states[self.pos])

    def redo(self):
        if not self.can_redo():
            return None
        self.pos += 1
        self.on_change()
        return copy.deepcopy(self.states[self.pos])

    def current(self):
        return copy.deepcopy(self.states[self.pos])

    def can_undo(self):
        return self.pos > 0

    def can_redo(self):
        return self.pos < len(self.states) - 1

    def is_clean(self):
        return self.pos == self.clean

    def set_clean(self):
        self.clean = self.pos
        self.on_change()
