# -*- coding: utf-8 -*-

'''
A JSON parser.

This uses the *action* functionality to construct the JSON object as
it parses, rather than just producing an AST. The grammar is roughly
like this:

    start       <- Object / Array
    Object      <- OPENBRACE (KeyVal (COMMA KeyVal)*)? CLOSEBRACE
    Array       <- OPENBRACKET (Value (COMMA Value)*)? CLOSEBRACKET
    KeyVal      <- Key COLON Value
    Key         <- DQSTRING Spacing
    Value       <- (DQSTRING / Object / Array / Number / True / False / Null) Spacing
    DQSTRING    <- '"' (!'"' .)* '"'
    Number      <- Float / Int
    Float       <- Int FloatSuffix
    FloatSuffix <- '.' [0-9]+ 'e' [+-]? [0-9]+
                 / '.' [0-9]+
                 / 'e' [+-]? [0-9]+
    Int         <- '-'? (0 | [1-9][0-9]*)
    True        <- 'true'
    False       <- 'false'
    Null        <- 'null'
    OPENBRACE   <- '{' Spacing
    OPENBRACE   <- '}' Spacing
    OPENBRACKET <- '[' Spacing
    OPENBRACKET <- ']' Spacing
    COMMA       <- ',' Spacing
    COLON       <- ':' Spacing
    Spacing     <- [ \t\n]*

Note that string processing does not currently process escape
sequences. Because JSON strings can contain both unicode AND escaped
unicode, some custom processing is required. See this StackOverflow
answer: http://stackoverflow.com/a/24519338/1441112

'''

from grammarian.scanners import *
from grammarian.actions import constant
from grammarian.grammars import Grammar


grm = {}
Str = Group(BoundedString('"', '"'), action=lambda s: s[1:-1])
Flt = Group(Float(), action=float)
Int = Group(Integer(), action=int)
Tru = Group(Literal('true'), action=constant(True))
Fls = Group(Literal('false'), action=constant(False))
Nul = Group(Literal('null'), action=constant(None))
Comma = Literal(',')
WS = Spacing()
Object = Group(
    Bounded(
        Literal('{'),
        Repeat(Group(Sequence(WS, Str, WS, Literal(':'), WS,
                              Group(Nonterminal(grm, 'Value')), WS)),
               delimiter=Comma),
        Literal('}')
    ),
    action=dict
)
Array = Group(
    Bounded(
        Sequence(Literal('['), WS),
        Repeat(Group(Nonterminal(grm, 'Value')),
               delimiter=Sequence(WS, Comma, WS)),
        Sequence(WS, Literal(']'))
    ),
    action=list
)
grm['Value'] = Choice(Object, Array, Str, Tru, Fls, Nul, Flt, Int)

Json = Choice(Object, Array)


Json2 = Grammar(
    '''
    Start    = Object | Array
    Object   = "{" Spacing
               ((DQString) Spacing ":" Spacing (Value)){:Comma}
               Spacing "}"
    Array    = "[" Spacing
               (Value){:Comma}
               Spacing "]"
    Value    = Object | Array | DQString
             | TrueVal | FalseVal | NullVal | Float | Integer
    TrueVal  = "true"
    FalseVal = "false"
    NullVal  = "null"
    Comma    = Spacing "," Spacing
    '''
)
Json2['Float'] = Float()
Json2['Integer'] = Integer()
Json2['DQString'] = BoundedString('"', '"')
Json2['Spacing'] = Spacing()
Json2.update_actions(
    Object=dict,
    Array=list,
    DQString=lambda s: s[1:-1],
    TrueVal=constant(True),
    FalseVal=constant(False),
    NullVal=constant(None),
    Float=float,
    Integer=int
)


if __name__ == '__main__':
    s = '''{
        "bool": [
            true,
            false
        ],
        "number": {
            "float": -0.14e3,
            "int": 1
        },
        "other": {
            "string": "string",
            "unicode": "あ",
            "null": null
        }
    }'''

    assert Json.match(s) is not None
    assert Json.match(s).value == {
        'bool': [True, False],
        'number': {'float': -0.14e3, 'int': 1},
        'other': {'string': 'string', 'unicode': 'あ', 'null': None}
    }
    assert Json2.match(s) is not None
    assert Json2.match(s).value == {
        'bool': [True, False],
        'number': {'float': -0.14e3, 'int': 1},
        'other': {'string': 'string', 'unicode': 'あ', 'null': None}
    }
    import timeit
    print(
        'grammarian (function composition)',
        timeit.timeit(
            'Json.match(s)',
            setup='from __main__ import Json, s',
            number=10000
        )
    )
    print(
        'grammarian (grammar definition)',
        timeit.timeit(
            'Json2.match(s)',
            setup='from __main__ import Json2, s',
            number=10000
        )
    )
    print(
        'json',
        timeit.timeit(
            'json.loads(s)',
            setup='from __main__ import s; import json',
            number=10000
        )
    )
    try:
        from parsimonious.grammar import Grammar
        Json3 = Grammar(r'''
            Start    = Object / Array
            Object   = LBrace (Mapping (Comma Mapping)*)? RBrace
            Mapping  = DQString Colon Value
            Array    = LBracket (Value (Comma Value)*)? RBracket
            Value    = Object / Array / DQString
                     / TrueVal / FalseVal / NullVal / Float / Integer
            Spacing  = ~"\s*"
            Comma    = "," Spacing
            Colon    = ":" Spacing
            LBrace   = "{" Spacing
            RBrace   = "}" Spacing
            LBracket = "[" Spacing
            RBracket = "]" Spacing
            TrueVal  = "true" Spacing
            FalseVal = "false" Spacing
            NullVal  = "null" Spacing
            DQString = ~"\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\"" Spacing
            Float    = ~"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?" Spacing
            Integer  = ~"[-+]?\d+" Spacing
        ''')
        print(
            'parsimonious (scan only)',
            timeit.timeit(
                'Json3.match(s)',
                setup='from __main__ import Json3, s',
                number=10000
            )
        )
    except ImportError:
        pass

    import cProfile
    cProfile.run('[Json.match(s) for i in range(100)]', 'stats')
