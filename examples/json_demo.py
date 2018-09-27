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

from textpy.scanners import *
from textpy.actions import constant
from textpy.grammars import Grammar, PEG


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


Json2b = Grammar(
    '''
    Start    = Object | Array
    Object   = /{\s*/ (Mapping (/\s*,\s*/ Mapping)*)? /\s*}/
    Mapping  = DQString /\s*:\s*/ Value
    Array    = /\[\s*/ (Value (/\s*,\s*/ Value)*)? /\s*\]/
    Value    = Object | Array | DQString
             | TrueVal | FalseVal | NullVal | Float | Integer
    TrueVal  = "true"
    FalseVal = "false"
    NullVal  = "null"
    DQString = /\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\"/
    Float    = /[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?/
    Integer  = /[-+]?\d+/
    '''
)

Json2c = Grammar(
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
Json2c['Float'] = Float()
Json2c['Integer'] = Integer()
Json2c['DQString'] = BoundedString('"', '"')
Json2c['Spacing'] = Spacing()

Json2d = PEG(
    '''
    Start    <- Object / Array
    Object   <- "{" Spacing (Mapping (Spacing "," Spacing Mapping)*)? Spacing "}"
    Mapping  <- DQString Spacing ":" Spacing Value
    Array    <- "[" Spacing (Value (Spacing "," Spacing Value)*)? Spacing "]"
    Value    <- Object / Array / DQString / TrueVal / FalseVal / NullVal / Float / Integer
    TrueVal  <- "true"
    FalseVal <- "false"
    NullVal  <- "null"
    DQString <- ~"\\\"[^\\\"\\\\]*(?:\\\\.[^\\\"\\\\]*)*\\\""
    Float    <- ~"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?"
    Integer  <- ~"[-+]?\d+"
    Spacing  <- [ \t\n]*
    '''
)

# slower PEG version
    # Start        <- Object / Array
    # Object       <- OPENBRACE (KeyVal (COMMA KeyVal)*)? CLOSEBRACE
    # Array        <- OPENBRACKET (Value (COMMA Value)*)? CLOSEBRACKET
    # KeyVal       <- Key COLON Value
    # Key          <- DQSTRING Spacing
    # Value        <- (DQSTRING / Object / Array / Number / True / False / Null) Spacing
    # DQSTRING     <- ~"\\\"[^\\\"\\\\]*(?:\\\\.[^\\\"\\\\]*)*\\\"" Spacing
    # Number       <- Float / Int
    # Float        <- ~"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?" Spacing
    # Int          <- ~"[-+]?\d+" Spacing
    # True         <- 'true'
    # False        <- 'false'
    # Null         <- 'null'
    # OPENBRACE    <- '{' Spacing
    # CLOSEBRACE   <- '}' Spacing
    # OPENBRACKET  <- '[' Spacing
    # CLOSEBRACKET <- ']' Spacing
    # COMMA        <- ',' Spacing
    # COLON        <- ':' Spacing
    # Spacing      <- [ \t\n]*


try:
    from parsimonious.grammar import Grammar
    # much slower grammar
    '''
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
    '''
    Json3 = Grammar(r'''
        Start    = Object / Array
        Object   = ~"{\s*" (Mapping (~"\s*,\s*" Mapping)*)? ~"\s*}"
        Mapping  = DQString ~"\s*:\s*" Value
        Array    = ~"\[\s*" (Value (~"\s*,\s*" Value)*)? ~"\s*\]"
        Value    = Object / Array / DQString
                 / TrueVal / FalseVal / NullVal / Float / Integer
        TrueVal  = "true"
        FalseVal = "false"
        NullVal  = "null"
        DQString = ~"\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\""
        Float    = ~"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?"
        Integer  = ~"[-+]?\d+"
    ''')
except ImportError:
    Json3 = None

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
    assert Json2b.match(s) is not None
    import timeit
    print(
        'textpy (function composition)',
        timeit.timeit(
            'Json.match(s)',
            setup='from __main__ import Json, s',
            number=10000
        )
    )
    print(
        'textpy (grammar definition)',
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

    print(
        'textpy (grammar definition; alt grammar; scan only)',
        timeit.timeit(
            'Json2b.scan(s)',
            setup='from __main__ import Json2b, s',
            number=10000
        )
    )
    print(
        'textpy (grammar definition; scan only)',
        timeit.timeit(
            'Json2c.scan(s)',
            setup='from __main__ import Json2c, s',
            number=10000
        )
    )
    print(
        'textpy (peg; scan only)',
        timeit.timeit(
            'Json2d.scan(s)',
            setup='from __main__ import Json2d, s',
            number=10000
        )
    )

    if Json3 is not None:
        print(
            'parsimonious (scan only)',
            timeit.timeit(
                'Json3.match(s)',
                setup='from __main__ import Json3, s',
                number=10000
            )
        )

    import cProfile
    cProfile.run('[Json.match(s) for i in range(100)]', 'stats')
