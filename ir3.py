# Ye Guoquan, A0188947A
import ast
from typing import List, Tuple


class IR3Exception(Exception):
    pass

# -----------------------------------------------------------------------------------------------
# IR3 AST
# -----------------------------------------------------------------------------------------------

class IR3ASTNode():
    pass

class CData3(IR3ASTNode):

    def __init__(self, class_name, varDecls):
        self.class_name : str = class_name
        self.varDecls : List[VarDecl3] = varDecls

    def addVarDecl(self, type, id):
        self.varDecls.append(VarDecl3(type, id))

    def __str__(self):
        string = f'class {self.class_name} {{ \n'
        string += ''.join([f'    {var};\n' for var in self.varDecls])
        string += '}'
        return string

class CMethod3(IR3ASTNode):
    def __init__(self, type, id, formals, body):
        self.type :str = type
        self.id :str = id
        self.formals : List[Formal3] = formals
        self.body : Block3 = body

    def __str__(self):
        # print formals
        formalListStr = ""
        for i in range(len(self.formals)):
            formalListStr += f'{self.formals[i]}'
            if i < len(self.formals) - 1:
                formalListStr += ","

        string = f'{self.type} {self.id} ({formalListStr}) {{ \n{self.body}}}'
        return string

class Program3(IR3ASTNode):
    def __init__(self, cData3List: List[CData3], cMethod3List: List[CMethod3], stringList : List[str]):
        self.cData3List = cData3List
        self.cMethod3List = cMethod3List
        self.stringList = stringList
    
    def __str__(self):
        string = "======= CData3 =======\n\n"
        for cData in self.cData3List:
            string += f'{cData}\n\n'
        string += "=======  CMtd3 =======\n\n"
        for cMethod in self.cMethod3List:
            string += f'{cMethod}\n\n'
        return string

class VarDecl3(IR3ASTNode):
    def __init__(self, type, id):
        self.type :str = type
        self.id : str = id
    
    def __str__(self):
        return f'{self.type} {self.id}'


class Formal3(IR3ASTNode):
    # TODO: merge with vardecl
    def __init__(self, type, id):
        self.type :str = type
        self.id : str = id
    
    def __str__(self):
        return f'{self.type} {self.id}'

class Block3(IR3ASTNode):
    def __init__(self, varDecls, stmts):
        self.varDecls : List[VarDecl3] = varDecls
        self.stmts : List[Stmt3] = stmts

    def __str__(self):
        string = ""
        for var in self.varDecls:
            string += f'    {var};\n'
        for statement in self.stmts:
            string += f'{statement}\n'
        return string

    def get_statements(self):
        return self.stmts



class Stmt3(IR3ASTNode):
    pass

class Label3(Stmt3):
    def __init__(self, label : str):
        self.label : str = label

    def __str__(self):
        string = f'  Label {self.label}:'
        return string

class Goto3(Stmt3):
    def __init__(self, label : str):
        self.label : str = label

    def __str__(self):
        string = f'    goto {self.label}:'
        return string

class IfGoto3(Stmt3):
    def __init__(self, cond : str, label : str):
        self.cond : str = cond
        self.label : str = label

    def __str__(self):
        string = f'    if ( {self.cond} ) goto {self.label};'
        return string

class Readln3(Stmt3):
    def __init__(self, id:str):
        self.id : str = id

    def __str__(self):
        string = f'    readln({self.id});'
        return string

class Println3(Stmt3):
    def __init__(self, id:str):
        self.id :str = id

    def __str__(self):
        string = f'    println({self.id});'
        return string


class Return3(Stmt3):
    def __init__(self, id:str):
        self.id : str = id

    def __str__(self):
        if self.id == None:
            string = f'    return ;'
        else:
            string = f'    return {self.id};'
        return string


class TypeAssign3(Stmt3):
    def __init__(self, type:str, id:str, value: str):
        self.type = type
        self.id = id
        self.value = value

    def __str__(self):
        string = f'    {self.type} {self.id} = {self.value};'
        return string

class TypeAssignAtomAccess3(TypeAssign3):
    def __init__(self, type:str, id:str, obj: str, field: str):
        self.type = type
        self.id = id
        self.obj = obj
        self.field = field

    def __str__(self):
        string = f'    {self.type} {self.id} = {self.obj}.{self.field};'
        return string

class TypeAssignNew3(TypeAssign3):
    def __init__(self, type:str, id:str, cname: str):
        self.type = type
        self.id = id
        self.cname = cname

    def __str__(self):
        string = f'    {self.type} {self.id} = new {self.cname}();'
        return string

class TypeAssignCall3(TypeAssign3):
    def __init__(self, type:str, id:str, call: str, args: List[str]):
        self.type = type
        self.id = id
        self.call = call
        self.args = args

    def __str__(self):
        args = ",".join(self.args)
        string = f'    {self.type} {self.id} = {self.call}({args});'
        return string

class Assign3(Stmt3):
    def __init__(self, id:str, result: str):
        self.id = id
        self.result = result

    def __str__(self):
        string = f'    {self.id} = {self.result};'
        return string
        

class BinaryOp3(Stmt3):
    def __init__(self, type:str, target:str, lhs: str, op : str, rhs : str):
        self.type = type
        self.target = target
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    def __str__(self):
        string = f'    {self.type} {self.target} = {self.lhs} {self.op} {self.rhs};'
        return string

class UnaryOp3(Stmt3):
    def __init__(self, target:str, op : str, operand : str):
        self.target = target
        self.op = op
        self.operand = operand

    def __str__(self):
        string = f'    {self.target} = {self.op} {self.operand};'
        return string


# -----------------------------------------------------------------------------------------------
# IR3 generator
# -----------------------------------------------------------------------------------------------

class IR3:
    def __init__(self, ast : ast.Program):
        self.label = 0
        self.tmp = 0
        self.ast = ast
        self.stringList = []

    def newLabel(self) -> str:
        result = "L" + str(self.label)
        self.label += 1
        return result

    def newTmp(self) -> str:
        result = "_v" + str(self.tmp)
        self.tmp += 1
        return result

    def generateIR3(self) -> IR3ASTNode:
        self.label = 0
        self.tmp = 0
        return self.genProgram3(self.ast)

    def genProgram3(self, astNode : ast.Program) -> Program3:
        cData3List : List[CData3] = []
        cMethod3List : List[CMethod3] = []
        cData3List.append(self.genCData3(astNode.main_class))
        cMethod3List += self.genCMethod3(astNode.main_class)
        for i in astNode.classes:
            cData3List.append(self.genCData3(i))
            cMethod3List += self.genCMethod3(i)
        return Program3(cData3List, cMethod3List, self.stringList)

    def genCData3(self, astNode : ast.Class) -> CData3:
        varDecl3List : List[VarDecl3] = []
        for i in astNode.fields:
            varDecl3List.append(self.genVarDecl3(i))
        return CData3(astNode.class_type.get_name(), varDecl3List)

    def genVarDecl3(self, astNode : ast.VarDecl) -> VarDecl3:
        return VarDecl3(astNode.get_type(), astNode.get_name())

    def genCMethod3(self, astNode : ast.Class) -> List[CMethod3]:
        class_name = astNode.class_type.get_name()
        cMethod3List : List[CMethod3] = []
        for method in astNode.methods:
            type_name = method.ret_type.get_name()
            method_name = class_name + "_" + method.name.get_name() + "_" + "_".join(i.get_type() for i in method.formals)
            formals3 : List[Formal3] = [Formal3(class_name, "this")]
            for i in method.formals:
                formals3.append(self.genFormal3(i))
            body = self.genBlock3(method.body)
            cMethod3List.append(CMethod3(type_name, method_name, formals3, body))
        return cMethod3List

    def genFormal3(self, astNode : ast.Formal) -> Formal3:
        return Formal3(astNode.get_type(), astNode.get_name())

    def genBlock3(self, astNode : ast.Block) -> Block3:
        varDecl3List : List[VarDecl3] = []
        for i in astNode.vars:
            varDecl3List.append(self.genVarDecl3(i))
        stmt3List : List[Stmt3] = []
        for i in astNode.stmts:
            stmt3List += self.genStmt3(i)
        return Block3(varDecl3List, stmt3List)

    def genStmt3(self, astNode : ast.Statement) -> List[Stmt3]:
        if isinstance(astNode, ast.IfThenElse):
            return self.genIfThenElse3(astNode)
        elif isinstance(astNode, ast.While):
            return self.genWhile3(astNode)
        elif isinstance(astNode, ast.Readln):
            return self.genReadln3(astNode)
        elif isinstance(astNode, ast.Println):
            return self.genPrintln3(astNode)
        elif isinstance(astNode, ast.Return):
            return self.genReturn3(astNode)
        elif isinstance(astNode, ast.Assignment):
            return self.genAssignment3(astNode)
        elif isinstance(astNode, ast.MethodCall):
            return self.genMethodCall3(astNode)

    def genIfThenElse3(self, astNode : ast.IfThenElse) -> List[Stmt3]:
        statements : List[Stmt3] = []
        B_true = self.newLabel()
        B_false = self.newLabel()
        S_next = self.newLabel()

        statements += self.genBranchExpr3(astNode.cond, B_true, B_false)
        statements.append(Label3(B_true))
        statements += self.genBlock3(astNode.true_branch).get_statements()
        statements.append(Goto3(S_next))
        statements.append(Label3(B_false))
        statements += self.genBlock3(astNode.false_branch).get_statements()
        statements.append(Label3(S_next))
        return statements

    def genWhile3(self, astNode : ast.While) -> List[Stmt3]:
        statements : List[Stmt3] = []
        B_true = self.newLabel()
        S_begin = self.newLabel()
        S_next = self.newLabel()

        statements.append(Label3(S_begin))
        statements += self.genBranchExpr3(astNode.cond, B_true, S_next)
        statements.append(Label3(B_true))
        statements += self.genBlock3(astNode.body).get_statements()
        statements.append(Goto3(S_begin))
        statements.append(Label3(S_next))
        return statements

    def genReadln3(self, astNode : ast.Readln) -> List[Stmt3]:
        statements : List[Stmt3] = []
        statements.append(Readln3(astNode.identifier.get_name()))
        return statements

    def genPrintln3(self, astNode : ast.Println) -> List[Stmt3]:
        statements : List[Stmt3] = []
        v = self.newTmp()
        (expr_stmts, result) = self.genExpr3(astNode.expr)
        statements += expr_stmts
        statements.append(TypeAssign3(astNode.expr.get_type(), v, result))
        statements.append(Println3(v))
        return statements

    def genReturn3(self, astNode : ast.Return) -> List[Stmt3]:
        statements : List[Stmt3] = []
        if astNode.ret_expr == None:
            statements.append(Return3(None))
            return statements
        else:
            v = self.newTmp()
            (expr_stmts, result) = self.genExpr3(astNode.ret_expr)
            statements += expr_stmts
            statements.append(TypeAssign3(astNode.ret_expr.get_type(), v, result))
            statements.append(Return3(v))
        return statements

    def genAssignment3(self, astNode : ast.Assignment) -> List[Stmt3]:
        statements : List[Stmt3] = []
        (expr_stmts, result) = self.genExpr3(astNode.rhs)
        statements += expr_stmts
        if isinstance(astNode.lhs, ast.AtomAccess):
            (atom_stmts, atom_result) = self.genAtomAcess3(astNode.lhs, newVar=False)
        else:
            (atom_stmts, atom_result) = self.genAtom3(astNode.lhs)
        statements += atom_stmts
        statements.append(Assign3(atom_result, result))
        return statements

    def genMethodCall3(self, astNode : ast.MethodCall) -> List[Stmt3]:
        (statements, result) = self.genAtomCall3(astNode.call)
        return statements

    def genAtomCall3(self, astNode : ast.AtomCall) -> Tuple[List[Stmt3], str]:
        statements : List[Stmt3] = []

        if isinstance(astNode.call, ast.Identifier):
            # local call
            #class_name = astNode.call.get_name()
            class_name = "this"
            obj_name = "this"
        else:
            # global call
            class_name = astNode.call.lhs.get_type()
            if isinstance(astNode.call.lhs, ast.Identifier):
                obj_name = astNode.call.lhs.get_name()
            else:            
                (atom_stmts, atom_result) = self.genAtom3(astNode.call.lhs)
                statements += atom_stmts
                obj_name = atom_result

        args : List[str] = [obj_name]
        for i in astNode.args:
            (expr_stmts, result) = self.genExpr3(i)
            statements += expr_stmts
            args.append(result)

        v = self.newTmp()
        methodInfo : ast.MethodInfo = astNode.get_callInfo()
        mangling = class_name + "_" + methodInfo.name + "_" + "_".join([i for i in methodInfo.args])
        statements.append(TypeAssignCall3(methodInfo.ret_type, v, mangling, args))
        return (statements, v)

    def genBranchExpr3(self, astNode : ast.Expr, B_true : str, B_false : str) -> List[Stmt3]:
        (statements, result) = self.genExpr3(astNode)
        statements.append(IfGoto3(result, B_true))
        statements.append(Goto3(B_false))
        return statements

    def genExpr3(self, astNode : ast.Expr) -> Tuple[List[Stmt3], str]:
        if isinstance(astNode, ast.BinaryOp):
            return self.genBinaryOp3(astNode)
        elif isinstance(astNode, ast.UnaryOp):
            return self.genUnaryOp3(astNode)
        elif isinstance(astNode, ast.String):
            return self.genIDC3(astNode)
        elif isinstance(astNode, ast.Atom):
            print(astNode)
            return self.genAtom3(astNode)
        else:
            raise IR3Exception(f"genExpr3() error, unexpected {astNode}")

    def genBinaryOp3(self, astNode : ast.BinaryOp) -> Tuple[List[Stmt3], str]:
        statements : List[Stmt3] = []
        if isinstance(astNode.left_operand, ast.BinaryOp):
            (lhs_stmts, lhs_result) = self.genBinaryOp3(astNode.left_operand)
        elif isinstance(astNode.left_operand, ast.UnaryOp):
            (lhs_stmts, lhs_result) = self.genUnaryOp3(astNode.left_operand)
        elif isinstance(astNode.left_operand, ast.String):
            (lhs_stmts, lhs_result) = self.genIDC3(astNode.left_operand)
        elif isinstance(astNode.left_operand, ast.Atom):
            (lhs_stmts, lhs_result) = self.genAtom3(astNode.left_operand)
        else:
            raise IR3Exception(f"genBranchBinaryOp3() error, unexpected {astNode}")

        if isinstance(astNode.right_operand, ast.BinaryOp):
            (rhs_stmts, rhs_result) = self.genBinaryOp3(astNode.right_operand)
        elif isinstance(astNode.right_operand, ast.UnaryOp):
            (rhs_stmts, rhs_result) = self.genUnaryOp3(astNode.right_operand)
        elif isinstance(astNode.right_operand, ast.String):
            (rhs_stmts, rhs_result) = self.genIDC3(astNode.right_operand)
        elif isinstance(astNode.right_operand, ast.Atom):
            (rhs_stmts, rhs_result) = self.genAtom3(astNode.right_operand)
        else:
            raise IR3Exception(f"genBranchBinaryOp3() error, unexpected {astNode}")

        statements += rhs_stmts
        statements += lhs_stmts
        v = self.newTmp()
        type = astNode.get_type()
        statements.append(BinaryOp3(type, v, lhs_result, astNode.operator.get_name(), rhs_result))
        return (statements, v)

    def genUnaryOp3(self, astNode : ast.UnaryOp) -> Tuple[List[Stmt3], str]:
        statements : List[Stmt3] = []
        if isinstance(astNode.operand, ast.Boolean) or isinstance(astNode.operand, ast.Integer):
            (stmts, result) = self.genIDC3(astNode.operand)
        elif isinstance(astNode.operand, ast.Atom):
            (stmts, result) = self.genAtom3(astNode.operand)
        else:
            raise IR3Exception(f"genUnaryOp3() error, unexpected {astNode.operand}")

        statements += stmts

        v = self.newTmp()
        type = astNode.operand.get_type()
        statements.append(TypeAssign3(type, v, result))

        for i in range(astNode.repeat):
            statements.append(UnaryOp3(v, astNode.operator.get_name(), v))
        return (statements, v)


    def genAtom3(self, astNode : ast.Atom) -> Tuple[List[Stmt3], str]:
        if isinstance(astNode, ast.AtomCall):
            #print(astNode)
            #print("atomcall")
            return self.genAtomCall3(astNode)
        elif isinstance(astNode, ast.Null) or isinstance(astNode, ast.This) or isinstance(astNode, ast.Identifier):
            #print(astNode)
            #print("null/this/id")
            return self.genIDC3(astNode)
        elif isinstance(astNode, ast.NewClass):
            #print(astNode)
            #print("new")
            return self.genAtomNew(astNode)
        elif isinstance(astNode, ast.AtomExpr):
            #print(astNode)
            #print("atom expr")
            return self.genExpr3(astNode.expr)
        elif isinstance(astNode, ast.AtomAccess):
            #print(astNode)
            #print("access")
            return self.genAtomAcess3(astNode)
        else:
            raise IR3Exception(f"genAtom3() error, unexpected {astNode}")

    def genIDC3(self, astNode : ast.ASTNode) -> Tuple[List[Stmt3], str]:
        if isinstance(astNode, ast.String):
            self.stringList.append(str(astNode))
        return ([], str(astNode))

    def genAtomNew(self, astNode : ast.NewClass) -> Tuple[List[Stmt3], str]:
        statements : List[Stmt3] = []
        type = astNode.get_type()
        v = self.newTmp()
        statements.append(TypeAssignNew3(type, v, astNode.get_name()))
        return (statements, v)

    def genAtomAcess3(self, astNode : ast.AtomAccess, newVar = True) -> Tuple[List[Stmt3], str]:
        statements : List[Stmt3] = []
        if isinstance(astNode.lhs, ast.Identifier):
            obj_name = astNode.get_obj_name()
        else:
            (stmts, result) = self.genAtom3(astNode.lhs)
            statements += stmts
            obj_name = result

        if newVar:
            type = astNode.get_type()
            v = self.newTmp()
            statements.append(TypeAssignAtomAccess3(type, v, obj_name, astNode.get_attr_name()))
            return (statements, v)
        else:
            return (statements, obj_name + "." + astNode.get_attr_name())
        

