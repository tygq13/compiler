# Ye Guoquan, A0188947A
from dataclasses import dataclass
import ast
from typing import List, Dict
from lex import Lexer
from parse import Parser
from ir3 import IR3
from optimize import Optimizer
import sys
import argparse


class TypeCheckException():
    def __init__(self, msg):
        print(msg)
        exit(1)


class TypeEnv:
    def __init__(self):
        self.classDes : Dict[str, ast.ClassInfo] = {}
        self.localEnv : Dict[str, List[str]] = {}
        self.localMethod : Dict[str, List[ast.MethodInfo]] = {}

    def addClass(self, c: ast.Class):
        classInfo = self.sig_from_class(c)
        self.classDes[classInfo.name] = classInfo

    def addLocal(self, var: str, type: str):
        if var in self.localEnv:
            # overwrite previous declaration
            self.localEnv[var].append(type)
        else:
            self.localEnv[var] = [type]

    def addLocalMethod(self, method: str, infos: List[ast.MethodInfo]):
        for info in infos:
            if method in self.localMethod:
                method_sigs = self.localMethod[method]
                if info in method_sigs:
                    TypeCheckException(f"addLocalMethod(): method name clash in '{method}'")
                else:
                    self.localMethod[method].append(info)
            else:
                self.localMethod[method] = [info]

    def removeLocal(self, var: str):
        self.localEnv[var].pop()
        if len(self.localEnv[var]) == 0:
            del self.localEnv[var]

    def removeLocalMethod(self, method: str):
        self.localMethod[method].pop()
        if len(self.localMethod[method]) == 0:
            del self.localMethod[method]

    def getLocal(self, name: str) -> str:
        if name in self.localEnv:
            return self.localEnv[name][-1]  # return the last entry, treat like a stack
        TypeCheckException(f"getLocal(): var '{name}' unresolved")

    def getClass(self, name: str) -> ast.ClassInfo:
        if name in self.classDes:
            return self.classDes[name]
        TypeCheckException(f"getClass(): class '{name}' unresolved")

    def getLocalMethod(self, method : str) -> ast.MethodInfo:
        if method in self.localMethod:
            return self.localMethod[method]
        TypeCheckException(f"getLocalMethod(): method '{method}' unresolved")

    def distinct(self, names : List[str]):
        seen = []
        for i in names:
            if i in seen:
                TypeCheckException(f"distinct(): name clash in '{i}'")
            seen.append(i)

    def sig_from_class(self, node : ast.Class) -> ast.ClassInfo:
        class_name = node.class_type.get_name()
        field_sigs: Dict[str, str] = {}
        for field in node.fields:
            if field.get_name() in field_sigs:
                TypeCheckException(f"sig_from_class(): in class '{class_name}', fileds name clash for '{field.get_name()}'")
            field_sigs[field.get_name()] = field.get_type()
        method_sigs: Dict[str, List[ast.MethodInfo]] = {}
        for method in node.methods:
            if method.name.get_name() in method_sigs:
                method_sigs[method.name.get_name()].append(self.sig_from_method(method))
            else:
                method_sigs[method.name.get_name()] = [self.sig_from_method(method)]
        return ast.ClassInfo(class_name, field_sigs, method_sigs)


    def sig_from_method(self, node : ast.Method) -> ast.MethodInfo:
        self.distinct([i.get_name() for i in node.formals])
        args = [i.get_type() for i in node.formals]
        return ast.MethodInfo(node.name.get_name(), args, node.ret_type.get_name())


class Checker:
    def check(self, astRoot : ast.ASTNode):
        env = TypeEnv()
        self.astRoot = astRoot
        self.type_check_program(env, self.astRoot)

    def validate(self, type1: str, type2: str, node : ast.ASTNode):
        if type1 != type2 and (type1 != "Null" or type2 in ["Int", "Bool"]):
            TypeCheckException(f"validate(): expect type '{type2}' but obtain '{type1}' near '{node}'")

    def validateOneOf(self, type: str, table: List[str], node : ast.ASTNode):
        if not type in table:
            TypeCheckException(f"validateOneOf(): expect '{table}' but obtain '{type}' near '{node}'")

    def assertion(self, boolean: bool, node : ast.ASTNode):
        if not boolean:
            TypeCheckException(f"assertion(): unexpected error near '{node}'")

    def distinct(self, names : List[str]):
        seen = []
        for i in names:
            if i in seen:
                TypeCheckException(f"distinct(): name clash in '{i}'")
            seen.append(i)

    def type_check_program(self, env: TypeEnv, node: ast.Program) -> bool:
        self.distinct([node.main_class.get_name()] + [i.get_name() for i in node.classes],)
        env.addClass(node.main_class)
        for i in node.classes:
            env.addClass(i)

        isOK = self.type_check_class(env, node.main_class)
        for i in node.classes:
            isOK = isOK and self.type_check_class(env, i)
        return isOK

    def type_check_class(self, env: TypeEnv, node: ast.Class) -> bool:
        classInfo = env.sig_from_class(node)
        env.addLocal("this", classInfo.name)
        for name in classInfo.fields:
            env.addLocal(name, classInfo.fields[name])
        for name in classInfo.methods:
            env.addLocalMethod(name, classInfo.methods[name])

        isOK = True
        for method in node.methods:
            isOK = isOK and self.type_check_method(env, method)

        env.removeLocal("this")
        for name in classInfo.fields:
            env.removeLocal(name)
        for name in classInfo.methods:
            env.removeLocalMethod(name)
        return isOK

    def type_check_method(self, env: TypeEnv, node: ast.Method) -> bool:
        # add envs
        methodInfo = env.sig_from_method(node)
        for formal in node.formals:
            env.addLocal(formal.get_name(), formal.get_type())
        env.addLocal("return", methodInfo.ret_type)
        formals = [i.get_name() for i in node.formals]
        self.distinct(formals)

        # type check
        type = self.type_check_block(env, node.body, formals)

        # clear envs
        for formal in node.formals:
            env.removeLocal(formal.get_name())
        env.removeLocal("return")

        return type == methodInfo.ret_type

    def type_check_block(self, env: TypeEnv, node: ast.Block, formals : List[str] = []) -> str:
        # don't allow declarations in block to have the same name although not in specification
        self.distinct([i.get_name() for i in node.vars] + formals)
        for var in node.vars:
            env.addLocal(var.get_name(), var.get_type())

        for stmts in node.stmts[:-1]:
            self.type_check_statement(env, stmts)

        last_type = self.type_check_statement(env, node.stmts[-1])

        for var in node.vars:
            env.removeLocal(var.get_name())
        return last_type

    def type_check_statement(self, env: TypeEnv, node: ast.Statement) -> str:
        if isinstance(node, ast.IfThenElse):
            return self.type_check_ifThenElse(env, node)
        elif isinstance(node, ast.While):
            return self.type_check_while(env, node)
        elif isinstance(node, ast.Return):
            return self.type_check_return(env, node)
        elif isinstance(node, ast.Assignment):
            return self.type_check_assignment(env, node)
        elif isinstance(node, ast.MethodCall):
            return self.type_check_methodCall(env, node)
        elif isinstance(node, ast.Readln):
            return self.type_check_readln(env, node)
        elif isinstance(node, ast.Println):
            return self.type_check_println(env, node)
        else:
            self.assertion(False, node)

    def type_check_ifThenElse(self, env: TypeEnv, node: ast.IfThenElse) -> str:
        self.validate(self.type_check_expr(env, node.cond), "Bool", node)
        if_type = self.type_check_block(env, node.true_branch)
        else_type = self.type_check_block(env, node.false_branch)
        self.validate(if_type, else_type, node)
        return else_type

    def type_check_while(self, env: TypeEnv, node: ast.While) -> str:
        self.validate(self.type_check_expr(env, node.cond), "Bool", node)
        return self.type_check_block(env, node.body)

    def type_check_return(self, env: TypeEnv, node: ast.Return) -> str:
        if node.ret_expr == None:
            return "Void"
        else:
            self.validate(self.type_check_expr(env, node.ret_expr), env.getLocal("return"), node)
        return env.getLocal("return")

    def type_check_readln(self, env: TypeEnv, node: ast.Readln) -> str:
        self.validateOneOf(env.getLocal(node.identifier.get_name()), ["Int", "Bool", "String"], node)
        return "Void"

    def type_check_println(self, env: TypeEnv, node: ast.Println) -> str:
        self.validateOneOf(self.type_check_expr(env, node.expr), ["Int", "Bool", "String"], node)
        return "Void"

    def type_check_assignment(self, env: TypeEnv, node: ast.Assignment) -> str:
        atom_type = self.type_check_atom(env, node.lhs)
        expr_type = self.type_check_expr(env, node.rhs)
        self.validate(expr_type, atom_type, node)
        return "Void"

    def type_check_methodCall(self, env: TypeEnv, node: ast.MethodCall) -> str:
        return self.type_check_atomCall(env, node.call)

    # only three cases: BinaryOp, UnaryOp (where int, bool atom included), or String
    def type_check_expr(self, env: TypeEnv, node: ast.Expr) -> str:
        if isinstance(node, ast.BinaryOp):
            type = self.type_check_binaryOp(env, node)
        elif isinstance(node, ast.UnaryOp):
            type = self.type_check_unaryOp(env, node)
        elif isinstance(node, ast.String):
            type = "String"
        elif isinstance(node, ast.Atom):
            type = self.type_check_atom(env, node)
        else:
            self.assertion(False, node)
        node.annotate_type(type)
        return type

    def type_check_unaryOp(self, env: TypeEnv, node: ast.UnaryOp) -> str:
        if isinstance(node.operand, ast.Integer):
            type = "Int"
        elif isinstance(node.operand, ast.Boolean):
            type = "Bool"
        else:
            type =  self.type_check_atom(env, node.operand)
        node.annotate_type(type)
        return type    

    def type_check_binaryOp(self, env: TypeEnv, node: ast.BinaryOp) -> str:
        # somehow this is right associative, but doesn't affect calculation, ignore for now
        if isinstance(node.left_operand, ast.BinaryOp):
            lhs = self.type_check_binaryOp(env, node.left_operand)
        elif isinstance(node.left_operand, ast.UnaryOp):
            lhs = self.type_check_unaryOp(env, node.left_operand)
        elif isinstance(node.left_operand, ast.String):
            lhs = "String"
        elif isinstance(node.left_operand, ast.Atom):
            lhs = self.type_check_atom(env, node.left_operand)
        else:
            self.assertion(False, node)

        if isinstance(node.right_operand, ast.BinaryOp):
            rhs = self.type_check_binaryOp(env, node.right_operand)
        elif isinstance(node.right_operand, ast.UnaryOp):
            rhs = self.type_check_unaryOp(env, node.right_operand)
        elif isinstance(node.right_operand, ast.String):
            rhs = "String"
        elif isinstance(node.right_operand, ast.Atom):
            rhs = self.type_check_atom(env, node.right_operand)
        else:
            self.assertion(False, node)

        if isinstance(node.operator, ast.RelativeOperator):
            self.validate(lhs, "Int", node)
            self.validate(rhs, "Int", node)
            type = "Bool"
        else:
            self.validate(lhs, rhs, node)
            type = rhs
        node.annotate_type(type)
        return type

    def type_check_atom(self, env: TypeEnv, node: ast.Atom) -> str:
        if isinstance(node, ast.Identifier):
            type = env.getLocal(node.get_name())
        elif isinstance(node, ast.NewClass):
            type =  node.get_name()
        elif isinstance(node, ast.AtomAccess):
            type =  self.type_check_atomAccess(env, node)
        elif isinstance(node, ast.AtomExpr):
            type =  self.type_check_expr(env, node.expr)
        elif isinstance(node, ast.AtomCall):
            type =  self.type_check_atomCall(env, node)
        elif isinstance(node, ast.This):
            type =  env.getLocal("this")
        elif isinstance(node, ast.Null):
            type =  "Null"
        else:
            self.assertion(False, node)
        node.annotate_type(type)
        return type

    def type_check_atomAccess(self, env: TypeEnv, node: ast.AtomAccess) -> str:
        classname = self.type_check_atom(env, node.lhs)
        classInfo = env.getClass(classname)
        if node.rhs.get_name() in classInfo.fields:
            type = classInfo.fields[node.rhs.get_name()]
        else:
            self.assertion(False, node)
        node.annotate_type(type)
        return type

    def type_check_atomCall(self, env: TypeEnv, node: ast.AtomCall) -> str:
        if isinstance(node.call, ast.Identifier) or isinstance(node.call, ast.This):
            # local call
            methodInfos = env.getLocalMethod(str(node.call))
        else:
            # global call
            classname = self.type_check_atom(env, node.call.lhs)
            classInfo = env.getClass(classname)
            if not node.call.rhs.get_name() in classInfo.methods:
                TypeCheckException(f"Unable to find method '{node.call.rhs.get_name()}' in class '{classInfo.name}' near '{node}'")
            methodInfos = classInfo.methods[node.call.rhs.get_name()]


        match = 0
        ret_type : str
        match_info : ast.MethodInfo
        for methodInfo in methodInfos:
            valid = True
            if len(node.args) != len(methodInfo.args):
                valid = False
                continue
            for arg in range(len(node.args)):
                type = self.type_check_expr(env, node.args[arg])
                if type != methodInfo.args[arg]:
                    valid = False
            if valid == True:
                match += 1
                match_info = methodInfo
                ret_type = methodInfo.ret_type

        if match > 1:
            TypeCheckException(f"type_check_atomCall(): unable to resolve ambiguous function signature for {node}")
        if match == 0:
            TypeCheckException(f"type_check_atomCall(): unable to find function signature for {node}")
        node.annotate_type(ret_type)
        node.call.annotate_type(ret_type)
        node.annotate_callInfo(match_info)
        return ret_type


if __name__ == '__main__':
    source_file = sys.argv[1]
    with open(source_file) as f:
        source_code = f.read()
    lexer = Lexer(source_code)
    parser = Parser(lexer)
    astree = parser.parse()
    checker = Checker().check(astree)
    argparser = argparse.ArgumentParser()
    argparser.add_argument('input', help='input file')
    argparser.add_argument('-O', '--optimize', help='optimize program', action='store_true')
    args = argparser.parse_args()
    ir3 = IR3(astree).generateIR3()
    if args.optimize:
        ir3 = Optimizer(ir3).optimize()
    print(ir3)