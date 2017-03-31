
import re


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
    'Nonterminal',
    'Group',
    'split',
]

try:
    from grammarian._scanners import (
        Match           as c_Match,
        Scanner         as c_Scanner,
        Nonterminal     as c_Nonterminal,
        Group           as c_Group,
        Bounded         as c_Bounded,
        Repeat          as c_Repeat,
        Dot             as c_Dot,
        CharacterClass  as c_CharacterClass,
        Literal         as c_Literal,
        BoundedString   as c_BoundedString,
        Sequence        as c_Sequence,
        Choice          as c_Choice,
        Spacing         as c_Spacing,
        Integer         as c_Integer,
        Float           as c_Float,
        Regex           as c_Regex
    )
except ImportError:
    c_Match         = None
    c_Scanner       = None
    c_Nonterminal   = None
    c_Group         = None
    c_Bounded       = None
    c_Repeat        = None
    c_Dot           = None
    c_CharacterClass= None
    c_Literal       = None
    c_BoundedString = None
    c_Sequence      = None
    c_Choice        = None
    c_Spacing       = None
    c_Integer       = None
    c_Float         = None
    c_Regex         = None

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
    grouped = False
    action = None

    def scan(self, s, pos=0):
        try:
            return self._scan(s, pos)
        except IndexError:
            return NOMATCH

    def scanpos(self, s, pos=0):
        end = self.scan(s, pos)
        if end == NOMATCH:
            return pos
        return end

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
    def _scan(self, s, pos):
        s[pos]  # check for IndexError
        return pos + 1


class py_CharacterClass(py_Scanner):
    def __init__(self, clsstr):
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

    def _scan(self, s, pos):
        c = s[pos]
        if c in self._chars or any(a <= c <= b for a, b in self._ranges):
            return pos + 1
        return NOMATCH


class py_Literal(py_Scanner):
    def __init__(self, x):
        self._x = x
        self._xlen = len(x)

    def _scan(self, s, pos):
        end = pos + self._xlen
        if s[pos:end] != self._x:
            return NOMATCH
        return end


class py_Regex(py_Scanner):
    def __init__(self, pattern):
        if hasattr(pattern, 'match'):
            self.regex = pattern
        else:
            self.regex = re.compile(pattern)

    def _scan(self, s, pos):
        m = self.regex.match(s, pos=pos)
        if m is None:
            return NOMATCH
        else:
            return m.end()


class py_Spacing(py_Scanner):
    def __init__(self, ws=u' \t\n\r\f\v'):
        self._ws = ws

    def _scan(self, s, pos):
        ws = self._ws
        try:
            while s[pos] in ws:
                pos += 1
        except IndexError:
            pass
        return pos


class py_Integer(py_Scanner):
    def _scan(self, s, pos):
        # [-+]? \d+
        if s[pos] in u'-+':
            pos += 1
        numdigits = _scan_digits(s, pos)
        if numdigits == 0:
            return NOMATCH
        return pos + numdigits


class py_Float(py_Scanner):
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
    def __init__(self, first, last):
        self.first = first
        self.last = last

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
    def __init__(self, lhs, body, rhs):
        self._lhs = lhs
        self._body = body
        self._rhs = rhs

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
    def __init__(self, *scanners):
        self._scanners = scanners
        self._no_groups = not any(s.grouped for s in scanners)

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
            if scanner.grouped:
                m = scanner.match(s, end)
                if m is None:
                    return None
                end = m.endpos
                val.append(m.value)
            else:
                end = scanner._scan(s, end)
                if end == NOMATCH:
                    return None
        if self._no_groups:
            val = s[pos:end]
        action = self.action
        if action is not None:
            val = action(val)
        return Match(s, pos, end, val)


class py_Choice(py_Scanner):
    def __init__(self, *scanners):
        self._scanners = scanners

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
    def __init__(self, scanner, min=0, max=-1, delimiter=None):
        self._scanner = scanner
        self._min = min
        self._max = max
        self._delimiter = delimiter

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
        s_is_grp, d_is_grp = scanner.grouped, delimiter.grouped
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
                    val.append(m.value)
                if delimiter is not None:
                    if d_is_grp:
                        m = delimiter.match(s, end)
                        if m is None:
                            break
                        d_end = m.endpos
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


class py_Nonterminal(py_Scanner):
    def __init__(self, grammar, name):
        self._grammar = grammar
        self._name = name

    def _scan(self, s, pos):
        scanner = self._grammar[self._name]
        return scanner._scan(s, pos)

    def match(self, s, pos=0):
        scanner = self._grammar[self._name]
        m = scanner.match(s, pos)
        action = self.action
        if action is not None:
            m.value = action(m.value)
        return m


def py_Group(scanner, action=None):
    scanner.grouped = True
    scanner.action = action
    return scanner


# use fast versions if available

Scanner         = c_Scanner or py_Scanner
Nonterminal     = c_Nonterminal or py_Nonterminal
Group           = c_Group or py_Group
Bounded         = c_Bounded or py_Bounded
Repeat          = c_Repeat or py_Repeat
Dot             = c_Dot or py_Dot
CharacterClass  = c_CharacterClass or py_CharacterClass
Literal         = c_Literal or py_Literal
BoundedString   = c_BoundedString or py_BoundedString
Sequence        = c_Sequence or py_Sequence
Choice          = c_Choice or py_Choice
Spacing         = c_Spacing or py_Spacing
Integer         = c_Integer or py_Integer
Float           = c_Float or py_Float
Regex           = c_Regex or py_Regex


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
