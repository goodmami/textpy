
from textpy.scanners import *

'''
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
'''


# helper functions

_WS = Spacing()
_Int = Group(Integer(), action=int)
_Id = Regex(r'[-a-zA-Z_][-a-zA-Z0-9_]*')


# basic functions

DotReader = Group(
    Literal('.'),
    action=lambda s: ('Dot',)
)

SQLiteralReader = Group(
    BoundedString("'", "'"),
    action=lambda s: ('Literal', s[1:-1])
)

DQLiteralReader = Group(
    BoundedString('"', '"'),
    action=lambda s: ('Literal', s[1:-1])
)

CharacterClassReader = Group(
    BoundedString('[', ']'),
    action=lambda s: ('CharacterClass', s[1:-1])
)

RegexReader = Group(
    BoundedString('/', '/'),
    action=lambda s: ('Regex', s[1:-1])
)

LookaheadReader = Group(
    Literal('&'),
    action=lambda x: ('Lookahead', None)
)

NegativeLookaheadReader = Group(
    Literal('!'),
    action=lambda x: ('NegativeLookahead', None)
)

ZeroOrMoreReader = Group(
    Literal('*'),
    action=lambda x: ('ZeroOrMore', None)
)

OneOrMoreReader = Group(
    Literal('+'),
    action=lambda x: ('OneOrMore', None)
)

OptionalReader = Group(
    Literal('?'),
    action=lambda x: ('Optional', None)
)

CommentReader = Sequence(
    Literal('#'),
    Repeat(Sequence(NegativeLookahead(Literal('\n')), Dot()))
)


# composed grammar functions

patterns = {}

PrimaryReader = Choice(
    DotReader,
    DQLiteralReader,
    CharacterClassReader,
    RegexReader,
    Nonterminal(patterns, 'Group'),
    Group(
        Sequence(
            Group(_Id),
            NegativeLookahead(Sequence(_WS, Literal('=')))
        ),
        action=lambda xs: ('Nonterminal', xs[0]),
    )
)

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
    Literal('}'),
    action=lambda xs: (
        'Repeat', None, {'min': xs[0], 'max': xs[1], 'delimiter': xs[2]}
    )
)

PrefixReader = Choice(LookaheadReader, NegativeLookaheadReader)

SuffixReader = Choice(
    ZeroOrMoreReader, OneOrMoreReader, OptionalReader, RepeatReader
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
    Group(Optional(SuffixReader, default=None)),
    action=_make_term
)


# Sequences and Choices take a list of scanners; if there's only one,
# just return the scanner (minor optimization)

def _make_list(t, vs):
    if len(vs) == 0:
        raise ValueError('At least one term is required.')
    elif len(vs) == 1:
        return vs[0]
    else:
        return (t, vs)

SequenceReader = Repeat(
    Group(TermReader), min=1, delimiter=_WS,
    action=lambda xs: _make_list('Sequence', xs)
)

ChoiceReader = Repeat(
    Group(SequenceReader), min=1, delimiter=Sequence(_WS, Literal('|'), _WS),
    action=lambda xs: _make_list('Choice', xs)
)

GroupReader = Bounded(
    Sequence(Literal('('), _WS),
    ChoiceReader,
    Sequence(_WS, Literal(')')),
    action=lambda x: ('Group', x)
)

patterns['Group'] = GroupReader

RuleReader = Sequence(
    _WS, Group(_Id), _WS, Literal('='), _WS, Group(ChoiceReader),
    action=lambda xs: ('Rule', xs[0], xs[1])
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
    delimiter=_WS,
    action=_make_grammar
)


# PEG functions

PEGPatterns = {}

PEGSQRegexReader = Group(
    BoundedString("~'", "'"),
    action=lambda s: ('Regex', s[2:-1])
)

PEGDQRegexReader = Group(
    BoundedString('~"', '"'),
    action=lambda s: ('Regex', s[2:-1])
)

PEGPrimaryReader = Choice(
    DotReader,
    SQLiteralReader,
    DQLiteralReader,
    CharacterClassReader,
    PEGSQRegexReader,
    PEGDQRegexReader,
    Nonterminal(PEGPatterns, 'Group'),
    Group(
        Sequence(
            Group(_Id),
            NegativeLookahead(Sequence(_WS, Literal('<-')))
        ),
        action=lambda xs: ('Nonterminal', xs[0]),
    )
)

PEGSuffixReader = Choice(ZeroOrMoreReader, OneOrMoreReader, OptionalReader)

PEGTermReader = Sequence(
    Group(Optional(PrefixReader, default=None)),
    Group(PEGPrimaryReader),
    Group(Optional(PEGSuffixReader, default=None)),
    action=_make_term
)

PEGSequenceReader = Repeat(
    Group(PEGTermReader), min=1, delimiter=_WS,
    action=lambda xs: _make_list('Sequence', xs)
)

PEGChoiceReader = Repeat(
    Group(PEGSequenceReader), min=1, delimiter=Sequence(_WS,Literal('/'),_WS),
    action=lambda xs: _make_list('Choice', xs)
)

PEGGroupReader = Bounded(
    Sequence(Literal('('), _WS),
    PEGChoiceReader,
    Sequence(_WS, Literal(')')),
    action=lambda x: ('Group', x)
)

PEGPatterns['Group'] = PEGGroupReader

PEGRuleReader = Sequence(
    _WS, Group(_Id), _WS, Literal('<-'), _WS, Group(PEGChoiceReader),
    action=lambda xs: ('Rule', xs[0], xs[1])
)

PEGReader = Repeat(
    Group(PEGRuleReader),
    min=1,
    delimiter=_WS,
    action=_make_grammar
)
