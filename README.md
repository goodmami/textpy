![TextPy Logo](logo.png)

The TextPy package is a collection of scanners
for creating text parsers.

## Build Instructions

The Cython sources of TextPy need to be compiled to be used. Make
sure that Cython for Python 3 is installed (e.g., `apt install cython3`),
as well as a C compiler like `gcc`. Run the following to build:

    python3 setup.py build_ext --inplace

You can then run the unit tests if `pytest` is installed for Python 3:

    pytest-3

Run the JSON demo for some benchmarks:

    python3 -m examples.json_demo

If [Parsimonious](https://github.com/erikrose/parsimonious) is also
installed and importable by Python 3, then a Parsimonious-based benchmark
will also run for comparison.

## Scanners

Scanners "scan" the string for patterns and return the index where a
match ends, or the `NOMATCH` constant if there was no match.

* Dot            - scans any single character
* CharacterClass - scans any single character in the class
* Literal        - scans an exact string
* BoundedString  - scans a string from a start character to an end
                   character
* Regex          - scans a regular expression
* Integer        - scans an integer
* Float          - scans a float
* Spacing        - scans whitespace

There are some scanners that take other scanners as arguments:

* Nonterminal    - lookup a parsing function at parse-time
* Group          - creates the "value" of a match
* Sequence       - composes one or more scanners into one
* Choice         - ordered-choice of scanners; return first successful
                   result
* Repeat         - scan with a single scanner between min and max times

## Miscellaneous Functions

* `split()` - like `shlex.split()`, but with different behavior than
              the POSIX or non-POSIX modes

# Defining Grammars

## Patterns and Constructs

**NOTE:** the following table is for planning; grammar parsing is not
yet implemented, and not all features below have a function equivalent.

| pattern      | description                                      |
| ------------ | ------------------------------------------------ |
| `X = ...`    | Rule `X` returns an item                         |
| `.`          | dot; matches any single character                |
| `"..."`      | string                                           |
| `[...]`      | character class                                  |
| `/.../`      | regular expression                               |
| `A B`        | `A` and `B` are a sequence                       |
| `A | B`      | `A` and `B` are an ordered choice                |
| `(...)`      | matching group                                   |
| `(?:...)`    | non-matching group (not implemented)             |
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
| `A ^`        | cut/ratchet after matching `A` (not implemented) |

## Special Symbols

| symbol  | description                 |
| ------- | --------------------------- |
| `Start` | Starting rule for a grammar |
| `IFS`   | Internal Field Separator (**NOTE:** not currently implemented) |

## Groups, Matches, and Expression Values

You can use groups to decide what parts of an expression get stored as
parsed values. If there are no defined groups, the whole expression is
considered as one group. This behavior affects both sequences and
ordered-choices. Here are some examples:

| Pattern                   | Input     | Value                         |
| ------------------------- | --------- | ----------------------------- |
| `"a"`                     | `abc`     | `'a'`                         |
| `("a")`                   | `abc`     | `['a']`                       |
| `(("a"))`                 | `abc`     | `[['a']]`                     |
| `"a" "b"`                 | `abc`     | `'ab'`                        |
| `("a" "b") "c"`           | `abc`     | `['ab']`                      |
| `"a" ("b") "c"`           | `abc`     | `['b']`                       |
| `"a" / "b"`               | `a`       | `'a'`                         |
| ...                       | `b`       | `'b'`                         |
| `"a" / ("b")`             | `a`       | `[]`                          |
| ...                       | `b`       | `['b']`                       |
| `(("a")":"("b"))`         | `a:ba:b`  | `[['a','b']]`                 |
| `(?:("a")":"("b"))*`      | `a:ba:b`  | `['a','b','a','b']`           |
| `(("a")":"("b"))*`        | `a:ba:b`  | `[['a','b'],['a','b']]`       |
| `(?:"a" ":" "b"){:","}`   | `a:b,a:b` | `['a:b,a:b']`                 |
| `("a" ":" "b"){:","}`     | `a:b,a:b` | `[['a:b'],['a:b']]`           |
| `(("a")":"("b")){:","}`   | `a:b,a:b` | `[['a','b'],['a','b']]`       |
| `(("a")":"("b")){:(",")}` | `a:b,a:b` | `[['a','b'],[','],['a','b']]` |

It would be nice if we could also get regex-style groups from matches,
although initial tests show a marked slowdown, so this is still pending.

| Pattern                   | Input     | Groups                        |
| ------------------------- | --------- | ----------------------------- |
| `"a"`                     | `abc`     | `[]`                          |
| `("a")`                   | `abc`     | `['a']`                       |
| `(("a"))`                 | `abc`     | `[['a']]`                     |
| `"a" "b"`                 | `abc`     | `[]`                          |
| `("a" "b") "c"`           | `abc`     | `['ab']`                      |
| `"a" ("b") "c"`           | `abc`     | `['b']`                       |
| `"a" / "b"`               | `a`       | `[]`                          |
| ...                       | `b`       | `[]`                          |
| `"a" / ("b")`             | `a`       | `[]`                          |
| ...                       | `b`       | `['b']`                       |
| `(("a")":"("b"))`         | `a:ba:b`  | `[['a','b']]`                 |
| `(?:("a")":"("b"))*`      | `a:ba:b`  | `['a','b','a','b']`           |
| `(("a")":"("b"))*`        | `a:ba:b`  | `[['a','b'],['a','b']]`       |
| `(?:"a" ":" "b"){:","}`   | `a:b,a:b` | `[]`                          |
| `("a" ":" "b"){:","}`     | `a:b,a:b` | `['a:b','a:b']`               |
| `(("a")":"("b")){:","}`   | `a:b,a:b` | `[['a','b'],['a','b']]`       |
| `(("a")":"("b")){:(",")}` | `a:b,a:b` | `[['a','b'],[','],['a','b']]` |

