# Ye Guoquan, A0188947A
from dataclasses import dataclass
from lex import TokenInfo, TokenType
from typing import List, Optional, Set, Dict


# Abstract classes

class ASTNode():
    pass

@dataclass(frozen=False)
class MethodInfo():
    name: str
    args: List[str]
    ret_type: str


@dataclass(frozen=False)
class ClassInfo():
    name: str
    fields: Dict[str, str]
    methods: Dict[str, List[MethodInfo]]

# -----------------------------------------------------------------------------------------------
# Declaration
# -----------------------------------------------------------------------------------------------
@dataclass(frozen=False)
class Type(ASTNode):
    type: TokenInfo

    @staticmethod
    def valid_types() -> Set[TokenType]:
        return {TokenType.TOKEN_TYPE_INT, TokenType.TOKEN_TYPE_BOOL, TokenType.TOKEN_TYPE_VOID,
                TokenType.TOKEN_TYPE_STRING, TokenType.TOKEN_CNAME}

    def __str__(self) -> str:
        return f"{self.type.value}"

    def __post_init__(self):
        assert self.type.token_type in Type.valid_types(), f"{self.type.value} is not a valid type"

    def get_name(self) -> str:
        return self.type.value


# -----------------------------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------------------------
class Operator(ASTNode):
    operator: TokenInfo

    def __str__(self) -> str:
        return f"{self.operator.value}"

    def get_name(self) -> str:
        return self.operator.value


@dataclass(frozen=False)
class BinaryOperator(Operator):
    operator: TokenInfo


@dataclass(frozen=False)
class RelativeOperator(BinaryOperator):
    operator: TokenInfo


@dataclass(frozen=False)
class UnaryOperator(Operator):
    operator: TokenInfo


# -----------------------------------------------------------------------------------------------
# Expression
# -----------------------------------------------------------------------------------------------
class Expr(ASTNode):
    annotated_type : str
    def annotate_type(self, type : str):
        self.annotated_type = type

    def get_type(self) -> str:
        return self.annotated_type


@dataclass(frozen=False)
class UnaryOp(Expr):
    operator: UnaryOperator
    repeat: int
    operand: Expr # can only be bool, int or atom

    def __str__(self) -> str:
        pprint = ""
        for i in range(self.repeat):
            pprint += "(" + str(self.operator) + ")"
        pprint += str(self.operand)
        return pprint


@dataclass(frozen=False)
class BinaryOp(Expr):
    left_operand: Expr
    operator: BinaryOperator
    right_operand: Expr

    def __str__(self) -> str:
        return f"({self.left_operand} {self.operator} {self.right_operand})"


# -----------------------------------------------------------------------------------------------
# Atoms
# -----------------------------------------------------------------------------------------------
class Atom(Expr):
    pass


@dataclass(frozen=False)
class Identifier(Atom):
    identifier: TokenInfo

    def __str__(self) -> str:
        return f"{self.identifier.value}"

    def get_name(self) -> str:
        return self.identifier.value


class This(Atom):
    def __str__(self) -> str:
        return "this"


class Null(Atom):
    def __str__(self) -> str:
        return "null"


@dataclass(frozen=False)
class NewClass(Atom):
    class_name: TokenInfo

    def __post_init__(self):
        assert self.class_name.token_type == TokenType.TOKEN_CNAME

    def __str__(self) -> str:
        return f"new {self.class_name.value}()"

    def get_name(self) -> str:
        return self.class_name.value


@dataclass(frozen=False)  # Field access
class AtomAccess(Atom):
    lhs: Atom
    rhs: Identifier

    def __str__(self) -> str:
        return f"({self.lhs}.{self.rhs})"

    def get_obj_name(self) -> str:
        return str(self.lhs)

    def get_attr_name(self) -> str:
        return str(self.rhs)


@dataclass(frozen=False)  # Expression interpreted as Atom
class AtomExpr(Atom):
    expr: Expr

    def __str__(self) -> str:
        return f"({self.expr})"


@dataclass(frozen=False)  # Function call in an expression
class AtomCall(Atom):
    call: Atom
    args: List[Expr]

    def __str__(self) -> str:
        return f"{self.call}(" + ", ".join(map(str, self.args)) + ")"

    def annotate_callInfo(self, methodInfo : MethodInfo):
        self.methodInfo = methodInfo

    def get_callInfo(self) -> MethodInfo:
        return self.methodInfo



# -----------------------------------------------------------------------------------------------
# Literal
# -----------------------------------------------------------------------------------------------
@dataclass(frozen=False)
class Literal(Expr):
    literal: TokenInfo

    def __str__(self) -> str:
        return f"{self.literal.value}"

    def get_name(self) -> str:
        return self.literal.value


@dataclass(frozen=False)
class String(Literal):
    literal: TokenInfo

    def get_type(self) -> str:
        return "String"


@dataclass(frozen=False)
class Boolean(Literal):
    literal: TokenInfo

    def get_type(self) -> str:
        return "Bool"


@dataclass(frozen=False)
class Integer(Literal):
    literal: TokenInfo

    def get_type(self) -> str:
        return "Int"


# -----------------------------------------------------------------------------------------------
# Statements
# -----------------------------------------------------------------------------------------------
class Statement(ASTNode):
    pass


# Declarations
@dataclass(frozen=False)
class VarDecl(ASTNode):
    type: Type
    identifier: Identifier

    def __str__(self) -> str:
        return f"{self.type} {self.identifier};"

    def get_type(self) -> str:
        return self.type.get_name()

    def get_name(self) -> str:
        return self.identifier.get_name()


@dataclass(frozen=False)
class Block(ASTNode):
    vars: List[VarDecl]
    stmts: List[Statement]

    def __str__(self) -> str:
        return "{\n" + "\n".join(map(str, self.vars)) + "\n".join(map(str, self.stmts)) + "\n"


@dataclass(frozen=False)
class IfThenElse(Statement):
    cond: Expr
    true_branch: Block
    false_branch: Block

    def __str__(self) -> str:
        return f"if ({self.cond}) {self.true_branch} {self.false_branch}"


@dataclass(frozen=False)
class While(Statement):
    cond: Expr
    body: Block

    def __str__(self) -> str:
        return f"while ({self.cond}) {self.body}"


@dataclass(frozen=False)
class Return(Statement):
    ret_expr: Optional[Expr]

    def __str__(self) -> str:
        if self.ret_expr is None:
            return "return;"
        else:
            return f"return {self.ret_expr};"


@dataclass(frozen=False)
class Readln(Statement):
    identifier: Identifier

    def __str__(self) -> str:
        return f"readln({self.identifier});"


@dataclass(frozen=False)
class Println(Statement):
    expr: Expr

    def __str__(self) -> str:
        return f"println({self.expr});"


@dataclass(frozen=False)
class Assignment(Statement):
    lhs: Atom
    rhs: Expr

    def __str__(self) -> str:
        return f"{self.lhs} = {self.rhs};"


@dataclass(frozen=False)
class MethodCall(Statement):
    call: AtomCall

    def __str__(self) -> str:
        return f"{self.call};"


# -----------------------------------------------------------------------------------------------
# Method, Class
# -----------------------------------------------------------------------------------------------
@dataclass(frozen=False)
class Formal(ASTNode):
    type: Type
    identifier: Identifier

    def __str__(self) -> str:
        return f"{self.type} {self.identifier}"

    def get_name(self) -> str:
        return self.identifier.get_name()

    def get_type(self) -> str:
        return self.type.get_name()


@dataclass(frozen=False)
class Method(ASTNode):
    ret_type: Type
    name: Identifier
    formals: List[Formal]
    body: Block

    def __str__(self) -> str:
        return f"{self.ret_type} {self.name}(" + ", ".join(map(str, self.formals)) + f") {self.body}"


# class
@dataclass(frozen=False)
class Class(ASTNode):
    class_type: Type
    fields: List[VarDecl]
    methods: List[Method]

    def __str__(self) -> str:
        return f"class {self.class_type}" + "{\n" + \
               "\n".join(map(str, self.fields)) + "\n".join(map(str, self.methods)) \
               + "\n}"

    def get_name(self) -> str:
        return self.class_type.get_name()


@dataclass(frozen=False)
class Program(ASTNode):
    main_class: Class
    classes: List[Class]

    def __str__(self) -> str:
        return f"{self.main_class}" + "\n".join(map(str, self.classes))
