# zxngdefmt/token.py

# Tokens are pieces of text in a NextGuide document and can be literal
# text or commands.
#
# This module help parse and render these.



import re



# --- constants ---



# <?>_RESTR = string
# <?>_RE = re.Pattern
#
# Regular expressions to match various bits of NextGuide markup.


# link to another node
LINK_RESTR = r'@{ *"(?P<link_text>[^"]+)" LINK (?P<link_target>[^ }]+) *}'
LINK_RE = re.compile(LINK_RESTR)

# formatting attribute
ATTR_RESTR = r"@{\w+}"
ATTR_RE = re.compile(ATTR_RESTR)

# literal characters
LITERALTOKEN_RESTR = r"@(?P<char>[^{])"
LITERALTOKEN_RE = re.compile(LITERALTOKEN_RESTR)

# plain (unformatted) word (as opposed to markup)
WORD_RESTR = r"[^@ ]+"

# one or more spaces
SPACE_RESTR = r"(?P<space> +)"
SPACE_RE = re.compile(SPACE_RESTR)

# match any type of markup token or word or block of spaces
TOKEN_RE = re.compile(r"(?P<token>"
                      + LINK_RESTR
                      + r'|' + ATTR_RESTR
                      + r'|' + LITERALTOKEN_RESTR
                      + r'|' + WORD_RESTR
                      + r'|' + SPACE_RESTR
                      + r')'
                      + r"(?P<remainder>.*)")

# start of a new node
NODE_CMDS_RE = re.compile(r"@node (?P<name>\S+)")

# nodal commands for a linked node token
NODE_LINK_CMDS_RE = re.compile(
                        r"@(?P<link>(node|prev|next|toc)) (?P<name>\S+)")

# lines to ignore:
#
# - a token with hyphens (a separator between nodes), or
#
# - a remark command
IGNORE_RE = re.compile(r"@(-+|rem\s)")


# LITERALLINE_RE = string
#
# Regular expression to match lines which must be included in the output
# guide literally (i.e. without reformatting).

LITERALLINE_RE = re.compile(
    r'('

    # lines with leading spaces
    + r"\s+"

    # lines with 3 or more consecutive spaces
    + r"|.+\s{3,}"

    # lines with headers
    + r"|.*@{h\d}"

    # lines with centred or right-justified text
    + r"|@{[cr]}"

    # lines consisting solely of a single link
    + r'|' + LINK_RESTR + r'$'

    + r')')



# --- functions ---



def rendertoken(t, *, link_bracket=False):
    """Return a single rendered NextGuide token (which could be a
    literal piece of text, a command, or block of spaces) into the plain
    text equivalent (without formatting) that would be displayed on
    screen.

    This is used to work out the length of rendered markup and calculate
    displayed line lengths; it is not used when writing out guide files,
    unless a readable, plain text version is requested.

    'link_bracket' will cause links with spaces at the beginning and end
    of the link text to have those replaced by angle brackets ('<' and
    '>').  This doesn't change their length but does highlight that they
    would have been links (and makes the multiple spaces look less odd).
    """

    # if the token is a link, use the displayed text field
    m = LINK_RE.match(t)
    if m:
        t = m["link_text"]
        if link_bracket and t.startswith(' ') and t.endswith(' '):
            return '<' + t[1:-1] + '>'
        return m["link_text"]

    # if the token is a literal character, convert that to the displayed
    # character
    m = LITERALTOKEN_RE.match(t)
    if m:
        c = m["char"]

        # '@(' is the copyright sign
        if c == "(":
            return "\N{COPYRIGHT SIGN}"

        # everything else we treat as whatever is after the '@'
        else:
            return c

    # attribute formatting codes don't render to anything displayed
    m = ATTR_RE.match(t)
    if m:
        return ''

    # we have a literal word or block of spaces - just use that directly
    return t



def renderstring(s, *, link_bracket=False):
    """Return a string containing tokens (literals, commands, spaces,
    etc.) rendered into their plain text equivalent.  It is a wrapper
    around rendertoken() which iteratively renders all the tokens in a
    string.

    The 'link_bracket' argument is passed on to rendertoken().
    """

    # start with the rendered string empty
    r = ''

    # go through the string matching tokens (markup, literal or spaces)
    remainder = s
    while remainder:
        m = TOKEN_RE.match(remainder)

        # if we couldn't match a token, something has gone irretrievably
        # wrong (probably with the regexp)
        if not m:
            raise ValueError("failed to match next token in: " + remainder)

        token, remainder = m.group("token", "remainder")

        r += rendertoken(token, link_bracket=link_bracket)

    return r
