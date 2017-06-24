
import re
from functools import partial

__all__ = [
    'Match',
    'Scanner',
    'Dot',
    'CharacterClass',
    'Literal',
    'Regex',
    'Spacing',
    'Integer',
    'Float',
    'BoundedString',
    'Bounded',
    'Sequence',
    'Choice',
    'Repeat',
    'ZeroOrMore',
    'OneOrMore',
    'Optional',
    'Lookahead',
    'NegativeLookahead',
    'Nonterminal',
    'Group',
    'split',
]

try:
    from grammarian._scanners import (
        Scanner             as c_Scanner,
        Dot                 as c_Dot,
        CharacterClass      as c_CharacterClass,
        Literal             as c_Literal,
        Regex               as c_Regex,
        Spacing             as c_Spacing,
        Integer             as c_Integer,
        Float               as c_Float,
        BoundedString       as c_BoundedString,
        Bounded             as c_Bounded,
        Sequence            as c_Sequence,
        Choice              as c_Choice,
        Repeat              as c_Repeat,
        Optional            as c_Optional,
        Lookahead           as c_Lookahead,
        NegativeLookahead   as c_NegativeLookahead,
        Nonterminal         as c_Nonterminal,
        Group               as c_Group,
    )
except ImportError:
    c_Scanner             = None
    c_Dot                 = None
    c_CharacterClass      = None
    c_Literal             = None
    c_Regex               = None
    c_Spacing             = None
    c_Integer             = None
    c_Float               = None
    c_BoundedString       = None
    c_Bounded             = None
    c_Sequence            = None
    c_Choice              = None
    c_Repeat              = None
    c_Optional            = None
    c_Lookahead           = None
    c_NegativeLookahead   = None
    c_Nonterminal         = None
    c_Group               = None

NOMATCH = -1
EOS = -2


class Match(object):
    def __init__(self, s, pos, endpos, value=None):
        self.string = s
        self.pos = pos
        self.endpos = endpos
        self.value = value
        # self.lastindex = sum(n.lastindex for n in ast)

    def start(self, group=0):
        if group == 0:
            return self.pos
        else:
            return self._groups[group].start()

    def end(self, group=0):
        if group == 0:
            return self.endpos
        else:
            return self._groups[group].end()

    def span(self, group=0):
        if group == 0:
            return (self.pos, self.endpos)
        else:
            return self._groups[group].span()

    def group(self, group=0):
        if group == 0:
            start, end = self.pos, self.endpos
        else:
            start, end = self._groups[group].span()
        return self.string[start:end]


class py_Scanner(object):
    capturing = False
    action = None

    def __init__(self, action=None):
        self.action = action

    def scan(self, s, pos=0):
        try:
            return self._scan(s, pos)
        except IndexError:
            return NOMATCH

    def match(self, s, pos=0):
        try:
            end = self._scan(s, pos)
            if end == NOMATCH:
                return None
            else:
                val = s[pos:end]
                action = self.action
                if action is not None:
                    val = action(val)
                return Match(s, pos, end, val)
        except IndexError:
            return None

class py_Dot(py_Scanner):
    def __repr__(self): return 'Dot()'
    def __str__(self): return '.'
    def _scan(self, s, pos):
        s[pos]  # check for IndexError
        return pos + 1


class py_CharacterClass(py_Scanner):
    def __init__(self, clsstr, action=None):
        self.action = action
        self._clsstr = clsstr
        self._ranges = []
        self._chars = []
        i = 0
        while i < len(clsstr)-2:
            if clsstr[i+1] == u'-':
                self._ranges.append((clsstr[i], clsstr[i+2]))
            else:
                self._chars.append(clsstr[i])
            i += 1
        # remaining character(s) cannot be ranges
        while i < len(clsstr):
            self._chars.append(clsstr[i])
            i += 1

    def __repr__(self): return 'CharacterClass({})'.format(repr(self._clsstr))
    def __str__(self): return '[{}]'.format(self._clsstr)

    def _scan(self, s, pos):
        c = s[pos]
        if c in self._chars or any(a <= c <= b for a, b in self._ranges):
            return pos + 1
        return NOMATCH


class py_Literal(py_Scanner):
    def __init__(self, x, action=None):
        self.action = action
        self._x = x
        self._xlen = len(x)

    def __repr__(self): return 'Literal({})'.format(repr(self._x))
    def __str__(self): return '"{}"'.format(self._x)

    def _scan(self, s, pos):
        end = pos + self._xlen
        if s[pos:end] != self._x:
            return NOMATCH
        return end


class py_Regex(py_Scanner):
    def __init__(self, pattern, action=None):
        self.action = action
        if hasattr(pattern, 'match'):
            self.regex = pattern
        else:
            self.regex = re.compile(pattern)

    def __repr__(self): return 'Regex({})'.format(repr(self.regex.pattern))
    def __str__(self): return '/{}/'.format(self.regex.pattern)

    def _scan(self, s, pos):
        m = self.regex.match(s, pos=pos)
        if m is None:
            return NOMATCH
        else:
            return m.end()


class py_Spacing(py_Scanner):
    def __init__(self, ws=u' \t\n\r\f\v', action=None):
        self.action = action
        self._ws = ws

    def __repr__(self):
        return 'Spacing({})'.format(
            repr(self._ws) if self._ws != u' \t\n\r\f\v' else ''
        )
    def __str__(self): return '[{}]*'.format(repr(self._ws)[1:-1])

    def _scan(self, s, pos):
        ws = self._ws
        try:
            while s[pos] in ws:
                pos += 1
        except IndexError:
            pass
        return pos


class py_Integer(py_Scanner):
    def __repr__(self): return 'Integer()'
    def __str__(self): return 'Integer'

    def _scan(self, s, pos):
        # [-+]? \d+
        if s[pos] in u'-+':
            pos += 1
        numdigits = _scan_digits(s, pos)
        if numdigits == 0:
            return NOMATCH
        return pos + numdigits


class py_Float(py_Scanner):
    def __repr__(self): return 'Float()'
    def __str__(self): return 'Float'

    def _scan(self, s, pos):
        # one of:
        #   [-+]? \d+\.\d* ([eE][-+]?\d+)?
        #   [-+]? \.\d+ ([eE][-+]?\d+)?
        #   [-+]? \d+ [eE][-+]?\d+
        # note that bare integers (e.g. 1, -1, etc.) are not accepted
        if s[pos] in u'-+':  # [-+]?
            pos += 1

        if s[pos] == u'.':  # \.\d+ ([eE][-+]?\d+)?
            dpos = _scan_digits(s, pos+1)
            if dpos == 0:
                return NOMATCH
            pos += dpos + 1
            pos += _scan_exponent(s, pos)

        else:  # other two patterns begin with \d+
            dpos = _scan_digits(s, pos)
            if dpos == 0:
                return NOMATCH
            pos += dpos

            if s[pos] == u'.':  # \d+\.\d* ([eE][-+]?\d+)?
                pos += 1
                pos += _scan_digits(s, pos)
                pos += _scan_exponent(s, pos)

            else:  # \d+ [eE][-+]?\d+
                dpos = _scan_exponent(s, pos)
                if dpos == 0:
                    return NOMATCH
                pos += dpos
        return pos


class py_BoundedString(py_Scanner):
    def __init__(self, first, last, action=None):
        self.action = action
        self.first = first
        self.last = last

    def __repr__(self):
        return 'BoundedString("{}", "{}")'.format(self.first, self.last)
    def __str__(self): return 'BoundedString'

    def _scan(self, s, pos):
        a, b = self.first, self.last
        alen, blen = len(a), len(b)
        if s[pos:pos+alen] != a:
            return NOMATCH
        pos += alen
        while s[pos:pos+blen] != b:
            if s[pos] == u'\\':
                pos += 2
            else:
                pos += 1
        return pos + blen


class py_Bounded(py_Scanner):
    def __init__(self, lhs, body, rhs, action=None):
        self.action = action
        self._lhs = lhs
        self._body = body
        self._rhs = rhs

    def __repr__(self):
        return 'Bounded({}, {}, {})'.format(
            repr(self._lhs), repr(self._body), repr(self._rhs)
        )
    def __str__(self): return 'Bounded'

    def _scan(self, s, pos):
        end = self._lhs._scan(s, pos)
        if end >= 0:
            end = self._body._scan(s, end)
            if end >= 0:
                end = self._rhs._scan(s, end)
        return end

    def match(self, s, pos=0):
        end = self._lhs._scan(s, pos)
        m = None
        if end >= 0:
            m = self._body.match(s, end)
            if m is not None:
                end = self._rhs._scan(s, m.endpos)
                if end < 0:
                    m = None
                else:
                    action = self.action
                    if action is not None:
                        m.value = action(m.value)
                    m.pos = pos
                    m.endpos = end
        return m


class py_Sequence(py_Scanner):
    def __init__(self, *scanners, action=None):
        self.action = action
        self._scanners = scanners
        self.capturing = any(s.capturing for s in scanners)

    def __repr__(self):
        return 'Sequence({})'.format(', '.join(map(repr, self._scanners)))
    def __str__(self):
        return ' '.join(map(str, self._scanners))

    def _scan(self, s, pos):
        for scanner in self._scanners:
            pos = scanner._scan(s, pos)
            if pos == NOMATCH:
                break
        return pos

    def match(self, s, pos=0):
        val = []
        end = pos
        for scanner in self._scanners:
            if scanner.capturing:
                m = scanner.match(s, end)
                if m is None:
                    return None
                end = m.endpos
                if scanner.action is None:
                    val.extend(m.value)
                else:
                    val.append(m.value)
            else:
                end = scanner._scan(s, end)
                if end == NOMATCH:
                    return None
        if not self.capturing:
            val = s[pos:end]
        action = self.action
        if action is not None:
            val = action(val)
        return Match(s, pos, end, val)


class py_Choice(py_Scanner):
    def __init__(self, *scanners, action=None):
        self.action = action
        self._scanners = scanners
        self.capturing = any(s.capturing for s in scanners)

    def __repr__(self):
        return 'Choice({})'.format(', '.join(map(repr, self._scanners)))
    def __str__(self):
        return ' | '.join(map(str, self._scanners))

    def _scan(self, s, pos):
        for scanner in self._scanners:
            endpos = scanner._scan(s, pos)
            if endpos >= 0:
                return endpos
        return NOMATCH

    def match(self, s, pos=0):
        val = None
        for scanner in self._scanners:
            m = scanner.match(s, pos)
            if m is not None:
                action = self.action
                if action is not None:
                    m.value = action(m.value)
                return m
        return None


class py_Repeat(py_Scanner):
    def __init__(self, scanner, min=0, max=-1, delimiter=None, action=None):
        self.action = action
        self._scanner = scanner
        self._min = min
        self._max = max
        self._delimiter = delimiter
        self.capturing = (scanner.capturing or
                          (delimiter is not None and delimiter.capturing))

    def __repr__(self):
        return 'Repeat({}, min={}, max={}, delimiter={})'.format(
            repr(self._scanner), self._min, self._max, repr(self._delimiter)
        )
    def __str__(self): return '{}{{{},{}{}}}'.format(
        str(self._scanner),
        self._min,
        self._max,
        ':' + str(self._delimiter) if self._delimiter is not None else ''
    )

    def _scan(self, s, pos):
        scanner, delimiter = self._scanner, self._delimiter
        a, b = self._min, self._max
        count = 0
        try:
            newpos = scanner._scan(s, pos)
            while newpos >= 0 and count != b:
                pos = newpos
                count += 1
                if delimiter is not None:
                    newpos = delimiter._scan(s, pos)
                    if newpos < 0:
                        break
                    newpos = scanner._scan(s, newpos)
                else:
                    newpos = scanner._scan(s, pos)
        except IndexError:
            pass
        if count >= a:
            return pos
        return NOMATCH

    def match(self, s, pos=0):
        scanner, delimiter = self._scanner, self._delimiter
        s_is_grp = scanner.capturing
        d_is_grp = delimiter.capturing if delimiter is not None else False
        a, b = self._min, self._max
        count = 0
        val = []
        end = pos
        try:
            m = scanner.match(s, end)
            while m is not None and count != b:
                end = m.endpos
                count += 1
                if s_is_grp:
                    if scanner.action is None:
                        val.extend(m.value)
                    else:
                        val.append(m.value)
                if delimiter is not None:
                    if d_is_grp:
                        m = delimiter.match(s, end)
                        if m is None:
                            break
                        d_end = m.endpos
                        if delimiter.action is None:
                            val.extend(m.value)
                        else:
                            val.append(m.value)
                    else:
                        d_end = delimiter._scan(s, end)
                        if d_end == NOMATCH:
                            break
                    m = scanner.match(s, d_end)
                else:
                    m = scanner.match(s, end)
        except IndexError:
            pass
        if count >= a:
            if not (s_is_grp or d_is_grp):
                val = s[pos:end]
            action = self.action
            if action is not None:
                val = action(val)
            return Match(s, pos, end, val)
        return None


class py_Optional(py_Scanner):
    def __init__(self, scanner, default=..., action=None):
        self.action = action
        self._scanner = scanner
        if default is Ellipsis:
            self._default = [] if scanner.capturing else ''
        else:
            self._default = default
        self.capturing = scanner.capturing

    def __repr__(self): return 'Optional({})'.format(repr(self._scanner))
    def __str__(self): return str(self._scanner) + '?'

    def _scan(self, s, pos):
        scanner = self._scanner
        try:
            end = scanner._scan(s, pos)
            if end == NOMATCH:
                end = pos
        except IndexError:
            end = pos
        return end

    def match(self, s, pos=0):
        scanner = self._scanner
        m = scanner.match(s, pos)
        if m is None:
            return Match(s, pos, pos, self._default)
        else:
            return m


class py_Lookahead(py_Scanner):
    def __init__(self, scanner):
        self._scanner = scanner

    def __repr__(self): return 'Lookahead({})'.format(repr(self._scanner))
    def __str__(self): return '&' + str(self._scanner)

    def _scan(self, s, pos):
        scanner = self._scanner
        if scanner._scan(s, pos) == NOMATCH:
            return NOMATCH
        else:
            return pos


class py_NegativeLookahead(py_Scanner):
    def __init__(self, scanner):
        self._scanner = scanner

    def __repr__(self):
        return 'NegativeLookahead({})'.format(repr(self._scanner))
    def __str__(self): return '!' + str(self._scanner)

    def _scan(self, s, pos):
        scanner = self._scanner
        if scanner._scan(s, pos) == NOMATCH:
            return pos
        else:
            return NOMATCH


class py_Nonterminal(py_Scanner):
    def __init__(self, grammar, name, action=None):
        self.action = action
        self._grammar = grammar
        self._name = name

    def __repr__(self): return 'Nonterminal(<dict>, "{}")'.format(self._name)
    def __str__(self): return self._name

    def _scan(self, s, pos):
        scanner = self._grammar[self._name]
        if scanner is None:
            raise Exception(
                'Nonterminal {} is not associated with a grammar'
                .format(self._name)
            )
        return scanner._scan(s, pos)

    def match(self, s, pos=0):
        scanner = self._grammar[self._name]
        m = scanner.match(s, pos)
        action = self.action
        if action is not None:
            m.value = action(m.value)
        return m


class py_Group(py_Scanner):
    def __init__(self, scanner, action=None):
        self.action = action
        self._scanner = scanner
        self.action = action
        self.capturing = True

    def __repr__(self): return 'Group({})'.format(repr(self._scanner))
    def __str__(self): return '({})'.format(str(self._scanner))

    def _scan(self, s, pos):
        scanner = self._scanner
        return scanner._scan(s, pos)

    def match(self, s, pos=0):
        scanner = self._scanner
        m = scanner.match(s, pos)
        if m is not None:
            if self.action is None:
                m.value = [m.value]
            else:
                m.value = self.action(m.value)
        return m


# use fast versions if available

Scanner             = c_Scanner or py_Scanner
Dot                 = c_Dot or py_Dot
CharacterClass      = c_CharacterClass or py_CharacterClass
Literal             = c_Literal or py_Literal
Regex               = c_Regex or py_Regex
Spacing             = c_Spacing or py_Spacing
Integer             = c_Integer or py_Integer
Float               = c_Float or py_Float
BoundedString       = c_BoundedString or py_BoundedString
Bounded             = c_Bounded or py_Bounded
Sequence            = c_Sequence or py_Sequence
Choice              = c_Choice or py_Choice
Repeat              = c_Repeat or py_Repeat
Optional            = c_Optional or py_Optional
Lookahead           = c_Lookahead or py_Lookahead
NegativeLookahead   = c_NegativeLookahead or py_NegativeLookahead
Nonterminal         = c_Nonterminal or py_Nonterminal
Group               = c_Group or py_Group

# convenient partial applications

ZeroOrMore = partial(Repeat, min=0, max=-1, delimiter=None)
OneOrMore  = partial(Repeat, min=1, max=-1, delimiter=None)

# utility functions

def split(s, sep=u' \t\v\n\f\r', maxsplit=-1, esc=u'\\', quotes=u'"\''):
    start = pos = numsplit = 0
    end = len(s)
    tokens = []
    in_quotes = False
    q = u''
    while pos < end and (maxsplit < 0 or numsplit < maxsplit):
        c = s[pos]
        if c in esc:
            if pos == end-1:
                raise ValueError('Runaway escape sequence.')
            pos += 1
        elif in_quotes is True:
            if c == q:
                tokens.append(s[start:pos+1])
                numsplit += 1
                start = pos+1
                in_quotes = False
        elif c in quotes:
            if start < pos:
                tokens.append(s[start:pos])
                numsplit += 1
            start = pos
            q = c
            in_quotes = True
        elif c in sep:
            if start < pos:
                tokens.append(s[start:pos])
                numsplit += 1
            start = pos + 1
        pos += 1
    if start < end:
        tokens.append(s[start:end])
    return tokens


# helper functions

# (these helpers do not follow the normal return-value semantics)
def _scan_digits(s, pos):
    i = 0
    try:
        while u'0' <= s[pos+i] <= u'9':
            i += 1
    except IndexError:
        pass
    return i


def _scan_exponent(s, pos):
    numdigits = 0
    try:
        if s[pos] in u'eE':
            if s[pos+1] in '-+':
                numdigits = _scan_digits(s, pos+2)
                if numdigits > 0:
                    return numdigits + 2
            else:
                numdigits = _scan_digits(s, pos+1)
                if numdigits > 0:
                    return numdigits + 1
    except IndexError:
        pass
    return 0
