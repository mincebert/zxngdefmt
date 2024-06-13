#!/usr/bin/env python3



import re
import sys



DOCUMENT_RE = "@[^{@]"

LINK_RE = '@{ *"(?P<text>[^"]+)" LINK [^ }]+ *}'
ATTR_RE = "@{\w+}"
MARKUP_RE = f"({LINK_RE}|{ATTR_RE})"

LITERAL_RE = "@(?P<char>[^{])"
TEXT_RE = "[^@ ]+"
SPACE_RE = " +"

TOKEN_RE = f"(?P<token>{MARKUP_RE}|{LITERAL_RE}|{TEXT_RE}|{SPACE_RE})(?P<remainder>.*)"


LINE_MAXLEN = 40


def render_token(t):
    m = re.match(LINK_RE, t)
    if m:
        return m["text"]

    m = re.match(LITERAL_RE, t)
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



buffer_markup = ""
buffer_render = ""

with sys.stdin as f:
    def writebuffer():
        global buffer_markup, buffer_render
        print("OUTPUT BUFFER >>>", buffer_markup)
        buffer_markup = ""
        buffer_render = ""

    for l in f:
        if re.match(DOCUMENT_RE, l):
            writebuffer()
            print("DOC >>>", l)
            continue

        # TODO: need to handle line beginning with space

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

            token_render = render_token(token)
            if len(buffer_render + token_render) > LINE_MAXLEN:
                print("MAXLEN REACHED!")
                writebuffer()

            # TODO: skip spaces at start of line
            buffer_markup += token
            buffer_render += token_render

writebuffer()