
from functools import partial

from grammarian.scanners import *
from grammarian.actions import constant
from grammarian.grammars import Grammar

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

def _make_term_or_sequence(vals):
    if len(vals) == 0:
        raise ValueError('At least one term is required.')
    elif len(vals) == 1:
        return vals[0]
    else:
        return Sequence(*vals)

def _make_sequence_or_choice(vals):
    if len(vals) == 0:
        raise ValueError('At least one term is required.')
    elif len(vals) == 1:
        return vals[0]
    else:
        return Choice(*vals)

def _make_repeat(vals):
    return partial(Repeat, min=vals[0], max=vals[1], delimiter=vals[2])

def _make_term(vals):
    prefix, term, suffix = vals
    if suffix is not None:
        term = suffix(term)
    if prefix is not None:
        term = prefix(term)
    return term

def _make_grammar(vals):
    grm = Grammar()
    for identifier, expression in vals:
        print(identifier, expression)
        grm[identifier] = expression
    return grm

patterns = {}

_WS = Spacing()

IntegerReader = Group(Integer(), action=int)

IdentifierReader = Regex(r'[-a-zA-Z_][-a-zA-Z0-9_]*')

DotReader = Group(Literal('.'), action=lambda s: Dot())

LiteralReader = Group(
    BoundedString('"', '"'), action=lambda s: Literal(s[1:-1])
)

CharacterClassReader = Group(
    BoundedString('[', ']'), action=lambda s: CharacterClass(s[1:-1])
)

RegexReader = Group(BoundedString('/', '/'), action=lambda s: Regex(s[1:-1]))

PrimaryReader = Choice(
    DotReader,
    LiteralReader,
    CharacterClassReader,
    RegexReader,
    Nonterminal(patterns, 'Group'),
    Group(
        Sequence(
            Group(IdentifierReader),
            NegativeLookahead(Sequence(_WS, Literal('=')))
        ),
        action=lambda xs: Nonterminal(None, xs[0]),
    )
)

# "{" (?: (Integer) (?: "," (Integer) )? )? (?: ":" (Term) )? "}"
RepeatReader = Bounded(
    Literal('{'),
    Sequence(
        Optional(Group(IntegerReader), default=(0,)),
        Optional(
            Sequence(Literal(','), Group(IntegerReader)),
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
    Group(Literal('&'), action=constant(Lookahead)),
    Group(Literal('!'), action=constant(NegativeLookahead))
)

SuffixReader = Choice(
    Group(Literal('*'), action=constant(ZeroOrMore)),
    Group(Literal('+'), action=constant(OneOrMore)),
    Group(Literal('?'), action=constant(Optional)),
    RepeatReader
)

TermReader = Sequence(
    Group(Optional(PrefixReader, default=None)),
    Group(PrimaryReader),
    Group(Optional(SuffixReader, default=None))
)
TermReader.action=_make_term

SequenceReader = Repeat(Group(TermReader), min=1, delimiter=_WS)
SequenceReader.action=_make_term_or_sequence

ChoiceReader = Repeat(
    Group(SequenceReader), min=1, delimiter=Sequence(_WS, Literal('|'), _WS)
)
ChoiceReader.action=_make_sequence_or_choice

GroupReader = Bounded(
    Sequence(Literal('('), _WS), ChoiceReader, Sequence(_WS, Literal(')'))
)
GroupReader.action = Group

patterns['Group'] = GroupReader

RuleReader = Sequence(
    _WS, Group(IdentifierReader), _WS, Literal('='), _WS, Group(ChoiceReader)
)

CommentReader = Sequence(
    Literal('#'), Repeat(Sequence(NegativeLookahead(Literal('\n')), Dot()))
)

GrammarReader = Repeat(
    Group(RuleReader),
    min=1,
    delimiter=_WS
)
GrammarReader.action = _make_grammar
