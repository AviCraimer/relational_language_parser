from typing import Literal, Optional, Tuple, Union
import re


type TokenType = Union[
    Literal[
        "plus",
        "times",
        "left_paren",
        "right_paren",
        "colon",
        "equals",
        "new_line",
        "arrow",
        "def_equals",
        "rel_keyword",
        "set_keyword",
        "end_of_source",
    ],
    Tuple[Literal["identifier"], str],
]

identifier_regex = re.compile("[a-zA-Z_][a-zA-Z_0-9]*")


class Scanner:
    def __init__(self, source: str):
        self.current_char: int = 0  # index of current character of the current word
        self.current_line: int = 0  # index of the current line
        self.lines = [line for line in source.splitlines() if line != ""]
        self.tokens: list[TokenType] = []

    def error_msg(self, message: str) -> str:
        return f"""Error at line {self.current_line + 1}, column {self.current_char + 1}:
    {message}"""

    def is_at_end(self) -> bool:
        """Returns true when on the last line and current_char is past the last character. Of if current line is after the last line"""
        if self.current_line > len(self.lines) - 1:
            print("current line greater than lines")
            return True
        elif self.current_line == len(self.lines) - 1 and self.current_char >= len(
            self.lines[self.current_line]
        ):

            return True
        else:
            return False

    def get_line(self):
        if self.current_line < len(self.lines):
            return self.lines[self.current_line]
        else:
            raise ValueError(
                self.error_msg(
                    "Couldn't get line, this is likely a bug in scanner code"
                )
            )

    def get_chars(self, length: int = 1) -> str:
        """
        Gets the character at the current character or characters from the current character up to plus n characters forward.
        """
        if length < 1:
            raise ValueError(self.error_msg("Length must be 1 or greater"))

        line = self.get_line()
        char_index = self.current_char
        end_index = self.current_char + length
        if char_index < len(line):
            return line[char_index:end_index]
        else:
            return ""

    def advance_line(self):
        self.current_line += 1
        self.current_char = 0
        if self.current_line < len(self.lines):
            self.tokens.append("new_line")
        else:
            self.tokens.append("end_of_source")

    def advance(self, length: int = 1):
        if length < 1:
            raise ValueError(self.error_msg("Length must be 1 or greater"))

        if self.current_char + length < len(self.get_line()):
            self.current_char += length
        else:
            self.advance_line()

    def match(self, to_match: str):
        return self.get_chars(len(to_match)) == to_match

    def match_identifier(self):
        remaining = self.get_line()[self.current_char :]
        print("matching identifier:")
        print(remaining)
        identifier = identifier_regex.match(remaining)
        if identifier:
            return identifier.group()
        else:
            return None

    def scan_token(self):
        c = self.get_chars()
        consumed_chars = 1
        token: Optional[TokenType] = None
        line = self.get_line()
        char_index = self.current_char
        no_match_msg: str = self.error_msg(
            f"""No match at:
{line[:char_index]}>>>{line[char_index:]}<<<"""
        )

        match c:
            case "(":
                token = "left_paren"
            case ")":
                token = "right_paren"
            case ":":
                if self.match(":="):
                    consumed_chars = 2
                    token = "def_equals"
                else:
                    token = "colon"
            case "=":
                token = "equals"
            case "+":
                token = "plus"
            case "*":
                token = "times"
            case "-":
                if self.match("->"):
                    token = "arrow"
                    consumed_chars = 2
                else:
                    raise ValueError(no_match_msg)
            case "r":
                if self.match("rel"):
                    consumed_chars = 3
                    token = "rel_keyword"
            case "s":
                if self.match("set"):
                    consumed_chars = 3
                    token = "rel_keyword"
            case " ":
                print("match space")
                pass  # Ignore spaces
            case "\t":
                pass  # Ignore tabs
            # Note: newlines are already removed when lines are split
            case _:
                identifier = self.match_identifier()
                if identifier:
                    consumed_chars = len(identifier)
                    token = ("identifier", identifier)
                else:
                    raise ValueError(no_match_msg)

        if token is not None:
            self.tokens.append(token)
        self.advance(consumed_chars)

    def scan_source(self):
        while not self.is_at_end():
            self.scan_token()
        print(self.tokens)


Scanner(
    """


R  := A + BB ->

R:=A+ B

"""
).scan_source()
