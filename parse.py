# Ye Guoquan, A0188947A
from lex import TokenType, Lexer, TokenInfo
from typing import List, Callable, Any, Collection
import ast
import sys


class ParseException(Exception):
    pass


class Parser:

    def __init__(self, lexer):
        self.tokens: List[TokenInfo] = lexer.get_all_tokens()
        # clear comments
        tokens: List[TokenInfo] = []
        for token in self.tokens:
            if not (token.token_type == TokenType.TOKEN_COMMENT or token.token_type == TokenType.TOKEN_MULTICOMMENT):
                tokens.append(token)
        self.tokens: List[TokenInfo] = tokens
        self.head: int = 0
        self.length: int = len(self.tokens)

    def next_token_is(self, t: TokenType) -> TokenInfo:
        if self.head != self.length and self.tokens[self.head].token_type == t:
            token: TokenInfo = self.tokens[self.head]
            self.head += 1
            return token
        else:
            raise ParseException(f"next_token_is(): unexpected symbol {self.tokens[self.head].value} at line {self.tokens[self.head].line_num}")

    def peek_token_is(self, t: TokenType) -> bool:
        if self.tokens[self.head].token_type == t:
            return True
        return False


    def peek_token_at_offset(self, t: int) -> TokenType:
        if (self.head + t) >= self.length:
            return None
        return self.tokens[self.head + t].token_type

    def expect_type(self) -> bool:
        return self.peek_token_is(TokenType.TOKEN_TYPE_INT) or \
               self.peek_token_is(TokenType.TOKEN_TYPE_STRING) or \
               self.peek_token_is(TokenType.TOKEN_TYPE_VOID) or \
               self.peek_token_is(TokenType.TOKEN_TYPE_BOOL) or \
               self.peek_token_is(TokenType.TOKEN_CNAME)


    def expect_id_at(self, t: int) -> bool:
        token_type = self.peek_token_at_offset(t)
        return token_type == TokenType.TOKEN_NAME

    def longest_of(self, rules: Collection[Callable[[], Any]]) -> ast.ASTNode:
        prev_head = self.head
        max_consumed: int = 0
        best_node: ast.ASTNode = None
        best_head: int = 0
        for rule in rules:
            try:
                node = rule()
                consumed = self.head - prev_head
                if (consumed > max_consumed):
                    max_consumed = consumed
                    best_node = node
                    best_head = self.head
            except ParseException:
                pass
            finally:
                self.head = prev_head
        if best_node is None:
            rule_names: List[str] = list(map(lambda x: x.__name__, rules))
            raise ParseException(f"No rule matched. Tried {rule_names}.")
        self.head = best_head
        return best_node

    # <Program> -> <MainClass> <ClassDecl>*
    def parse_program(self) -> ast.Program:
        main_class = self.parse_mainClass()
        classes: List[ast.Class] = []
        while self.peek_token_is(TokenType.TOKEN_CLASS):
            classes.append(self.parse_classDecl())
        return ast.Program(main_class, classes)

    # <MainClass> -> class <CNAME> {Void main ( <fmlist> ) <MdBody> }
    def parse_mainClass(self) -> ast.Class:
        self.next_token_is(TokenType.TOKEN_CLASS)
        class_name = ast.Type(self.next_token_is(TokenType.TOKEN_CNAME))
        self.next_token_is(TokenType.TOKEN_LEFT_BRACKET)
        no_fields : List[ast.VarDecl] = []
        ret_type = ast.Type(self.next_token_is(TokenType.TOKEN_TYPE_VOID))
        id = ast.Identifier(self.next_token_is(TokenType.TOKEN_MAIN))
        self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
        formals: List[ast.Formal] = []
        while not self.peek_token_is(TokenType.TOKEN_RIGHT_PARAM):
            formals.append(self.parse_fml())
        self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
        body = self.parse_mdBody()
        self.next_token_is(TokenType.TOKEN_RIGHT_BRACKET)
        main = ast.Method(ret_type, id, formals, body)
        return ast.Class(class_name, no_fields, [main])

    # <ClassDecl> -> class <CNAME> { <VarDecl> * <MdDecl> }
    def parse_classDecl(self) -> ast.Class:
        self.next_token_is(TokenType.TOKEN_CLASS)
        class_name = ast.Type(self.next_token_is(TokenType.TOKEN_CNAME))
        self.next_token_is(TokenType.TOKEN_LEFT_BRACKET)
        fields: List[ast.VarDecl] = []
        while self.peek_token_at_offset(2) == TokenType.TOKEN_SEMICOLON:
            fields.append(self.parse_varDecl())
        methods : List[ast.Method] = []
        while self.peek_token_at_offset(2) == TokenType.TOKEN_LEFT_PARAM:
            methods.append(self.parse_mdDecl())
        self.next_token_is(TokenType.TOKEN_RIGHT_BRACKET)
        return ast.Class(class_name, fields, methods)

    # <VarDecl> -> <Type> <id> ;
    def parse_varDecl(self) -> ast.VarDecl:
        var_type = self.parse_type()
        identifier = self.parse_id()
        self.next_token_is(TokenType.TOKEN_SEMICOLON)
        return ast.VarDecl(var_type, identifier)

    # <MdDecl> -> <Type> <id> ( <FmlList> ) <MdBody>
    def parse_mdDecl(self) -> ast.Method:
        ret_type = self.parse_type()
        identifier = self.parse_id()
        self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
        formals: List[ast.Formal] = []
        while not self.peek_token_is(TokenType.TOKEN_RIGHT_PARAM):
            formals.append(self.parse_fml())
        self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
        body = self.parse_mdBody()
        return ast.Method(ret_type, identifier, formals, body)

    # <Fml> -> <Type> <id> , | <Type> <id>
    def parse_fml(self) -> ast.Formal:
        arg_type = self.parse_type()
        identifier = self.parse_id()
        if self.peek_token_is(TokenType.TOKEN_COMMA):
            self.next_token_is(TokenType.TOKEN_COMMA)
        return ast.Formal(arg_type, identifier)

    # Int | Bool | String | Void | <CNAME>
    def parse_type(self) -> ast.Type:
        token_type = self.peek_token_at_offset(0)
        if token_type == TokenType.TOKEN_TYPE_INT:
            return ast.Type(self.next_token_is(TokenType.TOKEN_TYPE_INT))
        elif token_type == TokenType.TOKEN_TYPE_BOOL:
            return ast.Type(self.next_token_is(TokenType.TOKEN_TYPE_BOOL))
        elif token_type == TokenType.TOKEN_TYPE_STRING:
            return ast.Type(self.next_token_is(TokenType.TOKEN_TYPE_STRING))
        elif token_type == TokenType.TOKEN_TYPE_VOID:
            return ast.Type(self.next_token_is(TokenType.TOKEN_TYPE_VOID))
        elif token_type == TokenType.TOKEN_CNAME:
            return ast.Type(self.next_token_is(TokenType.TOKEN_CNAME))

    # { <VarDecl>* <Stmt>+ }
    def parse_mdBody(self) -> ast.Block:
        self.next_token_is(TokenType.TOKEN_LEFT_BRACKET)
        varDecls: List[ast.VarDecl] = []
        while self.expect_type() and self.expect_id_at(1) and self.peek_token_at_offset(2) == TokenType.TOKEN_SEMICOLON:
            varDecls.append(self.parse_varDecl())
        statements: List[ast.Statement] = []
        statements.append(self.parse_stmt())
        while not self.peek_token_is(TokenType.TOKEN_RIGHT_BRACKET):
            statements.append(self.parse_stmt())
        self.next_token_is(TokenType.TOKEN_RIGHT_BRACKET)
        return ast.Block(varDecls, statements)

    # <Stmt> -> 
    def parse_stmt(self) -> ast.Statement:
        token_type = self.peek_token_at_offset(0)
        # if ( Exp ) { <Stmt>+ } { <Stmt>+ }
        if token_type == TokenType.TOKEN_IF:
            self.next_token_is(TokenType.TOKEN_IF)
            self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
            condition = self.parse_exp()
            self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
            self.next_token_is(TokenType.TOKEN_LEFT_BRACKET)
            true_stmts: List[ast.Statement] = []
            true_stmts.append(self.parse_stmt())
            while not self.peek_token_is(TokenType.TOKEN_RIGHT_BRACKET):
                true_stmts.append(self.parse_stmt())
            self.next_token_is(TokenType.TOKEN_RIGHT_BRACKET)
            self.next_token_is(TokenType.TOKEN_ELSE)
            self.next_token_is(TokenType.TOKEN_LEFT_BRACKET)
            false_stmts: List[ast.Statement] = []
            false_stmts.append(self.parse_stmt())
            while not self.peek_token_is(TokenType.TOKEN_RIGHT_BRACKET):
                false_stmts.append(self.parse_stmt())
            self.next_token_is(TokenType.TOKEN_RIGHT_BRACKET)
            # although specificatio does not allow variable declaration in if branch, it is a block after all
            return ast.IfThenElse(condition, ast.Block([], true_stmts), ast.Block([], false_stmts))
        # while ( <Exp> ) { <Stmt>+ }
        elif token_type == TokenType.TOKEN_WHILE:
            self.next_token_is(TokenType.TOKEN_WHILE)
            self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
            condition = self.parse_exp()
            self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
            self.next_token_is(TokenType.TOKEN_LEFT_BRACKET)
            statements: List[ast.Statement] = []
            statements.append(self.parse_stmt())
            while not self.peek_token_is(TokenType.TOKEN_RIGHT_BRACKET):
                statements.append(self.parse_stmt())
            self.next_token_is(TokenType.TOKEN_RIGHT_BRACKET)
            return ast.While(condition, ast.Block([], statements))
        # readln ( id ) ;
        elif token_type == TokenType.TOKEN_READLN:
            self.next_token_is(TokenType.TOKEN_READLN)
            self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
            identifier = self.parse_id()
            self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
            self.next_token_is(TokenType.TOKEN_SEMICOLON)
            return ast.Readln(identifier)
        # println ( Exp ) ;
        elif token_type == TokenType.TOKEN_PRINTLN:
            self.next_token_is(TokenType.TOKEN_PRINTLN)
            self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
            identifier = self.parse_exp()
            self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
            self.next_token_is(TokenType.TOKEN_SEMICOLON)
            return ast.Println(identifier)
        # <id> = <Exp> ;
        elif self.expect_id_at(0) and self.peek_token_at_offset(1) == TokenType.TOKEN_ASSIGN:
            identifier = self.parse_id()
            self.next_token_is(TokenType.TOKEN_ASSIGN)
            expr = self.parse_exp()
            self.next_token_is(TokenType.TOKEN_SEMICOLON)
            return ast.Assignment(identifier, expr)
        # return <Exp> ; | return ;
        elif token_type == TokenType.TOKEN_RETURN:
            self.next_token_is(TokenType.TOKEN_RETURN)
            ret_exp = None
            if not self.peek_token_is(TokenType.TOKEN_SEMICOLON):
                ret_exp = self.parse_exp()
            self.next_token_is(TokenType.TOKEN_SEMICOLON)
            return ast.Return(ret_exp)
        # <Atom>.<id> = <Exp> ; | <Atom> ( <ExpList> ) ;
        else:
            atom = self.parse_atom()
            if isinstance(atom, ast.AtomAccess):
                self.next_token_is(TokenType.TOKEN_ASSIGN)
                expr = self.parse_exp()
                self.next_token_is(TokenType.TOKEN_SEMICOLON)
                return ast.Assignment(atom, expr)
            elif isinstance(atom, ast.AtomCall):
                self.next_token_is(TokenType.TOKEN_SEMICOLON)
                return ast.MethodCall(atom)
            # else error needed?

    # <Exp> -> <BExp> | <AExp> | <SExp>
    def parse_exp(self) -> ast.Expr:
        return self.longest_of([self.parse_boolExp, self.parse_arithExp, self.parse_stringExp])

    # <AExp> -> <AExp> + <Term> | <AExp> - <Term> | <Term>
    def parse_arithExp(self) -> ast.Expr:
        arithExp = self.parse_term()
        while self.peek_token_is(TokenType.TOKEN_PLUS) or self.peek_token_is(TokenType.TOKEN_MINUS):
            if self.peek_token_is(TokenType.TOKEN_PLUS):
                operator = ast.BinaryOperator(self.next_token_is(TokenType.TOKEN_PLUS))
            else:
                operator = ast.BinaryOperator(self.next_token_is(TokenType.TOKEN_MINUS))
            rhs = self.parse_term()
            arithExp = ast.BinaryOp(arithExp, operator, rhs)
        return arithExp

    # <Term> -> <Term> * <Ftr> | <Term> / <Ftr> | <Ftr>
    def parse_term(self) -> ast.Expr:
        term = self.parse_ftr()
        while self.peek_token_is(TokenType.TOKEN_TIMES) or self.peek_token_is(TokenType.TOKEN_DIVIDE):
            if self.peek_token_is(TokenType.TOKEN_TIMES):
                operator = ast.BinaryOperator(self.next_token_is(TokenType.TOKEN_TIMES))
            else:
                operator = ast.BinaryOperator(self.next_token_is(TokenType.TOKEN_DIVIDE))
            rhs = self.parse_ftr()
            term = ast.BinaryOp(term, operator, rhs)
        return term

    # <Ftr> -> DIGITS | -<Ftr> | <Atom>
    def parse_ftr(self) -> ast.UnaryOp:
        negative = 0
        operator: ast.UnaryOperator = None
        while (self.peek_token_is(TokenType.TOKEN_MINUS)):
            operator = ast.UnaryOperator(self.next_token_is(TokenType.TOKEN_MINUS))
            negative += 1
        if self.peek_token_is(TokenType.TOKEN_DIGITS):
            digits = ast.Integer(self.next_token_is(TokenType.TOKEN_DIGITS))
            return ast.UnaryOp(operator, negative, digits)
        else:
            atom = self.parse_atom()
            return ast.UnaryOp(operator, negative, atom)

    # <SExp> + <SExp> | STRING_LITERAL | <Atom>
    def parse_stringExp(self) -> ast.Expr:
        stringExp: ast.Expr
        if self.peek_token_is(TokenType.TOKEN_STRING):
            stringExp = ast.String(self.next_token_is(TokenType.TOKEN_STRING))
        else:
            stringExp = self.parse_atom()
        while self.peek_token_is(TokenType.TOKEN_PLUS):
            operator = ast.BinaryOperator(self.next_token_is(TokenType.TOKEN_PLUS))
            if self.peek_token_is(TokenType.TOKEN_STRING):
                rhs = ast.String(self.next_token_is(TokenType.TOKEN_STRING))
            else:
                rhs = self.parse_atom()
            stringExp = ast.BinaryOp(stringExp, operator, rhs)
        return stringExp

    # <BExp> -> <BExp> || <Conj> | <Conj>
    def parse_boolExp(self) -> ast.Expr:
        boolExp = self.parse_conj()
        while self.peek_token_is(TokenType.TOKEN_OR):
            operator = ast.BinaryOperator(self.next_token_is(TokenType.TOKEN_OR))
            rhs = self.parse_conj()
            boolExp = ast.BinaryOp(boolExp, operator, rhs)
        return boolExp

    # <Conj> -> <Conj> && <RExp> | <RExp>
    def parse_conj(self) -> ast.Expr:
        conj = self.parse_rexp()
        while self.peek_token_is(TokenType.TOKEN_AND):
            operator = ast.BinaryOperator(self.next_token_is(TokenType.TOKEN_AND))
            rhs = self.parse_rexp()
            conj = ast.BinaryOp(conj, operator, rhs)
        return conj

    # <RExp> -> <AExp> <BOp> <AExp> | <BGrd>
    def parse_rexp(self) -> ast.Expr:
        save_head = self.head
        try:
            lhs_exp = self.parse_arithExp()
            op = self.parse_BOp()
            rhs_exp = self.parse_arithExp()
            return ast.BinaryOp(lhs_exp, op, rhs_exp)
        except:
            self.head = save_head
            return self.parse_BGrd()

    # <BGrd> -> !<BGrd> | true | false | <Atom>
    def parse_BGrd(self) -> ast.UnaryOp:
        negate = 0
        operator: ast.UnaryOperator = None
        while self.peek_token_is(TokenType.TOKEN_NEGATE):
            operator = ast.UnaryOperator(self.next_token_is(TokenType.TOKEN_NEGATE))
            negate += 1
        if self.peek_token_is(TokenType.TOKEN_TRUE):
            operand = ast.Boolean(self.next_token_is(TokenType.TOKEN_TRUE))
        elif self.peek_token_is(TokenType.TOKEN_FALSE):
            operand = ast.Boolean(self.next_token_is(TokenType.TOKEN_FALSE))
        else:
            operand = self.parse_atom()
        return ast.UnaryOp(operator, negate, operand)

    # <BOp> -> < | > | <= | >= | == | !=
    def parse_BOp(self) -> ast.RelativeOperator:
        token_type = self.peek_token_at_offset(0)
        if token_type == TokenType.TOKEN_SMALLER:
            return ast.RelativeOperator(self.next_token_is(TokenType.TOKEN_SMALLER))
        elif token_type == TokenType.TOKEN_SMALLER_EQUAL:
            return ast.RelativeOperator(self.next_token_is(TokenType.TOKEN_SMALLER_EQUAL))
        elif token_type == TokenType.TOKEN_LARGER:
            return ast.RelativeOperator(self.next_token_is(TokenType.TOKEN_LARGER))
        elif token_type == TokenType.TOKEN_LARGER_EQUAL:
            return ast.RelativeOperator(self.next_token_is(TokenType.TOKEN_LARGER_EQUAL))
        elif token_type == TokenType.TOKEN_EQUAL:
            return ast.RelativeOperator(self.next_token_is(TokenType.TOKEN_EQUAL))
        elif token_type == TokenType.TOKEN_NOT_EQUAL:
            return ast.RelativeOperator(self.next_token_is(TokenType.TOKEN_NOT_EQUAL))

    # <Atom> ->
    def parse_atom(self) -> ast.Atom:
        token_type = self.peek_token_at_offset(0)
        atom: ast.Atom
        # this
        if token_type == TokenType.TOKEN_THIS:
            # Note: the specification allows sth like "this(explist)" but in real language should not allow
            self.next_token_is(TokenType.TOKEN_THIS)
            atom = ast.This()
        # new <cname> ()
        elif token_type == TokenType.TOKEN_NEW:
            self.next_token_is(TokenType.TOKEN_NEW)
            cname = self.next_token_is(TokenType.TOKEN_CNAME)
            self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
            self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
            atom = ast.NewClass(cname)
        # ( <Exp> )
        elif token_type == TokenType.TOKEN_LEFT_PARAM:
            self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
            expr = self.parse_exp()
            self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
            atom = ast.AtomExpr(expr)
        # null
        elif token_type == TokenType.TOKEN_NULL:
            self.next_token_is(TokenType.TOKEN_NULL)
            atom = ast.Null()
        # id
        else:
            atom = self.parse_id()
        while self.peek_token_is(TokenType.TOKEN_DOT) or self.peek_token_is(TokenType.TOKEN_LEFT_PARAM):
            # <Atom> . <id>
            if self.peek_token_is(TokenType.TOKEN_DOT):
                self.next_token_is(TokenType.TOKEN_DOT)
                identifier = self.parse_id()
                atom = ast.AtomAccess(atom, identifier)
            # <Atom> ( <ExpList> )
            else:
                self.next_token_is(TokenType.TOKEN_LEFT_PARAM)
                exprList: List[ast.Expr] = []
                while not self.peek_token_is(TokenType.TOKEN_RIGHT_PARAM):
                    exprList.append(self.parse_exp())
                    if self.peek_token_is(TokenType.TOKEN_COMMA):
                        self.next_token_is(TokenType.TOKEN_COMMA)
                self.next_token_is(TokenType.TOKEN_RIGHT_PARAM)
                atom = ast.AtomCall(atom, exprList)
        return atom

    def parse_id(self) -> ast.Identifier:
        if (self.peek_token_is(TokenType.TOKEN_MAIN)):
            return ast.Identifier(self.next_token_is(TokenType.TOKEN_MAIN))
        return ast.Identifier(self.next_token_is(TokenType.TOKEN_NAME))

    def parse(self) -> ast.ASTNode:
        self.head = 0
        out = self.parse_program()
        if self.head < self.length - 2:
            raise ParseException("Unable to consume all tokens")
        return out


if __name__ == '__main__':
    source_file = sys.argv[1]
    with open(source_file) as f:
        source_code = f.read()
    lex = Lexer(source_code)
    parse = Parser(lex)
    print(parse.parse())
