#!/usr/bin/env python3

from grammarian.io import (
    IdentifierReader,
    IntegerReader,
    DotReader,
    LiteralReader,
    CharacterClassReader,
    RegexReader,
    PrimaryReader,
    PrefixReader,
    SuffixReader,
    TermReader,
    SequenceReader,
    ChoiceReader,
    GroupReader,
    RuleReader
)

# NOMATCH = scanners.NOMATCH

def test_IdentifierReader():
    assert IdentifierReader.match('a1').value == 'a1'
    assert IdentifierReader.match('-_-').value == '-_-'
    assert IdentifierReader.match('1') is None

def test_IntegerReader():
    assert IntegerReader.match('1').value == 1

def test_DotReader():
    assert DotReader.match('.').value.match('a').value == 'a'
    assert DotReader.match('.').value.match(' ').value == ' '

def test_LiteralReader():
    assert LiteralReader.match('"abc"').value.match('abc').value == 'abc'

def test_CharacterClassReader():
    assert CharacterClassReader.match('[abc]').value.match('c').value == 'c'

def test_RegexReader():
    assert RegexReader.match('/ab*/').value.match('abbbbc').value == 'abbbb'

def test_PrimaryReader():
    assert PrimaryReader.match('"abc"').value.match('abc').value == 'abc'
    assert PrimaryReader.match('[abc]').value.match('c').value == 'c'
    assert PrimaryReader.match('/ab*/').value.match('abbbbc').value == 'abbbb'

def test_SequenceReader():
    assert SequenceReader.match('"abc"').value is not None
    assert SequenceReader.match('"abc"').value.match('abc').value == 'abc'
    assert SequenceReader.match('"a" "b" "c"').value.match('abc').value == 'abc'

def test_GroupReader():
    assert GroupReader.match('("abc")').value.match('abc').value == ['abc']
    assert SequenceReader.match('"a" ("b")').value.match('ab').value == ['b']

def test_ChoiceReader():
    assert ChoiceReader.match('"a" | "b"').value.match('a').value == 'a'
    assert ChoiceReader.match('"a" | "b"').value.match('b').value == 'b'
    assert ChoiceReader.match('"a" "b" | "c"').value.match('ab').value == 'ab'
    assert ChoiceReader.match('"a" "b" | "c"').value.match('c').value == 'c'
    assert ChoiceReader.match('"a" "b" | "c"').value.match('ac') is None

# def test_OptionalReader():
#     assert OptionalReader.match('"a"?').value.match('a').value == 'a'
#     assert OptionalReader.match('"a"?').value.match('b').value == ''

def test_RuleReader():
    assert RuleReader.match('A = "a"').value[1].match('a').value == 'a'
    assert RuleReader.match('A = "a"\n    "b"').value[1].match('a').value == 'a'
