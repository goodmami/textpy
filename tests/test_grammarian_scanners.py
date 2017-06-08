
#!/usr/bin/env python3

from grammarian import scanners

NOMATCH = scanners.NOMATCH

def test_Dot():
    for prefix in ('c', 'py'):
        p = getattr(scanners, prefix + '_Dot')()
        assert p.scan('') == NOMATCH
        assert p.scan('a') == 1
        assert p.scan('\na') == 1

def test_CharacterClass():
    for prefix in ('c', 'py'):
        cc = getattr(scanners, prefix + '_CharacterClass')
        assert cc('a').scan('b') == NOMATCH
        assert cc('a').scan('a') == 1
        assert cc('a-d').scan('b') == 1
        assert cc('ac-ez').scan('b') == NOMATCH
        assert cc('ac-ez').scan('d') == 1
        assert cc('-a').scan('-') == 1
        assert cc('-a').scan('a') == 1
        assert cc('a-').scan('-') == 1
        assert cc('a-').scan('a') == 1
        assert cc('a-z1-').scan('-') == 1
        assert cc('a-z1-').scan('1') == 1
        assert cc('a-z1-').scan('2') == NOMATCH
        assert cc('a-z1-').scan('A') == NOMATCH

def test_Repeat():
    for prefix in ('c', 'py'):
        rep = getattr(scanners, prefix + '_Repeat')
        cc = getattr(scanners, prefix + '_CharacterClass')
        assert rep(cc('a-z')).scan('') == 0
        assert rep(cc('a-z'), 1).scan('') == NOMATCH
        assert rep(cc('a-z')).scan('a') == 1
        assert rep(cc('a-z')).scan('abc') == 3
        assert rep(cc('a-z'), max=2).scan('abc') == 2
        assert rep(cc('a-z'), delimiter=cc(',-')).scan('a,b-c:d') == 5
        assert rep(cc('a-z'), delimiter=cc(',-')).scan('a,') == 1
        
def test_Literal():
    for prefix in ('c', 'py'):
        lit = getattr(scanners, prefix + '_Literal')
        assert lit('a').scan('b') == NOMATCH
        assert lit('a').scan('a') == 1
        assert lit('abc').scan('a') == NOMATCH
        assert lit('abc').scan('abcdef') == 3

def test_BoundedString():
    for prefix in ('c', 'py'):
        bs = getattr(scanners, prefix + '_BoundedString')
        p = bs('"', '"')
        assert p.scan('one "two"') == NOMATCH
        assert p.scan('"one" two') == 5
        assert p.scan('one "two"', pos=4) == 9
        assert p.scan('"one\\"two"') == 10
        p = bs('"""', '"""')
        assert p.scan('"""one"""') == 9
        assert p.scan('"""a""b"c"""') == 12

def test_Sequence():
    for prefix in ('c', 'py'):
        seq = getattr(scanners, prefix + '_Sequence')
        rep = getattr(scanners, prefix + '_Repeat')
        cc = getattr(scanners, prefix + '_CharacterClass')
        p = seq(cc('a-z'))
        assert p.scan('') == NOMATCH
        assert p.scan('1') == NOMATCH
        assert p.scan('abc') == 1
        p = seq(rep(cc('a-z')))
        assert p.scan('') == 0
        assert p.scan('abc', pos=3) == 3
        assert p.scan('abc123') == 3
        p = seq(
            rep(cc('a-z'), min=1),
            rep(cc('a-z0-9'), min=1)
        )
        assert p.scan('') == NOMATCH
        assert p.scan('abc', pos=3) == NOMATCH
        assert p.scan('abc') == NOMATCH  # patterns are greedy
        assert p.scan('abc123', pos=3) == NOMATCH
        assert p.scan('abc123') == 6

def test_Choice():
    for prefix in ('c', 'py'):
        ch = getattr(scanners, prefix + '_Choice')
        lit = getattr(scanners, prefix + '_Literal')
        p = ch(lit('a'))
        assert p.scan('') == NOMATCH
        assert p.scan('a') == 1
        assert p.scan('abc') == 1
        p = ch(lit('a'),lit('b'))
        assert p.scan('abc') == 1
        assert p.scan('abc', pos=1) == 2
        assert p.scan('abc', pos=2) == NOMATCH

def test_Integer():
    for prefix in ('c', 'py'):
        integer = getattr(scanners, prefix + '_Integer')()
        assert integer.scan('') == NOMATCH
        assert integer.scan('a') == NOMATCH
        assert integer.scan('0') == 1
        assert integer.scan('01') == 2
        assert integer.scan('0.1') == 1
        assert integer.scan('-0') == 2
        assert integer.scan('+0') == 2
        assert integer.scan('-') == NOMATCH
        assert integer.scan('+') == NOMATCH

def test_Float():
    for prefix in ('c', 'py'):
        float = getattr(scanners, prefix + '_Float')()
        assert float.scan('') == NOMATCH
        assert float.scan('a') == NOMATCH
        assert float.scan('0') == NOMATCH
        assert float.scan('01') == NOMATCH
        assert float.scan('0.1') == 3
        assert float.scan('.1') == 2
        assert float.scan('0.') == 2
        assert float.scan('.') == NOMATCH
        assert float.scan('0.1.2') == 3
        assert float.scan('-0') == NOMATCH
        assert float.scan('+0') == NOMATCH
        assert float.scan('-') == NOMATCH
        assert float.scan('+') == NOMATCH
        assert float.scan('1.0blah') == 3
        assert float.scan('1.0e') == 3
        assert float.scan('1.e') == 2
        assert float.scan('1.0e1') == 5
        assert float.scan('-1.0e+5') == 7
        assert float.scan('-1.0e-5') == 7
        assert float.scan('-1.0e5e3') == 6
        assert float.scan('-1.0e-e3') == 4
        assert float.scan('-1.e1') == 5
        assert float.scan('-.1e1') == 5
        assert float.scan('-.e1') == NOMATCH
        assert float.scan('1e') == NOMATCH
        assert float.scan('1e1') == 3

def test_Regex():
    for prefix in ('c', 'py'):
        regex = getattr(scanners, prefix + '_Regex')
        assert regex(r'a').scan('b') == NOMATCH
        assert regex(r'a').scan('a') == 1
        assert regex(r'a*').scan('aaab') == 3
        assert regex(r'a(b)c').scan('abc') == 3
        import re
        r = re.compile('a*', re.I)
        assert regex(r).scan('aAab') == 3

def test_Spacing():
    for prefix in ('c', 'py'):
        spacing = getattr(scanners, prefix + '_Spacing')()
        assert spacing.scan('') == 0
        assert spacing.scan('a') == 0
        assert spacing.scan(' a') == 1
        assert spacing.scan('\t\n\r\f\v a') == 6


def test_Group():
    for prefix in ('c', 'py'):
        grp = getattr(scanners, prefix + '_Group')
        seq = getattr(scanners, prefix + '_Sequence')
        lit = getattr(scanners, prefix + '_Literal')
        rep = getattr(scanners, prefix + '_Repeat')
        a = lit('a')
        b = lit('b')
        assert a.match('a').value == 'a'
        assert grp(a).match('a').value == ['a']
        assert grp(grp(a)).match('a').value == [['a']]
        assert seq(a, b).match('ab').value == 'ab'
        assert seq(grp(a), grp(b)).match('ab').value == ['a', 'b']
        assert grp(seq(a, b)).match('ab').value == ['ab']
        assert grp(seq(grp(a), grp(b))).match('ab').value == [['a', 'b']]
        assert seq(a, grp(b)).match('ab').value == ['b']
        # (?: "a" ("b")) "a"
        assert seq(seq(a, grp(b)), a).match('aba').value == ['b']
        # ("a"){:" "}
        assert rep(grp(a), delimiter=lit(' ')).match('a a').value == ['a', 'a']
        # (("a")){:" "}
        assert rep(grp(grp(a)), delimiter=lit(' ')).match('a a').value == [['a'], ['a']]


def test_Optional():
    for prefix in ('c', 'py'):
        opt = getattr(scanners, prefix + '_Optional')
        grp = getattr(scanners, prefix + '_Group')
        lit = getattr(scanners, prefix + '_Literal')
        a = lit('a')
        assert opt(a).match('a').value == 'a'
        assert opt(a).match('b').value == ''
        assert opt(a, default=None).match('b').value is None
        assert opt(grp(a)).match('a').value == ['a']
        assert opt(grp(a)).match('b').value == []
        assert opt(grp(a), default=None).match('b').value == None



# def test_sequence():
#     assert s.sequence(s.Integer)('a') is None

#     m = s.sequence(s.Integer)('123')
#     assert m.lastindex == 1
#     assert [m.span(i) for i in range(m.lastindex+1)] == [(0, 3), (0, 3)]

#     m = s.sequence(s.Spacing, s.Integer)('123')
#     assert m.lastindex == 2
#     assert [m.span(i) for i in range(m.lastindex+1)] == [(0, 3), (0, 0), (0, 3)]

#     m = s.sequence(s.Spacing, s.Integer)('  123')
#     assert m.lastindex == 2
#     assert [m.span(i) for i in range(m.lastindex+1)] == [(0, 5), (0, 2), (2, 5)]

#     m = s.sequence(s.Spacing, s.Integer, s.DQString)('  123"hello"')
#     assert m.lastindex == 3
#     assert [m.span(i) for i in range(m.lastindex+1)] == [
#         (0, 12), (0, 2), (2, 5), (5, 12)
#     ]
#     assert m.group() == m.string
#     assert m.group(1) == '  '
#     assert m.group(2) == '123'
#     assert m.group(3) == '"hello"'

#     m = s.sequence(s.literal('a'), s.literal('b'), ifs=s.Spacing)('a  bc')
#     assert m.span() == (0, 4)
#     assert m.span(1) == (0, 1)
#     assert m.span(2) == (3, 4)

# def test_join():
#     lit, cc = s.literal, s.character_class
#     assert s.join(lit('a'), lit('b'))('a b') is None
#     assert s.join(lit('a'), lit('b'))('ab').span() == (0, 2)
#     assert s.join(cc('a-z'), cc('a-zA-Z0-9'))('a8').span() == (0, 2)

# def test_choice():
#     assert s.choice(s.Integer)('') is None
#     assert s.choice(s.Integer)('123').span() == (0, 3)

#     assert s.choice(s.Integer, s.DQString)('123').span() == (0, 3)
#     assert s.choice(s.Integer, s.DQString)('"Hello"').span() == (0, 7)
#     assert s.choice(s.Integer, s.DQString)('Hello') is None

# def test_zero_or_more():
#     zom = s.zero_or_more
#     assert zom(s.literal('a'))('b').span() == (0, 0)
#     assert zom(s.literal('a'))('a').span() == (0, 1)
#     assert zom(s.literal('a'))('aaa').span() == (0, 3)
