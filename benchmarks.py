
from timeit import timeit

from textpy import scanners

def pycytime(scannernames, argstr, pattern):
    names = ['py_'+name for name in scannernames]
    pysetup = 'from textpy.scanners import {0}; f={1}({2}).scan; g={1}({2}).match'.format(
        ','.join(names), names[0], argstr.format(*names)
    )
    names = ['c_'+name for name in scannernames]
    cysetup = 'from textpy.scanners import {0}; f={1}({2}).scan; g={1}({2}).match'.format(
        ','.join(names), names[0], argstr.format(*names)
    )
    pyscan = timeit('f({})'.format(pattern), setup=pysetup, number=100000)
    cyscan = timeit('f({})'.format(pattern), setup=cysetup, number=100000)
    pymatch= timeit('g({})'.format(pattern), setup=pysetup, number=100000)
    cymatch= timeit('g({})'.format(pattern), setup=cysetup, number=100000)
    print(
        '{}({}).scan({})\n  py: {}\t{}\n  cy: {}\t{}'
        .format(scannernames[0], argstr.format(*scannernames), pattern, pyscan, pymatch, cyscan, cymatch)
    )

pycytime(['Dot'], '', '"ab"')
pycytime(['Dot'], '', '""')

pycytime(['CharacterClass'], '"abcdg-jwxyz"', '"a"')
pycytime(['CharacterClass'], '"abcdg-jwxyz"', '"m"')

pycytime(['Literal'], '"abcdefg"', '"abcdefghijklmnop"')
pycytime(['Literal'], '"abcdefg"', '"abcd"')

pycytime(['BoundedString'], '\'"\', \'"\'', '\'"a"\'')
pycytime(['BoundedString'], '\'"\', \'"\'', "\"'a'\"")

pycytime(['Integer'], '', '"-123"')
pycytime(['Integer'], '', '"a"')

pycytime(['Float'], '', '"1.01"')
pycytime(['Float'], '', '"1e5"')
pycytime(['Float'], '', '".5"')
pycytime(['Float'], '', '"123"')

print()
pycytime(['Spacing'], '', '"   \\n\\tabc"')
pycytime(['Repeat','CharacterClass'], '{1}(" \\n\\t\\r\\f\\v")', '"   \\n\\tabc"')
pycytime(['Regex'], '"\\s+"', '"   \\n\\tabc"')

print()
pycytime(['Sequence','Literal','Spacing'], '{1}("("),{2}()', '"(   xyz"')
pycytime(['Regex'], '"\(\s*"', '"(   xyz"')

print()
pycytime(['Repeat','Literal'], '{1}("abc"),min=1,max=3', '"abcabcabc"')
pycytime(['Regex'], 'r"(?:abc){{1,3}}"', '"abcabcabc"')

print()
pycytime(['Sequence','Literal'], '{1}("a"),{1}("b"),{1}("c")', '"abc"')

print()
pycytime(['Sequence','Repeat','Literal'], '{2}("a"),{1}({2}("b"))', '"abbb"')
pycytime(['Regex'], 'r"ab*"', '"abbb"')

print()
pycytime(['Repeat','Literal'], '{1}("a"),delimiter={1}(",")', '"a,a,a,a"')
pycytime(['Sequence','Repeat','Literal'], '{2}("a"),{1}({0}({2}(","),{2}("a")))', '"a,a,a,a"')
pycytime(['Regex'], 'r"a(?:,a)*"', '"a,a,a,a"')

print()
pycytime(['Choice','Literal'], '{1}("a"),{1}("b")', '"b"')

print()
pycytime(['Bounded','Group','Literal'], '{2}("a"),{1}({2}("b")),{2}("c")', '"abc"')
pycytime(['Sequence','Group','Literal'], '{2}("a"),{1}({2}("b")),{2}("c")', '"abc"')

