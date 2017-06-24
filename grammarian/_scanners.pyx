
import re
from functools import partial

cpdef enum:
    NOMATCH = -1
    EOS = -2


cdef class Match(object):
    cdef readonly unicode string
    cdef readonly int pos, endpos
    cdef readonly object value

    def __init__(self, unicode s, int pos, int endpos, object value=None):
        self.string = s
        self.pos = pos
        self.endpos = endpos
        self.value = value
        # self.lastindex = sum(n.lastindex for n in ast)

    cpdef int start(self, group=0):
        if group == 0:
            return self.pos
        else:
            return self._groups[group].start()

    cpdef int end(self, group=0):
        if group == 0:
            return self.endpos
        else:
            return self._groups[group].end()

    cpdef tuple span(self, group=0):
        if group == 0:
            return (self.pos, self.endpos)
        else:
            return self._groups[group].span()

    cpdef unicode group(self, group=0):
        if group == 0:
            start, end = self.pos, self.endpos
        else:
            start, end = self._groups[group].span()
        return self.string[start:end]


cdef class Scanner(object):
    cdef public bint capturing
    cdef public object action

    def __init__(self, object action=None):
        self.action = action

    cpdef int scan(self, unicode s, int pos=0) except EOS:
        try:
            return self._scan(s, pos)
        except IndexError:
            return NOMATCH

    cdef int _scan(self, unicode s, int pos) except EOS:
        return NOMATCH

    cpdef Match match(self, unicode s, int pos=0):
        cdef int end
        cdef object action = self.action
        try:
            end = self._scan(s, pos)
            if end == NOMATCH:
                return None
            else:
                if action is not None:
                    return Match(s, pos, end, action(s[pos:end]))
                else:
                    return Match(s, pos, end, s[pos:end])
        except IndexError:
            return None

    cpdef void set_grammar(self, object g):
        if hasattr(self, '_scanner'):
            self._scanner.set_grammar(g)
        if hasattr(self, '_delimiter') and self._delimiter is not None:
            self._delimiter.set_grammar(g)
        if hasattr(self, '_scanners'):
            for scanner in self._scanners:
                scanner.set_grammar(g)


cdef class Dot(Scanner):
    cdef int _scan(self, unicode s, int pos) except EOS:
        s[pos]  # check for IndexError
        return pos + 1


cdef class CharacterClass(Scanner):
    cdef list _ranges
    cdef unicode _chars
    def __init__(self, unicode clsstr, object action=None):
        self.action = action
        cdef list ranges = [], chars = []
        cdef int i = 0, n = len(clsstr)
        while i < n-2:
            if clsstr[i+1] == u'-':
                ranges.append((clsstr[i], clsstr[i+2]))
            else:
                chars.append(clsstr[i])
            i += 1
        # remaining character(s) cannot be ranges
        while i < n:
            chars.append(clsstr[i])
            i += 1
        self._chars = ''.join(chars)
        self._ranges = ranges
    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Py_UCS4 a, b, c
        c = s[pos]
        if c in self._chars:
            return pos + 1
        for a, b in self._ranges:
            if a <= c <= b:
                return pos + 1
        return NOMATCH


cdef class Literal(Scanner):
    cdef unicode _x
    cdef int _xlen
    def __init__(self, unicode x, object action=None):
        self.action = action
        self._x = x
        self._xlen = len(x)
    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef int end = pos + self._xlen
        if s[pos:end] != self._x:
            return NOMATCH
        return end


cdef class Regex(Scanner):
    cdef object _regex
    def __init__(self, object pattern, object action=None):
        self.action = action
        if hasattr(pattern, 'match'):
            self._regex = pattern
        else:
            self._regex = re.compile(pattern)
    cdef int _scan(self, unicode s, int pos) except EOS:
        m = self._regex.match(s, pos=pos)
        if m is None:
            return NOMATCH
        else:
            return m.end()


cdef class Spacing(Scanner):
    cdef unicode _ws
    def __init__(self, unicode ws=u' \n\t\r\f\v', object action=None):
        self.action = action
        self._ws = ws
    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef unicode ws = self._ws
        try:
            while s[pos] in ws:
                pos += 1
        except IndexError:
            pass
        return pos


cdef class Integer(Scanner):
    cdef int _scan(self, unicode s, int pos) except EOS:
        # [-+]? \d+
        cdef int numdigits
        if s[pos] in u'-+':
            pos += 1
        numdigits = _scan_digits(s, pos)
        if numdigits == 0:
            return NOMATCH
        return pos + numdigits


cdef class Float(Scanner):
    cdef int _scan(self, unicode s, int pos) except EOS:
        # one of:
        #   [-+]? \d+\.\d* ([eE][-+]?\d+)?
        #   [-+]? \.\d+ ([eE][-+]?\d+)?
        #   [-+]? \d+ [eE][-+]?\d+
        # note that bare integers (e.g. 1, -1, etc.) are not accepted
        cdef Py_UCS4 c
        cdef int dpos

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


cdef class BoundedString(Scanner):
    cdef unicode first, last
    def __init__(self, unicode first, unicode last, object action=None):
        self.action = action
        self.first = first
        self.last = last
    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef unicode c, a = self.first, b = self.last
        cdef int alen = len(a), blen = len(b)
        if s[pos:pos+alen] != a:
            return NOMATCH
        pos += alen
        while s[pos:pos+blen] != b:
            if s[pos] == u'\\':
                s[pos+1]  # check for IndexError
                pos += 2
            else:
                pos += 1
        return pos + blen


cdef class Bounded(Scanner):
    cdef Scanner _lhs, _body, _rhs

    def __init__(self, Scanner lhs, Scanner body, Scanner rhs,
                 object action=None):
        self.action = action
        self._lhs = lhs
        self._body = body
        self._rhs = rhs

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef int end
        end = self._lhs._scan(s, pos)
        if end >= 0:
            end = self._body._scan(s, end)
            if end >= 0:
                end = self._rhs._scan(s, end)
        return end

    cpdef Match match(self, unicode s, int pos=0):
        cdef object action = self.action
        cdef Match m
        cdef int end = self._lhs._scan(s, pos)
        if end == NOMATCH:
            return None
        m = self._body.match(s, end)
        if m is None:
            return None
        end = self._rhs._scan(s, m.endpos)
        if end == NOMATCH:
            return None
        if action is not None:
            m.value = action(m.value)
        m.pos = pos
        m.endpos = end
        return m


cdef class Sequence(Scanner):
    cdef tuple _scanners

    def __init__(self, *scanners, object action=None):
        self.action = action
        self._scanners = scanners
        self.capturing = any(s.capturing for s in scanners)

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner
        for scanner in self._scanners:
            pos = scanner._scan(s, pos)
            if pos == NOMATCH:
                break
        return pos

    cpdef Match match(self, unicode s, int pos=0):
        cdef object action = self.action
        cdef list vals = []
        cdef object val
        cdef int end = pos
        cdef Scanner scanner
        cdef Match m
        for scanner in self._scanners:
            if scanner.capturing:
                m = scanner.match(s, end)
                if m is None:
                    return None
                end = m.endpos
                if scanner.action is None:
                    vals.extend(m.value)
                else:
                    vals.append(m.value)
            else:
                end = scanner._scan(s, end)
                if end == NOMATCH:
                    return None
        if not self.capturing:
            val = s[pos:end]
        else:
            val = vals
        if action is not None:
            val = action(val)
        return Match(s, pos, end, val)


cdef class Choice(Scanner):
    cdef tuple _scanners

    def __init__(self, *scanners, object action=None):
        self.action = action
        self._scanners = scanners
        self.capturing = any(s.capturing for s in scanners)

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner
        cdef int end
        for scanner in self._scanners:
            end = scanner._scan(s, pos)
            if end >= 0:
                return end
        return NOMATCH

    cpdef Match match(self, unicode s, int pos=0):
        cdef object action = self.action
        cdef object val = None
        cdef Scanner scanner
        cdef Match m
        for scanner in self._scanners:
            m = scanner.match(s, pos)
            if m is not None:
                if action is not None:
                    m.value = action(m.value)
                return m
        return None


cdef class Repeat(Scanner):
    cdef Scanner _scanner
    cdef Scanner _delimiter
    cdef int _min, _max

    def __init__(self, Scanner scanner, int min=0, int max=-1,
                 Scanner delimiter=None, object action=None):
        self.action = action
        self._scanner = scanner
        self._min = min
        self._max = max
        self._delimiter = delimiter
        self.capturing = (scanner.capturing or
                          (delimiter is not None and delimiter.capturing))

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner = self._scanner
        cdef Scanner delim = self._delimiter
        cdef int a = self._min, b = self._max, count = 0
        cdef int newpos
        try:
            newpos = scanner._scan(s, pos)
            while newpos >= 0 and count != b:
                pos = newpos
                count += 1
                if delim is not None:
                    newpos = delim._scan(s, pos)
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

    cpdef Match match(self, unicode s, int pos=0):
        cdef object action = self.action
        cdef Scanner scanner = self._scanner
        cdef Scanner delimiter = self._delimiter
        cdef bint s_is_grp = scanner.capturing
        cdef bint d_is_grp = delimiter.capturing
        cdef int a = self._min, b = self._max, count = 0, end = pos
        cdef list vals = []
        cdef object val
        cdef Match m
        try:
            m = scanner.match(s, end)
            while m is not None and count != b:
                end = m.endpos
                count += 1
                if s_is_grp:
                    if scanner.action is None:
                        vals.extend(m.value)
                    else:
                        vals.append(m.value)
                if delimiter is not None:
                    if d_is_grp:
                        m = delimiter.match(s, end)
                        if m is None:
                            break
                        d_end = m.endpos
                        if delimiter.action is None:
                            vals.extend(m.value)
                        else:
                            vals.append(m.value)
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
            else:
                val = vals
            if action is not None:
                val = action(val)
            return Match(s, pos, end, val)
        return None


cdef class Optional(Scanner):
    cdef Scanner _scanner
    cdef object _default

    def __init__(self, Scanner scanner, object default=...,
                 object action=None):
        self.action = action
        self._scanner = scanner
        if default is Ellipsis:
            self._default = [] if scanner.capturing else ''
        else:
            self._default = default
        self.capturing = scanner.capturing

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner = self._scanner
        cdef int end
        try:
            end = scanner._scan(s, pos)
            if end == NOMATCH:
                end = pos
        except IndexError:
            end = pos
        return end

    cpdef Match match(self, unicode s, int pos=0):
        cdef Scanner scanner = self._scanner
        cdef object default = self._default
        cdef Match m
        m = scanner.match(s, pos)
        if m is None:
            return Match(s, pos, pos, default)
        else:
            return m


cdef class Lookahead(Scanner):
    cdef Scanner _scanner
    def __init__(self, Scanner scanner):
        self._scanner = scanner

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner = self._scanner
        if scanner._scan(s, pos) == NOMATCH:
            return NOMATCH
        else:
            return pos


cdef class NegativeLookahead(Scanner):
    cdef Scanner _scanner
    def __init__(self, Scanner scanner):
        self._scanner = scanner

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner = self._scanner
        if scanner._scan(s, pos) == NOMATCH:
            return pos
        else:
            return NOMATCH


cdef class Nonterminal(Scanner):
    cdef object _grammar
    cdef unicode _name

    def __init__(self, object grammar, unicode name, object action=None):
        self.action = action
        self._grammar = grammar
        self._name = name

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner
        scanner = self._grammar[self._name]
        if scanner is None:
            raise Exception(
                'Nonterminal {} is not associated with a grammar'
                .format(self._name)
            )
        return scanner._scan(s, pos)

    cpdef Match match(self, unicode s, int pos=0):
        cdef object action = self.action
        cdef Scanner scanner = self._grammar[self._name]
        cdef Match m = scanner.match(s, pos)
        if action is not None:
            m.value = action(m.value)
        return m

    cpdef void set_grammar(self, object g):
        self._grammar = g

cdef class Group(Scanner):
    cdef Scanner _scanner

    def __init__(self, Scanner scanner, object action=None):
        self.action = action
        self._scanner = scanner
        self.capturing = True

    cdef int _scan(self, unicode s, int pos) except EOS:
        cdef Scanner scanner = self._scanner
        return scanner._scan(s, pos)

    cpdef Match match(self, unicode s, int pos=0):
        cdef Scanner scanner = self._scanner
        cdef object action = self.action
        cdef Match m
        m = scanner.match(s, pos)
        if m is not None:
            if action is None:
                m.value = [m.value]
            else:
                m.value = action(m.value)
        return m


# utility functions

def split(
        unicode s not None,
        unicode sep=u' \t\v\n\f\r',
        int maxsplit=-1,
        unicode esc=u'\\',
        unicode quotes=u'"\''):
    cdef int start = 0
    cdef int pos = 0
    cdef int end = len(s)
    cdef int numsplit = 0
    cdef list tokens = []
    cdef bint in_quotes = False
    cdef unicode q = u''
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

cdef inline int _scan_digits(unicode s, int pos):
    cdef int i = 0
    try:
        while u'0' <= s[pos+i] <= u'9':
            i += 1
    except IndexError:
        pass
    return i


cdef inline bint _scan_exponent(unicode s, int pos):
    cdef int numdigits = 0
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
