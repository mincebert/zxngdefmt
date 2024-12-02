#!/usr/bin/env python3



import re
import sys



LITERALLINE_RE = "(\s+|.+\s{3,}|@[^{@]|@{[cr]}|.*@{h\d})"

LINK_RE = '@{ *"(?P<text>[^"]+)" LINK [^ }]+ *}'
ATTR_RE = "@{\w+}"
MARKUP_RE = f"({LINK_RE}|{ATTR_RE})"

LITERALTOKEN_RE = "@(?P<char>[^{])"
TEXT_RE = "[^@ ]+"
SPACE_RE = " +"

TOKEN_RE = f"(?P<token>{MARKUP_RE}|{LITERALTOKEN_RE}|{TEXT_RE}|{SPACE_RE})(?P<remainder>.*)"


LINE_MAXLEN = 80


def render_token(t):
    m = re.match(LINK_RE, t)
    if m:
        return m["text"]

    m = re.match(LITERALTOKEN_RE, t)
    if m:
        c = m["char"]
        if c == "(":
            return "\N{COPYRIGHT SIGN}"
        else:
            return c

    m = re.match(ATTR_RE, t)
    if m:
        return ""

    return t



line_markup = ""
line_render = ""

word_markup = ""
word_render = ""

space = ""


def writeline():
    """If there is anything in it, write the current line buffer out and
    clear it, ready for the next line.
    """
    global line_markup, line_render
    if line_markup:
        print(line_markup)
        line_markup = ""
        line_render = ""


def writeliteral(l=""):
    """Write a literal line.
    """
    global line_markup, word_markup, space
    if line_markup or word_markup:
        raise AssertionError("line or word buffers not empty when"
                             " writing literal line")
    print(l)
    # if we had a space from the previous line, scrap that
    space = ""


def completeword():
    """Complete the current word.  If the rendered word would fit on the
    current line, it is just appended.  If, however, it would flow out
    of the right margin, the current line will be completed and a new
    line begun with the current word.

    Returns True if a word was completed.
    """
    global line_markup, line_render, word_markup, word_render, space

    # if no word or line, return False as we didn't actually complete a word
    if (not line_render) and (not word_render):
        return False

    if len(line_render + space + word_render) > LINE_MAXLEN:
        writeline()
        # don't add the space, as we're beginning a new line
    else:
        # add the space, as we're continuing the line
        line_markup += space
        line_render += space

    line_markup += word_markup
    line_render += word_render

    # start a new word with no space
    word_markup = ""
    word_render = ""
    space = ""

    # we completed a word so return True
    return True


def appendtoken(t):
    """Append the supplied token to the current word.
    """
    global word_markup, word_render
    word_markup += t
    word_render += render_token(t)


with sys.stdin as f:
    for l in f:
        # remove any trailing whitespace
        l = l.rstrip()

        if re.match(LITERALLINE_RE, l):
            writeline()
            writeliteral(l)
            continue

        # if the line is blank, we complete any line we're building up
        # and write a blank line
        if not l:
            writeline()
            writeliteral()
            space = ""
            continue

        # go through bits of line
        while l:
            m = re.match(TOKEN_RE, l)
            if not m:
                print(f"Something has gone wrong matching <{l}>!")
                exit(1)
            g = m.groupdict()
            token = g["token"]
            #print(f"TOKEN >>> <{token}>")
            l = g["remainder"]
            #print(f"REMAINDER >>> <{l}>")

            if re.match(SPACE_RE, token):
                completeword()
                space = token
                continue

            appendtoken(token)

        # end of line completes a word and adds a space
        if completeword():
            space = " "

# if there is something in the buffer
writeline()
