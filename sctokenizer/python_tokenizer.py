from __future__ import absolute_import

from sctokenizer.cpp_tokenizer import CppTokenizer
from sctokenizer.assets.python_keywords import keyword_set
# from sctokenizer.aset.python_operator_set import python_operator_set
from sctokenizer.token import TokenType, Token

class PythonTokenizer(CppTokenizer):
    def __init__(self):
        super().__init__()
        self.keyword_set = keyword_set

    def tokenize(self, source_str):
        len_lines = [len(x) for x in source_str.split('\n')]
        state = self.REGULAR
        pending = ''
        first_no_space = ''
        first_no_space_in_word = ''
        first_char_in_string = ''
        first_char_in_comment = ''
        cur = ''
        prev = ''
        i = 0
        t = 0
        while i < len(source_str):
            prev = cur
            cur = source_str[i]
            if i < len(source_str) - 1:
                next = source_str[i+1]
            else:
                next = ''

            if i < len(source_str) - 2:
                nextnext = source_str[i+2]
            else:
                nextnext = ''

            if prev == self.LF:
                first_no_space = ''
                first_no_space_in_word = ''
                self.linenumber += 1
                t += 1
            if cur == self.CR:
                if next == self.LF:
                    continue
                else: # Not sure about this part
                    self.linenumber += 1
                    t += 1
                    cur = self.LF
            if cur != ' ' and cur != self.TAB:
                if first_no_space == '':
                    first_no_space = cur
                if first_no_space_in_word == '':
                    first_no_space_in_word = cur
                    self.colnumber = i
            if state == self.IN_COMMENT:
                # Check end of block comment
                if cur == first_char_in_comment and \
                    next == first_char_in_comment and \
                    nextnext == first_char_in_comment:
                    first_char_in_comment = ''
                    self.colnumber = i
                    self.add_pending(cur*3, TokenType.IDENTIFIER, len_lines, t)
                    i += 3
                    state = self.REGULAR
                    continue
            elif state == self.IN_LINECOMMENT:
                # Check end of line comment
                if cur == self.LF:
                    state = self.REGULAR
            elif state == self.IN_STRING:
                # Check end of string
                if cur == first_char_in_string and prev != '\\':
                    first_char_in_string = ''
                    state = self.REGULAR
                    self.add_pending(pending, TokenType.STRING, len_lines, t)
                    pending = ''
                    first_no_space_in_word = ''
                    self.colnumber = i
                    self.add_pending(cur, TokenType.SPECIAL_SYMBOL, len_lines, t)
                else:
                    pending += cur
            elif state == self.IN_NUMBER:
                if (cur >= '0' and cur <= '9') or \
                    cur == '.' or cur == 'E' or cur == 'e':
                    pending += cur
                    i += 1
                    continue
                if (cur == '-' or cur == '+') and \
                    (prev == 'E' or prev == 'e'):
                    pending += cur
                    i += 1
                    continue
                self.add_pending(pending, TokenType.CONSTANT, len_lines, t)
                pending = ''
                first_no_space_in_word = ''
                self.colnumber = i
                if cur in self.operator_set:
                    self.add_pending(cur, TokenType.OPERATOR, len_lines, t)
                else:
                    self.add_pending(cur, TokenType.SPECIAL_SYMBOL, len_lines, t)
                state = self.REGULAR 
            elif state == self.REGULAR:
                if (first_no_space == '"' or first_no_space == "'") and \
                    cur == first_no_space and \
                    next == first_no_space and \
                    nextnext == first_no_space:
                    # Begin block comment
                    if first_char_in_comment == '':
                        first_char_in_comment = cur
                    state = self.IN_COMMENT
                    self.add_pending(pending, TokenType.IDENTIFIER, len_lines, t)
                    pending = ''
                    first_no_space_in_word = ''
                    self.colnumber = i
                    self.add_pending(cur*3, TokenType.SPECIAL_SYMBOL, len_lines, t)
                    i += 3
                    continue
                elif cur == '"' or cur == "'":
                    if first_char_in_string == '':
                        first_char_in_string = cur
                    state = self.IN_STRING
                    self.add_pending(pending, TokenType.IDENTIFIER, len_lines, t)
                    pending = ''
                    first_no_space_in_word = ''
                    self.colnumber = i
                    self.add_pending(cur, TokenType.SPECIAL_SYMBOL, len_lines, t)
                elif cur == '#':
                    # Begin line comment
                    state = self.IN_LINECOMMENT
                    self.add_pending(pending, TokenType.IDENTIFIER, len_lines, t)
                    pending = ''
                    first_no_space_in_word = ''
                    self.colnumber = i
                    self.add_pending('#', TokenType.SPECIAL_SYMBOL, len_lines, t)
                    i += 1
                    continue
                elif cur >= '0' and cur <= '9':
                    if first_no_space_in_word == cur:
                        state = self.IN_NUMBER
                        self.add_pending(pending, TokenType.IDENTIFIER, len_lines, t)
                        # first_no_space_in_word = ''
                        pending = cur
                    else:
                        pending += cur
                elif self.is_alpha(cur):
                    pending += cur
                else: # cur = + - * / , ; ...
                    self.add_pending(pending, TokenType.IDENTIFIER, len_lines, t)
                    pending = ''
                    first_no_space_in_word = ''
                    if cur > ' ': 
                        self.colnumber = i
                        if cur in self.operator_set:
                            self.add_pending(cur, TokenType.OPERATOR, len_lines, t)
                        else:
                            self.add_pending(cur, TokenType.SPECIAL_SYMBOL, len_lines, t)
                        pending = ''
            i += 1
        # End of the program
        # This need to be fixed in the future
        if len(cur) > 1 or self.is_alpha(cur):
            self.add_pending(pending, TokenType.IDENTIFIER, len_lines, t) 
        elif pending in self.operator_set:
            self.add_pending(pending, TokenType.OPERATOR, len_lines, t)
        else:
            self.add_pending(pending, TokenType.SPECIAL_SYMBOL, len_lines, t)
        self.compact_operators()
        self.compact_operators()
        return self.tokens

    def add_pending(self, pending, token_type, len_lines, t):
        if pending <= ' ':
            return
        for k in range(t):
            self.colnumber -= (len_lines[k] + 1)
        if token_type == TokenType.IDENTIFIER and \
            pending in self.keyword_set:
            self.tokens.append(Token(pending, TokenType.KEYWORD, self.linenumber, self.colnumber + 1))
        else:
            self.tokens.append(Token(pending, token_type, self.linenumber, self.colnumber + 1))

    def compact_operators(self):
        correct = []
        cur = None
        for next in self.tokens:
            # try:
            #     print (cur.token_value ,next.token_value)
            # except:
            #     print (None)
            if cur:
                if cur.token_type == TokenType.OPERATOR and \
                    next.token_type == TokenType.OPERATOR and \
                    cur.token_value not in '()[]{};' and \
                    next.token_value not in '()[]{};':
                    if cur.token_value != '<' or (cur.token_value == '<' and next.token_value != '>'):
                        cur.token_value += next.token_value
                        next = None
                correct.append(cur)
            cur = next
        if cur:
            correct.append(cur)
        self.tokens = correct
