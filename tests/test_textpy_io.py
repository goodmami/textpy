#!/usr/bin/env python3

from textpy.io import (
    _Id,
    DotReader,
    SQLiteralReader,
    DQLiteralReader,
    CharacterClassReader,
    RegexReader,
    PrimaryReader,
    PrefixReader,
    SuffixReader,
    TermReader,
    SequenceReader,
    ChoiceReader,
    GroupReader,
    RuleReader,
    GrammarReader
)

# NOMATCH = scanners.NOMATCH

def test_IdentifierReader():
    assert _Id.match('a1').value == 'a1'
    assert _Id.match('-_-').value == '-_-'
    assert _Id.match('1') is None

def test_DotReader():
    assert DotReader.match('.').value == ('Dot',)

def test_SQLiteralReader():
    assert SQLiteralReader.match("'abc'").value == ('Literal', 'abc')

def test_DQLiteralReader():
    assert DQLiteralReader.match('"abc"').value == ('Literal', 'abc')

def test_CharacterClassReader():
    assert CharacterClassReader.match('[abc]').value == ('CharacterClass', 'abc')

def test_RegexReader():
    assert RegexReader.match('/ab*/').value == ('Regex', 'ab*')

def test_PrimaryReader():
    assert PrimaryReader.match('.').value == ('Dot',)
    assert PrimaryReader.match('"abc"').value == ('Literal', 'abc')
    assert PrimaryReader.match('[abc]').value == ('CharacterClass', 'abc')
    assert PrimaryReader.match('/ab*/').value == ('Regex', 'ab*')
    assert PrimaryReader.match('(.)').value == ('Group', ('Dot',))
    assert PrimaryReader.match('A').value == ('Nonterminal', 'A')

def test_SequenceReader():
    assert SequenceReader.match('"abc"').value == ('Literal', 'abc')
    assert SequenceReader.match('"a" "b" "c"').value == ('Sequence', [
        ('Literal', 'a'), ('Literal', 'b'), ('Literal', 'c')
    ])

def test_GroupReader():
    assert GroupReader.match('("abc")').value == ('Group', ('Literal', 'abc'))
    assert SequenceReader.match('"a" ("b")').value == ('Sequence', [
        ('Literal', 'a'), ('Group', ('Literal', 'b'))
    ])

def test_ChoiceReader():
    assert ChoiceReader.match('"a" | "b"').value == ('Choice', [
        ('Literal', 'a'), ('Literal', 'b')
    ])
    assert ChoiceReader.match('"a" "b" | "c"').value == ('Choice', [
        ('Sequence', [('Literal', 'a'), ('Literal', 'b')]), ('Literal', 'c')
    ])

def test_PrefixReader():
    assert PrefixReader.match('&').value == ('Lookahead', None)
    assert PrefixReader.match('!').value == ('NegativeLookahead', None)

def test_SuffixReader():
    assert SuffixReader.match('*').value == ('ZeroOrMore', None)
    assert SuffixReader.match('+').value == ('OneOrMore', None)
    assert SuffixReader.match('?').value == ('Optional', None)
    assert SuffixReader.match('{}').value == ('Repeat', None, {'min': 0, 'max': -1, 'delimiter': None})

def test_TermReader():
    assert TermReader.match('"abc"').value == ('Literal', 'abc')
    assert TermReader.match('"abc"?').value == ('Optional', ('Literal', 'abc'))
    assert TermReader.match('&"abc"').value == ('Lookahead', ('Literal', 'abc'))
    assert TermReader.match('&"abc"+').value == ('Lookahead', ('OneOrMore', ('Literal', 'abc')))

def test_RuleReader():
    assert RuleReader.match('A = "a"').value == ('Rule', 'A', ('Literal', 'a'))
    assert RuleReader.match('A = "a"\n    "b"').value == ('Rule', 'A', ('Sequence', [
        ('Literal', 'a'), ('Literal', 'b')
    ]))

def test_GrammarReader():
    assert GrammarReader.match('''
        A = B
        B = "b"
    ''').value == {
        'A': ('Nonterminal', 'B'),
        'B': ('Literal', 'b')
    }
