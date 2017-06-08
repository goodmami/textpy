
from grammarian.scanners import Scanner, Nonterminal

class Grammar(Scanner):
    def __init__(self, start='Start'):
        self.start = start
        self._grm = {}

    def __setitem__(self, identifier, scanner):
        if not isinstance(scanner, Scanner):
            raise TypeError('Values must be Scanner objects')
        self._grm[identifier] = scanner
        scanner.set_grammar(self)

    def __getitem__(self, identifier):
        return self._grm[identifier]

    def nonterminal(self, identifier):
        return Nonterminal(self._grm, identifier)

    def _scan(self, s, pos):
        scanner = self._grm[self.start]
        return scanner._scan(s, pos)

    def update_actions(self, items=None, **kwargs):
        print(self._grm)
        if items is None:
            items = []
        elif hasattr(items, 'items'):
            items = list(items.items())
        items.extend(kwargs.items())

        pairs = []
        for identifier, action in items:
            if not callable(action):
                raise ValueError(
                    'action for {} is not callable'.format(identifier)
                )
            scanner = self._grm[identifier]
            pairs.append((scanner, action))

        for scanner, action in pairs:
            scanner.action = action
