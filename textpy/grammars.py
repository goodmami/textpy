
from textpy.scanners import *
from textpy import io
# from textpy.scanners import Scanner, Nonterminal

class Grammar(Scanner):
    GrammarReader = io.GrammarReader
    def __init__(self, definition=None, actions=None, start='Start'):
        self._grm = {}
        self._description = {}
        if definition is not None:
            self.read(definition)
        if actions is not None:
            self.update_actions(actions)
        self.start = start

    def __str__(self):
        return '\n'.join(n + ' = ' + str(r) for n, r in self._grm.items())

    def __setitem__(self, identifier, scanner):
        if not isinstance(scanner, Scanner):
            raise TypeError('Values must be Scanner objects')
        self._grm[identifier] = scanner

    def __getitem__(self, identifier):
        return self._grm[identifier]

    def nonterminal(self, identifier):
        return Nonterminal(self._grm, identifier)

    # def _scan(self, s, pos):
    #     scanner = self._grm[self.start]
    #     return scanner._scan(s, pos)

    def scan(self, s, pos=0):
        scanner = self._grm[self.start]
        return scanner.scan(s, pos)

    def match(self, s, pos=0, trace=False):
        scanner = self._grm[self.start]
        return scanner.match(s, pos, trace=trace)

    def read(self, definition):
        d = self.GrammarReader.match(definition)
        if d is None:
            raise ValueError('Not a valid grammar definition: ' + definition)
        self._description.update(d.value)
        for identifier, spellout in d.value.items():
            self[identifier] = self._make_scanner(spellout)

    def update_actions(self, items=None, **kwargs):
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

    def _make_scanner(self, a):
        typ = a[0]
        if typ == 'Dot':
            return Dot()
        elif typ == 'Literal':
            return Literal(a[1])
        elif typ == 'CharacterClass':
            return CharacterClass(a[1])
        elif typ == 'Regex':
            return Regex(a[1])
        elif typ == 'Group':
            return Group(self._make_scanner(a[1]))
        elif typ == 'Nonterminal':
            return self.nonterminal(a[1])
        elif typ == 'Lookahead':
            return Lookahead(self._make_scanner(a[1]))
        elif typ == 'NegativeLookahead':
            return NegativeLookahead(self._make_scanner(a[1]))
        elif typ == 'ZeroOrMore':
            return ZeroOrMore(self._make_scanner(a[1]))
        elif typ == 'OneOrMore':
            return OneOrMore(self._make_scanner(a[1]))
        elif typ == 'Optional':
            return Optional(self._make_scanner(a[1]))
        elif typ == 'Repeat':
            minimum = a[2]['min']
            maximum = a[2]['max']
            delimiter = a[2]['delimiter']
            if delimiter is not None:
                delimiter = self._make_scanner(delimiter)
            return Repeat(self._make_scanner(a[1]),
                          min=minimum, max=maximum, delimiter=delimiter)
        elif typ == 'Sequence':
            return Sequence(*[self._make_scanner(b) for b in a[1]])
        elif typ == 'Choice':
            return Choice(*[self._make_scanner(b) for b in a[1]])
        else:
            raise ValueError('Invalid scanner type: ' + str(typ))


class PEG(Grammar):
    GrammarReader = io.PEGReader
