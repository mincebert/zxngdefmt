# zxngdefmt/token.py



import re



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

# start of a node
NODE_CMDS_RE = r"@node (?P<name>\S+)"

# matching a linked node token (for constructing node links)
NODAL_CMDS_RE = r"@(?P<link>(node|prev|next|toc)) (?P<name>\S+)"

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


# TODO

INDEX_RE = (r'('
            + LINK_RE
            + r"|(?P<static_text>\S+(\s{,2}\S+)*)"
            + r")?"
            + r"(\s{3,}(?P<remainder>.+))?")

INDEX_REF_RE = LINK_RE + r"(,\s+(?P<remainder>.+))?"



# --- functions ---



def rendertoken(t):
    """Render a NextGuide token (which could be markup, or a literal
    word, or block of spaces) into the text that would be displayed on
    screen (ignoring formatting).  This is used to work out the length
    of rendered markup and calculate displayed line lengths; it is not
    used to generate output.
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

        else:
            return c

    # attribute formatting codes don't render to anything displayed
    m = re.match(ATTR_RE, t)
    if m:
        return ""

    # we have a literal word or block of spaces - just use that directly
    return t



def renderstring(s):
    # start with the returned string empty
    r = ""

    # go through the string matching tokens (markup, literal or spaces)
    remainder = s
    while remainder:
        m = re.match(TOKEN_RE, remainder)

        if not m:
            raise AssertionError(
                "failed to match next token in: " + remainder)

        token, remainder = m.group("token", "remainder")

        r += rendertoken(token)

    return r
