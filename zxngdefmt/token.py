# zxngdefmt/token.py

# Tokens are pieces of text in a NextGuide document and can be literal
# text or commands.
#
# This module help parse and render these.



import re



# --- constants ---



# <?>_RE = string
#
# Regular expressions to match various bits of NextGuide markup.


# link to another node
LINK_RE = r'@{ *"(?P<link_text>[^"]+)" LINK (?P<link_target>[^ }]+) *}'

# formatting attribute
ATTR_RE = r"@{\w+}"

# literal characters
LITERALTOKEN_RE = r"@(?P<char>[^{])"

# plain (unformatted) word (as opposed to markup)
WORD_RE = r"[^@ ]+"

# one or more spaces
SPACE_RE = r"(?P<space> +)"

# match any type of markup token or word or block of spaces
TOKEN_RE = (r"(?P<token>"
            + LINK_RE
            + r'|' + ATTR_RE
            + r'|' + LITERALTOKEN_RE
            + r'|' + WORD_RE
            + r'|' + SPACE_RE
            + r')'
            + r"(?P<remainder>.*)")

# start of a new node
NODE_CMDS_RE = r"@node (?P<name>\S+)"

# nodal commands for a linked node token
NODE_LINK_CMDS_RE = r"@(?P<link>(node|prev|next|toc)) (?P<name>\S+)"

# lines to ignore:
#
# - a token with hyphens (a separator between nodes), or
#
# - a remark command
IGNORE_RE = r"@(-+|rem\s)"


# LITERALLINE_RE = string
#
# Regular expression to match lines which must be included in the output
# guide literally (i.e. without reformatting).

LITERALLINE_RE = (
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
    + r'|' + LINK_RE + r'$'

    + r')')



# --- functions ---



def rendertoken(t):
    """Return a single rendered NextGuide token (which could be a
    literal piece of text, a command, or block of spaces) into the plain
    text equivalent (without formatting) that would be displayed on
    screen.

    This is used to work out the length of rendered markup and calculate
    displayed line lengths; it is not used to generate output.
    """

    # if the token is a link, use the displayed text field
    m = re.match(LINK_RE, t)
    if m:
        return m["link_text"]

    # if the token is a literal character, convert that to the displayed
    # character
    m = re.match(LITERALTOKEN_RE, t)
    if m:
        c = m["char"]

        # '@(' is the copyright sign
        if c == "(":
            return "\N{COPYRIGHT SIGN}"

        # everything else we treat as whatever is after the '@'
        else:
            return c

    # attribute formatting codes don't render to anything displayed
    m = re.match(ATTR_RE, t)
    if m:
        return ''

    # we have a literal word or block of spaces - just use that directly
    return t



def renderstring(s):
    """Return a string containing tokens (literals, commands, spaces,
    etc.) rendered into their plain text equivalent.  It is a wrapper
    around rendertoken() which iteratively renders all the tokens in a
    string.
    """

    # start with the rendered string empty
    r = ''

    # go through the string matching tokens (markup, literal or spaces)
    remainder = s
    while remainder:
        m = re.match(TOKEN_RE, remainder)

        # if we couldn't match a token, something has gone irretrievably
        # wrong (probably with the regexp)
        if not m:
            raise ValueError("failed to match next token in: " + remainder)

        token, remainder = m.group("token", "remainder")

        r += rendertoken(token)

    return r
