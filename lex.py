# Ye Guoquan, A0188947A
from typing import Tuple
from enum import Enum, auto
import re
import sys


class LexerException(Exception):
    pass


class TokenType(Enum):
    # arithmetic
    TOKEN_PLUS = auto()
    TOKEN_MINUS = auto()
    TOKEN_TIMES = auto()
    TOKEN_DIVIDE = auto()
    # relational 
    TOKEN_LARGER = auto()
    TOKEN_SMALLER = auto()
    TOKEN_EQUAL = auto()
    TOKEN_NOT_EQUAL = auto()
    TOKEN_LARGER_EQUAL = auto()
    TOKEN_SMALLER_EQUAL = auto()
    # boolean
    TOKEN_AND = auto()
    TOKEN_OR = auto()
    # string operator
    TOKEN_CONCAT = auto()

    # unary operator
    TOKEN_NEGATE = auto()
    TOKEN_NEGATIVE = auto()

    # boolean
    TOKEN_TRUE = auto()
    TOKEN_FALSE = auto()

    # punctuation
    TOKEN_LEFT_PARAM = auto()
    TOKEN_RIGHT_PARAM = auto()
    TOKEN_LEFT_BRACKET = auto()
    TOKEN_RIGHT_BRACKET = auto()
    TOKEN_SEMICOLON = auto()
    TOKEN_DOT = auto()
    TOKEN_COMMA = auto()

    # basic types
    TOKEN_ASSIGN = auto()
    TOKEN_NAME = auto()
    TOKEN_CNAME = auto()
    TOKEN_INTEGER = auto()
    TOKEN_STRING = auto()
    TOKEN_DIGITS = auto()

    # comment
    TOKEN_MULTICOMMENT = auto()
    TOKEN_COMMENT = auto()

    # keywords
    TOKEN_IF = auto()
    TOKEN_ELSE = auto()
    TOKEN_RETURN = auto()
    TOKEN_WHILE = auto()
    TOKEN_READLN = auto()
    TOKEN_PRINTLN = auto()
    TOKEN_NEW = auto()
    TOKEN_THIS = auto()
    TOKEN_NULL = auto()
    TOKEN_CLASS = auto()
    TOKEN_MAIN = auto()
    TOKEN_TYPE_INT = auto()
    TOKEN_TYPE_BOOL = auto()
    TOKEN_TYPE_STRING = auto()
    TOKEN_TYPE_VOID = auto()

    # others
    TOKEN_IGNORED = auto()
    TOKEN_EOF = auto()


KEYWORDS = {
    'if': TokenType.TOKEN_IF,
    'else': TokenType.TOKEN_ELSE,
    'return': TokenType.TOKEN_RETURN,
    'while': TokenType.TOKEN_WHILE,
    'readln': TokenType.TOKEN_READLN,
    'println': TokenType.TOKEN_PRINTLN,
    'new': TokenType.TOKEN_NEW,
    'this': TokenType.TOKEN_THIS,
    'null': TokenType.TOKEN_NULL,
    'class': TokenType.TOKEN_CLASS,
    'true' : TokenType.TOKEN_TRUE,
    'false' : TokenType.TOKEN_FALSE,
    'main' : TokenType.TOKEN_MAIN
}

TYPE_KEYWORDS = {
    'Int' : TokenType.TOKEN_TYPE_INT,
    'Bool' : TokenType.TOKEN_TYPE_BOOL,
    'String' : TokenType.TOKEN_TYPE_STRING,
    'Void' : TokenType.TOKEN_TYPE_VOID,
}


class TokenInfo:

    def __init__(self, line_num: int, token_type: TokenType, value: str):
        self.line_num = line_num
        self.token_type = token_type
        self.value = value

    def __repr__(self) -> str:
        return str((self.line_num, self.token_type, self.value))


class Lexer:

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.length = len(source_code)
        self.head = 0
        self.line_num = 1
        self.next_token_info = None

    def scan_pattern(self, pattern) -> str:
        result = re.findall(pattern, self.source_code[self.head:])
        if len(result) != 1:
            raise LexerException(
                'scan_pattern(): returned unexpected result: {} for pattern {}'.format(
                    result, pattern))
        return result[0]

    def scan_digits(self) -> str:
        return self.scan_pattern(r'^\d+')

    def scan_name(self) -> str:
        return self.scan_pattern(r'^[a-z][a-zA-Z0-9_]*')

    def scan_cname(self) -> str:
        return self.scan_pattern(r'^[A-Z][a-zA-Z0-9_]*')

    def scan_string(self) -> str:
        pos = self.head + 1
        result = '"'
        while (pos != self.length):
            result += self.source_code[pos]
            if self.source_code[pos] == '"' and self.source_code[pos-1] != '\\':
                return result
            pos += 1
        raise LexerException('scan_string(): reach the end of line')

    def scan_ignored(self) -> str:
        return self.scan_pattern(r'^[\t\n\v\f\r ]+')

    def scan_comment(self) -> str:
        head = self.head
        result = ''
        while (self.source_code[head] != '\n' and head != self.length):
            result += self.source_code[head]
            head += 1
        return result

    def scan_multicomment(self, head : int) -> str:
        pos = head + 2
        result = '/*'
        while pos < self.length - 1:
            if (self.source_code[pos:pos+2] == '/*'):
                # comment within comment, not added as token
                multi_comment = self.scan_multicomment(pos)
                pos += len(multi_comment)
                result += multi_comment
            elif (self.source_code[pos:pos+2] == '*/'):
                result += self.source_code[pos:pos+2]
                return result
            result += self.source_code[pos]
            pos += 1
        raise LexerException('scan_multicomment(): reach the end of file')

    def process_new_line(self, ignored) -> None:
        i = 0
        while i < len(ignored):
            if ignored[i:][:2] in ['\r\n', '\n\r']:
                i += 2
                self.line_num += 1
            else:
                if ignored[i] in ['\r', '\n']:
                    self.line_num += 1
                i += 1

    def get_next_token(self) -> TokenInfo:
        if self.next_token_info is not None:
            next_token_info = self.next_token_info
            self.next_token_info = None
            return next_token_info

        if self.head >= self.length:
            return TokenInfo(self.line_num, TokenType.TOKEN_EOF, 'EOF')

        next_chr = self.source_code[self.head]
        if next_chr == '/':
            if self.head + 1 < self.length and self.source_code[self.head+1] == '/':
                comment = self.scan_comment()
                self.head += len(comment)
                return TokenInfo(self.line_num, TokenType.TOKEN_COMMENT, comment)
            if self.head + 1 < self.length and self.source_code[self.head+1] == '*':
                multi_comment = self.scan_multicomment(self.head)
                self.head += len(multi_comment)
                line_num = self.line_num
                self.process_new_line(multi_comment)
                return TokenInfo(line_num, TokenType.TOKEN_MULTICOMMENT, multi_comment)
        if next_chr == '+':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_PLUS, '+')
        if next_chr == '-':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_MINUS, '-')
        if next_chr == '*':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_TIMES, '*')
        if next_chr == '/':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_DIVIDE, '/')
        if next_chr == '(':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_LEFT_PARAM, '(')
        if next_chr == ')':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_RIGHT_PARAM, ')')
        if next_chr == '{':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_LEFT_BRACKET, '{')
        if next_chr == '}':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_RIGHT_BRACKET, '}')
        if next_chr == ';':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_SEMICOLON, ';')
        if next_chr == ',':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_COMMA, ',')
        if next_chr == '.':
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_DOT, '.')
        if next_chr == '=':
            if self.head + 1 < self.length and self.source_code[self.head+1] == '=':
                self.head += 2
                return TokenInfo(self.line_num, TokenType.TOKEN_EQUAL, '==')
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_ASSIGN, '=')
        if next_chr == '>':
            if self.head + 1 < self.length and self.source_code[self.head+1] == '=':
                self.head += 2
                return TokenInfo(self.line_num, TokenType.TOKEN_LARGER_EQUAL, '>=')
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_LARGER, '>')
        if next_chr == '<':
            if self.head + 1 < self.length and self.source_code[self.head+1] == '=':
                self.head += 2
                return TokenInfo(self.line_num, TokenType.TOKEN_SMALLER_EQUAL, '<=')
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_SMALLER, '<')
        if next_chr == '&':
            if self.head + 1 < self.length and self.source_code[self.head+1] == '&':
                self.head += 2
                return TokenInfo(self.line_num, TokenType.TOKEN_AND, '&&')
        if next_chr == '|':
            if self.head + 1 < self.length and self.source_code[self.head+1] == '|':
                self.head += 2
                return TokenInfo(self.line_num, TokenType.TOKEN_OR, '||')
        if next_chr == '!':
            if self.head + 1 < self.length and self.source_code[self.head+1] == '=':
                self.head += 2
                return TokenInfo(self.line_num, TokenType.TOKEN_NOT_EQUAL, '!=')
            self.head += 1
            return TokenInfo(self.line_num, TokenType.TOKEN_NEGATE, '!')
        if next_chr.islower():
            name = self.scan_name()
            if name in KEYWORDS:
                self.head += len(name)
                return TokenInfo(self.line_num, KEYWORDS[name], name)
            self.head += len(name)
            return TokenInfo(self.line_num, TokenType.TOKEN_NAME, name)
        if next_chr.isupper():
            cname = self.scan_cname()
            if cname in TYPE_KEYWORDS:
                self.head += len(cname)
                return TokenInfo(self.line_num, TYPE_KEYWORDS[cname], cname)
            self.head += len(cname)
            return TokenInfo(self.line_num, TokenType.TOKEN_CNAME, cname)
        if next_chr.isnumeric():
            digits = self.scan_digits()
            self.head += len(digits)
            return TokenInfo(self.line_num, TokenType.TOKEN_DIGITS, digits)
        if next_chr == '"':
            string = self.scan_string()
            self.head += len(string)
            return TokenInfo(self.line_num, TokenType.TOKEN_STRING, string)
        if next_chr in ['\t', '\n', '\v', '\f', '\r', ' ']:
            ignored = self.scan_ignored()
            line_num = self.line_num
            self.head += len(ignored)
            self.process_new_line(ignored)
            return self.get_next_token()
        raise LexerException('get_next_token(): unexpected symbol {}'.format(next_chr))

    def get_all_tokens(self) -> [TokenInfo]:
        result = []
        while True: 
            token = self.get_next_token()
            result.append(token)
            if token.token_type == TokenType.TOKEN_EOF:
                return result


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    source_file = sys.argv[1]
    with open(source_file) as f:
        source_code = f.read()
    lex = Lexer(source_code).get_all_tokens()
    for token in lex:
        print(token)
