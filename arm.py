# Ye Guoquan, A0188947A
from typing import Dict, Tuple
from lex import Lexer
from parse import Parser
from gen import Checker
from reg import RegisterAllocator
import sys
from ir3 import *

class ArmGenException(Exception):
    pass

class ClassStackInfo:
    def __init__(self, cname : str):
        self.cname = cname
        self.fields = {}
        self.offset = 0

    def addField(self, field : VarDecl3):
        self.fields[field.id] = (field.type, self.offset)
        # all Int, String, Bool, ptr are of size 4
        self.offset += 4 

    def getSize(self):
        return self.offset

    def getOffset(self, field : str):
        return self.fields[field][1]


class Assembly:
    def __init__(self):
        self.assembly = []

    def append(self, line : str):
        self.assembly.append(line)

    def ldr(self, target : str, var : str, varTable : Dict[str, Tuple[str, int]], regMap : Dict[str,str]):
        if regMap[var] != "spill":
            self.assembly.append(f"   mov   {target}, {regMap[var]}")
        else:
            self.assembly.append(f"   ldr   {target}, [fp,#-{varTable[var][1]}]")

    def str(self, target : str, var : str, varTable : Dict[str, Tuple[str, int]], regMap : Dict[str,str]):
        if regMap[var] != "spill":
            self.assembly.append(f"   mov   {regMap[var]}, {target}")
        else:
            self.assembly.append(f"   str   {target}, [fp,#-{varTable[var][1]}]")

    def strGlobal(self, target : str, var : str, varTable : Dict[str, Tuple[str, int]], regMap : Dict[str,str], classTable : Dict[str, ClassStackInfo]):
        cname = varTable["this"][0]
        assert var in classTable[cname].fields
        self.ldr("ip", "this", varTable, regMap) # assume ip is always safe to be used as scratch
        self.assembly.append(f"   str   {target}, [ip,#-{classTable[cname].getOffset(var)}]")

    def ldrGlobal(self, target : str, var : str, varTable : Dict[str, Tuple[str, int]], regMap : Dict[str,str], classTable : Dict[str, ClassStackInfo]):
        cname = varTable["this"][0]
        assert var in classTable[cname].fields
        self.ldr("ip", "this", varTable, regMap) # assume ip is always safe to be used as scratch
        self.assembly.append(f"   ldr   {target}, [ip,#-{classTable[cname].getOffset(var)}]")

    def print(self):
        file = open("program.s", "w")
        for line in self.assembly:
            print(line)
            file.write(line + "\n")


class ArmGen:
    def __init__(self, program: Program3):
        self.program = program
        self.stringList = program.stringList
        self.dataTable = {}
        self.classTable = {}
        self.assembly = Assembly()

    def defaultType(self, type: str):
        if type == "String" or type == "Int" or type == "Void" or type == "Bool":
            return True
        return False

    def genArm(self):
        self.buildDataTable()
        self.buildClassTable()
        self.genMeta()
        for method in self.program.cMethod3List:
            self.genMethod(method)

        return self.assembly

    def buildDataTable(self):
        self.dataTable["\"%d\\n\""] = "LC0" # print interger
        self.dataTable["\"%s\\n\""] = "LC1" # print string
        self.dataTable["\"%d\""] = "LC2" # read integer
        self.dataTable["\"\\0\\0\\0\\0\""] = "LC3" # read buffer
        for i in range(len(self.stringList)):
           self.dataTable[self.stringList[i]] = "LC" + str(i+4)

    def buildClassTable(self):
        for cData in self.program.cData3List:
            self.classTable[cData.class_name] = ClassStackInfo(cData.class_name)
            for field in cData.varDecls:
                self.classTable[cData.class_name].addField(field)

    def genMeta(self):
        self.assembly.append("   .data")
        for i in self.dataTable:
            self.assembly.append(self.dataTable[i] + ":")
            self.assembly.append("   .asciz    " + i)
        self.assembly.append("")
        self.assembly.append("   .text")
        self.assembly.append("   .global   main")
        self.assembly.append("   .type   main, %function")
        self.assembly.append("")
        self.assembly.append("main:")


    # naive implmentation, all args and vars are stored in stack
    def genMethod(self, method : CMethod3):
        regMap = RegisterAllocator(method).regMap

        self.assembly.append(method.id + ":")
        self.assembly.append("   stmfd   sp!,{fp,lr,v1,v2,v3,v4,v5}") # prolog
        varTable = self.buildLocalTable(method)
        
        self.assembly.append("   mov   fp, sp") # mov ebp, esp
        self.assembly.append(f"   sub   sp, sp, #{len(varTable)*4}") # TODO: might exceed 255, don't care for now

        for i,arg in enumerate(method.formals): 
            if i >= 4:
                self.assembly.append(f"   ldr   a1, [fp,#{(i-3)*4+28}]") # minus the 6 saved register
                #self.assembly.append(f"   str   a1, [fp,#-{i*4}]")
                self.assembly.str(f"a1", arg.id, varTable, regMap)
            else:
                # arguments are immediately saved so that a1-4 can be used as scratch registers
                self.assembly.str(f"a{i+1}", arg.id, varTable, regMap)
        
        exitTag = f"{method.id}" + "_exit"
        self.genBlock(varTable, method.body, regMap, exitTag)

        self.assembly.append(exitTag + ":")
        self.assembly.append("   mov   sp, fp")
        self.assembly.append("   ldmfd   sp!,{fp,pc,v1,v2,v3,v4,v5}")


    # add all arguments and variables into local table
    def buildLocalTable(self, method : CMethod3) -> Dict[str, Tuple[str, int]] :
        varTable = {}
        offset = 0
        
        for arg in method.formals:
            varTable[arg.id] = (arg.type, offset)
            offset += 4
        
        block = method.body
        # I forgot whether argname = varname is allowed, just assume not allowed
        for var in block.varDecls:
            varTable[var.id] = (var.type, offset)
            offset += 4
        for stmt in block.stmts:
            if isinstance(stmt, TypeAssign3):
                varTable[stmt.id] = (stmt.type, offset)
                offset += 4 
            elif isinstance(stmt, BinaryOp3):
                varTable[stmt.target] = (stmt.type, offset)
                offset += 4
        return varTable

    def genBlock(self, varTable : Dict[str, Tuple[str, int]], block : Block3, regMap : Dict[str, str], exitTag : str):
        for stmt in block.stmts:
            if isinstance(stmt, Label3):
                self.assembly.append(f".{stmt.label}:")
            elif isinstance(stmt, Goto3):
                self.assembly.append(f"   b   .{stmt.label}")
            elif isinstance(stmt, IfGoto3):
                self.genIfGoto(varTable, stmt, regMap)
            elif isinstance(stmt, TypeAssignCall3):
                self.genTypeAssignCall(varTable, stmt, regMap)
            elif isinstance(stmt, TypeAssignNew3):
                self.genTypeAssignNew(varTable, stmt, regMap)
            elif isinstance(stmt, TypeAssignAtomAccess3):
                self.genTypeAssignAtomAccess(varTable, stmt, regMap)
            elif isinstance(stmt, TypeAssign3):
                self.genTypeAssign(varTable, stmt, regMap)
            elif isinstance(stmt, Assign3):
                self.genAssign(varTable, stmt, regMap)
            elif isinstance(stmt, BinaryOp3):
                self.genBinaryOp(varTable, stmt, regMap)
            elif isinstance(stmt, UnaryOp3):
                self.genUnaryOp(varTable, stmt, regMap)
            elif isinstance(stmt, Return3):
                self.genReturn(varTable, stmt, regMap, exitTag)
            elif isinstance(stmt, Println3):
                self.genPrintln(varTable, stmt, regMap)
            elif isinstance(stmt, Readln3):
                self.genReadln(varTable, stmt, regMap)
            else:
                raise ArmGenException(f"{stmt} Not supported")

    def genReturn(self, varTable : Dict[str, Tuple[str, int]], stmt : Println3, regMap : Dict[str, str], exitTag : str):
        if stmt.id:
            if stmt.id.isdigit():
                self.assembly.append(f"   mov   a1, #{stmt.id}")
            elif stmt.id in self.dataTable:
                self.assembly.append(f"   ldr   a1, ={self.dataTable[stmt.id]} + 0")
            elif stmt.id == "true":
                self.assembly.append(f"   mov   a1, #1")
            elif stmt.id == "false":
                self.assembly.append(f"   mov   a1, #0")
            elif stmt.id in varTable:
                self.assembly.ldr("a1", stmt.id, varTable, regMap)
            else:
                self.assembly.ldrGlobal("a1", stmt.id, varTable, regMap, self.classTable)
        self.assembly.append(f"   b   {exitTag}")

    def genPrintln(self, varTable : Dict[str, Tuple[str, int]], stmt : Println3, regMap : Dict[str, str]):
        self.assembly.append("   stmfd   sp!,{v6, v7}")
        if stmt.id in self.dataTable: # must be string
            self.assembly.append(f"   ldr   a2, ={self.dataTable[stmt.id]} + 0")
            self.assembly.append(f"   ldr   a1, =LC1 + 0")
        elif stmt.id.isdigit():
            self.assembly.append(f"   mov   a2, #{stmt.id}")
            self.assembly.append(f"   ldr   a1, =LC0 + 0")
        elif stmt.id in varTable:
            (type, offset) = varTable[stmt.id]
            self.assembly.ldr("a2", stmt.id, varTable, regMap)
            if type == "Int" or type == "Bool":
                self.assembly.append(f"   ldr   a1, =LC0 + 0")
            elif type == "String":
                self.assembly.append(f"   ldr   a1, =LC1 + 0")
            else:
                raise ArmGenException("print only support Int and String")
        else:
            raise ArmGenException(f"\"{stmt}\" Not supported")
        self.assembly.append("   bl   printf")
        self.assembly.append("   ldmfd   sp!,{v6, v7}")

    def genReadln(self, varTable : Dict[str, Tuple[str, int]], stmt : Readln3, regMap : Dict[str, str]):
        self.assembly.append("   stmfd   sp!,{v6, v7}")
        if stmt.id in varTable:
            (type, offset) = varTable[stmt.id]
            if type == "Int":
                self.assembly.append(f"   ldr   a2, =LC3 + 0")
                self.assembly.append(f"   ldr   a1, =LC2 + 0")
            else:
                raise ArmGenException("read only support Int")
        else:
            raise ArmGenException("Not supported")
        self.assembly.append("   bl   scanf")
        self.assembly.append("   ldmfd   sp!,{v6, v7}")
        self.assembly.append(f"   ldr   a1, =LC3 + 0")
        self.assembly.append(f"   ldr   a1, [a1]")
        self.assembly.str("a1", stmt.id, varTable, regMap)

    def genIfGoto(self, varTable : Dict[str, Tuple[str, int]], stmt : IfGoto3, regMap : Dict[str, str]):
        if stmt.cond in varTable:
            assert varTable[stmt.cond][0] == "Bool"
            self.assembly.ldr("a1", stmt.cond, varTable, regMap)
        else:
            self.assembly.ldrGlobal("a1", stmt.cond, varTable, regMap, self.classTable)
        self.assembly.append(f"   cmp   a1, #0")
        self.assembly.append(f"   bgt   .{stmt.label}")


    def genTypeAssign(self, varTable : Dict[str, Tuple[str, int]], stmt : TypeAssign3, regMap : Dict[str, str]):
        if stmt.value in self.dataTable:
            self.assembly.append(f"   ldr   a1, ={self.dataTable[stmt.value]} + 0")
        elif stmt.value.isdigit():
            self.assembly.append(f"   mov   a1, #{stmt.value}")
        elif stmt.value == "true":
            self.assembly.append(f"   mov   a1, #1")
        elif stmt.value == "false":
            self.assembly.append(f"   mov   a1, #0")
        elif (stmt.value in varTable): # local variable
            self.assembly.ldr("a1", stmt.value, varTable, regMap)
        else:
            self.assembly.ldrGlobal("a1", stmt.value, varTable, regMap, self.classTable)

        self.assembly.str("a1", stmt.id, varTable, regMap)

    def genTypeAssignNew(self, varTable : Dict[str, Tuple[str, int]], stmt : TypeAssignNew3, regMap : Dict[str, str]):
        classInfo = self.classTable[stmt.cname]
        size = classInfo.getSize()
        self.assembly.append(f"   mov   a1, #{size}")
        self.assembly.append(f"   bl   malloc")
        self.assembly.str("a1", stmt.id, varTable, regMap)

    def genTypeAssignCall(self, varTable : Dict[str, Tuple[str, int]], stmt : TypeAssignCall3, regMap : Dict[str, str]):

        for i,arg in enumerate(stmt.args):
            if i >= 4:
                break
            else:
                if arg.isdigit():
                    self.assembly.append(f"   mov   a{i+1}, #{arg}")
                elif arg in self.dataTable:
                    self.assembly.append(f"   ldr   a{i+1}, ={self.dataTable[arg]} + 0")
                else:
                    self.assembly.ldr(f"a{i+1}", arg, varTable, regMap)

        if stmt.call.split("_")[0] == "this":
            cname = varTable["this"][0]
            label = cname + "_" + "_".join(stmt.call.split("_")[1:])
        else:
            label = stmt.call

        self.assembly.append("   stmfd   sp!,{v6, v7}") # caller save
        for i,arg in enumerate(stmt.args[4:][::-1]): # save the rest of args to stack in reverse order
            if arg.isdigit():
                self.assembly.append(f"   mov   ip, #{arg}")
            elif arg in self.dataTable:
                self.assembly.append(f"   ldr   ip, ={self.dataTable[arg]} + 0")
            else:
                self.assembly.ldr("ip", arg, varTable, regMap)
            self.assembly.append(f"   str   ip, [sp,#-{i*4}]")
        if len(stmt.args) > 4:
            self.assembly.append(f"   sub   sp, sp, #{(len(stmt.args)-4)*4}")

        self.assembly.append(f"   bl   {label}")

        if len(stmt.args) > 4:
            self.assembly.append(f"   add   sp, sp, #{(len(stmt.args)-4)*4}")
        self.assembly.append("   ldmfd   sp!,{v6, v7}")
        self.assembly.str("a1", stmt.id, varTable, regMap)

    def genTypeAssignAtomAccess(self, varTable : Dict[str, Tuple[str, int]], stmt : TypeAssignAtomAccess3, regMap : Dict[str, str]):
        cname = varTable[stmt.obj][0]
        offset = self.classTable[cname].getOffset(stmt.field)
        self.assembly.ldr("a2", stmt.obj, varTable, regMap)
        self.assembly.append(f"   ldr   a1, [a2,#-{offset}]")
        self.assembly.str("a1", stmt.id, varTable, regMap)

    def genAssign(self, varTable : Dict[str, Tuple[str, int]], stmt : Assign3, regMap : Dict[str, str]):
        if stmt.result.isdigit():
            self.assembly.append(f"   mov   a1, #{stmt.result}")
        elif stmt.result in self.dataTable:
            self.assembly.append(f"   ldr   a1, ={self.dataTable[stmt.result]} + 0")
        elif stmt.result == "true":
            self.assembly.append(f"   mov   a1, #1")
        elif stmt.result == "false":
            self.assembly.append(f"   mov   a1, #0")
        elif stmt.result in varTable:
            self.assembly.ldr("a1", stmt.result, varTable, regMap)
        else:
            self.assembly.ldrGlobal("a1", stmt.result, varTable, regMap, self.classTable)

        if "." in stmt.id:
            (obj, field) = stmt.id.split(".")
            if obj in varTable:
                self.assembly.ldr("a2", obj, varTable, regMap)
                self.assembly.append(f"   str   a1, [a2,#-{self.classTable[varTable[obj][0]].getOffset(field)}]")
        elif stmt.id in varTable:
            self.assembly.str("a1", stmt.id, varTable, regMap)
        else:
            self.assembly.strGlobal("a1", stmt.id, varTable, regMap, self.classTable)

    def genBinaryOp(self, varTable : Dict[str, Tuple[str, int]], stmt : BinaryOp3, regMap : Dict[str, str]):
        if stmt.lhs.isdigit():
            self.assembly.append(f"   mov   a1, #{stmt.lhs}")
        elif stmt.lhs in self.dataTable:
            raise ArmGenException("string operation not supported")
        elif stmt.lhs == "true":
            self.assembly.append(f"   mov   a1, #1")
        elif stmt.lhs == "false":
            self.assembly.append(f"   mov   a1, #0")
        elif stmt.lhs in varTable:
            self.assembly.ldr("a1", stmt.lhs, varTable, regMap)
        else:
            self.assembly.ldrGlobal("a1", stmt.lhs, varTable, regMap, self.classTable)

        if stmt.rhs.isdigit():
            self.assembly.append(f"   mov   a3, #{stmt.rhs}")
        elif stmt.rhs in self.dataTable:
            raise ArmGenException("string operation not supported")
        elif stmt.rhs == "true":
            self.assembly.append(f"   mov   a3, #1")
        elif stmt.rhs == "false":
            self.assembly.append(f"   mov   a3, #0")
        elif stmt.rhs in varTable:
            self.assembly.ldr("a3", stmt.rhs, varTable, regMap)
        else:
            self.assembly.ldrGlobal("a3", stmt.rhs, varTable, regMap, self.classTable)

        if stmt.op == "+":
            self.assembly.append(f"   add   a4, a1, a3")
        elif stmt.op == "-":
            self.assembly.append(f"   sub   a4, a1, a3")
        elif stmt.op == "*":
            self.assembly.append(f"   mul   a4, a1, a3")
        elif stmt.op == "&&":
            self.assembly.append(f"   and   a4, a1, a3")
        elif stmt.op == "||":
            self.assembly.append(f"   orr   a4, a1, a3")
        elif stmt.op == ">" or stmt.op == ">=":
            self.assembly.append(f"   sub   a4, a1, a3") # implement algebraically
            self.assembly.append(f"   cmp   a4, #0") # set to zero if negative
            self.assembly.append(f"   movlt   a4, #0")
        elif stmt.op == "<" or stmt.op == "<=":
            self.assembly.append(f"   sub   a4, a3, a1")
            self.assembly.append(f"   cmp   a4, #0") # set to zero if negative
            self.assembly.append(f"   movlt   a4, #0")
        elif stmt.op == "==":
            self.assembly.append(f"   cmp   a1, a3")
            self.assembly.append(f"   moveq   a4, #1")
            self.assembly.append(f"   movne   a4, #0")
        elif stmt.op == "/":
            raise ArmGenException("division is not supported")
        else:
            raise ArmGenException("not supported")

        self.assembly.str("a4", stmt.target, varTable, regMap)


    def genUnaryOp(self, varTable : Dict[str, Tuple[str, int]], stmt : UnaryOp3, regMap : Dict[str, str]):
        if stmt.operand.isdigit():
            self.assembly.append(f"   mov   a1, #{stmt.operand}")
        elif stmt.operand in varTable:
            self.assembly.ldr("a1", stmt.operand, varTable, regMap)
        else:
            self.assembly.ldrGlobal("a1", stmt.operand, varTable, regMap, self.classTable)

        self.assembly.append(f"   rsb   a1, a1, #0")

        if stmt.target in varTable:
            self.assembly.str("a1", stmt.target, varTable, regMap)
        else:
            self.assembly.strGlobal("a1", stmt.target, varTable, regMap, self.classTable)




if __name__ == '__main__':
    source_file = sys.argv[1]
    with open(source_file) as f:
        source_code = f.read()
    lexer = Lexer(source_code)
    parser = Parser(lexer)
    astree = parser.parse()
    checker = Checker().check(astree)
    IR3 = IR3(astree)
    assembly = ArmGen(IR3).genArm()
    assembly.print()
