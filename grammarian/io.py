
from grammarian.scanners import *

'''
| `X < ...`    | Rule `X` returns a list                          |
| `X = ...`    | Rule `X` returns an item                         |
| `"..."`      | string                                           |
| `[...]`      | character class                                  |
| `/.../`      | regular expression                               |
| `A B`        | `A` and `B` are a sequence                       |
| `A | B`      | `A` and `B` are an ordered choice                |
| `(...)`      | matching group                                   |
| `(?:...)`    | non-matching group                               |
| `!A`         | negative lookahead on `A`                        |
| `&A`         | positive lookahead on `A`                        |
| `A?`         | optionally match `A`                             |
| `A*`         | match zero or more `A`s                          |
| `A+`         | match one or more `A`s                           |
| `A{n}`       | match exactly *n* `A`s                           |
| `A{m,n}`     | match between *m* and *n* `A`s                   |
| `A{:B}`      | match `A`s delimited by `B`s                     |
| `A{n:B}`     | match *n* `A`s delimited by `B`s                 |
| `A{m,n:B}`   | match between *m* and *n* `A`s delimited by `B`s |
| `A ^`        | cut/ratchet after matching `A`                   |
'''

def _make(t, v):
    return (t, v)

patterns = {}

_WS = Spacing()
_Int = Group(Integer(), action=int)
_Id = Regex(r'[-a-zA-Z_][-a-zA-Z0-9_]*')

DotReader = Group(
    Literal('.'),
    action=lambda s: ('Dot',)
)

LiteralReader = Group(
    BoundedString('"', '"'),
    action=lambda s: _make('Literal', s[1:-1])
)

CharacterClassReader = Group(
    BoundedString('[', ']'),
    action=lambda s: _make('CharacterClass', s[1:-1])
)

RegexReader = Group(
    BoundedString('/', '/'),
    action=lambda s: _make('Regex', s[1:-1])
)

PrimaryReader = Choice(
    DotReader,
    LiteralReader,
    CharacterClassReader,
    RegexReader,
    Nonterminal(patterns, 'Group'),
    Group(
        Sequence(
            Group(_Id),
            NegativeLookahead(Sequence(_WS, Literal('=')))
        ),
        action=lambda xs: _make('Nonterminal', xs[0]),
    )
)


def _make_repeat(vals):
    _min, _max, delim = vals
    return ('Repeat', None, {'min': _min, 'max': _max, 'delimiter': delim})

# "{" (?: (Integer) (?: "," (Integer) )? )? (?: ":" (Term) )? "}"
RepeatReader = Bounded(
    Literal('{'),
    Sequence(
        Optional(Group(_Int), default=(0,)),
        Optional(
            Sequence(Literal(','), Group(_Int)),
            default=(-1,)
        ),
        Optional(
            Sequence(Literal(':'), Group(PrimaryReader)),
            default=(None,)
        )
    ),
    Literal('}')
)
RepeatReader.action=_make_repeat

PrefixReader = Choice(
    Group(Literal('&'), action=lambda x: _make('Lookahead', None)),
    Group(Literal('!'), action=lambda x: _make('NegativeLookahead', None))
)

SuffixReader = Choice(
    Group(Literal('*'), action=lambda x: _make('ZeroOrMore', None)),
    Group(Literal('+'), action=lambda x: _make('OneOrMore', None)),
    Group(Literal('?'), action=lambda x: _make('Optional', None)),
    RepeatReader
)


def _make_term(vals):
    prefix, term, suffix = vals
    if suffix is not None:
        term = tuple([suffix[0], term] + list(suffix[2:]))
    if prefix is not None:
        term = tuple([prefix[0], term] + list(prefix[2:]))
    return term

TermReader = Sequence(
    Group(Optional(PrefixReader, default=None)),
    Group(PrimaryReader),
    Group(Optional(SuffixReader, default=None))
)
TermReader.action=_make_term


# Sequences and Choices take a list of scanners; if there's only one,
# just return the scanner (minor optimization)

def _make_list(t, vs):
    if len(vs) == 0:
        raise ValueError('At least one term is required.')
    elif len(vs) == 1:
        return vs[0]
    else:
        return (t, vs)

SequenceReader = Repeat(Group(TermReader), min=1, delimiter=_WS)
SequenceReader.action=lambda xs: _make_list('Sequence', xs)

ChoiceReader = Repeat(
    Group(SequenceReader), min=1, delimiter=Sequence(_WS, Literal('|'), _WS)
)
ChoiceReader.action=lambda xs: _make_list('Choice', xs)


GroupReader = Bounded(
    Sequence(Literal('('), _WS),
    ChoiceReader,
    Sequence(_WS, Literal(')'))
)
GroupReader.action = lambda x: _make('Group', x)

patterns['Group'] = GroupReader

RuleReader = Sequence(
    _WS, Group(_Id), _WS, Literal('='), _WS, Group(ChoiceReader)
)
RuleReader.action = lambda xs: ('Rule', xs[0], xs[1])

CommentReader = Sequence(
    Literal('#'),
    Repeat(Sequence(NegativeLookahead(Literal('\n')), Dot()))
)

# Grammars collect rules and manage the associations between
# nonterminals and their spellouts

def _make_grammar(vals):
    grm = {}
    for typ, identifier, expression in vals:
        if typ == 'Rule':
            grm[identifier] = expression
    return grm

GrammarReader = Repeat(
    Group(RuleReader),
    min=1,
    delimiter=_WS
)
GrammarReader.action = _make_grammar
