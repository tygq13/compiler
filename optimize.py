# Ye Guoquan, A0188947A
from ir3 import *
from typing import Dict, List, Tuple, Set

class ProgramPoint:
    def __init__(self, inst : IR3ASTNode):
        self.inst = inst
        self.alive = set()

    def branch(self):
        if isinstance(self.inst, Goto3) or isinstance(self.inst, IfGoto3):
            return self.inst.label
        return None


class BlockInfo:
    def __init__(self):
        self.points = [] # refer to point BEFORE the instruction
        self.ins = set()
        self.outs = set()
        self.outAlive = set() 

    def addPoint(self, point : ProgramPoint):
        self.points.append(point)

    def addIn(self, num : int):
        self.ins.add(num)

    def addOut(self, num : int):
        self.outs.add(num)

    def getInAlive(self):
        if self.points:
            return self.points[0].alive
        return set()



class Optimizer:
    def __init__(self, program : Program3):
        self.program = program

    def optimize(self) -> Program3:
        for method in self.program.cMethod3List:
            (labels, points) = self.buildProgramPoints(method.body)
            blocks = self.buildCFG(labels, points)
            symbols = self.buildSymbols(method)
            for block_id in blocks:
                 # local optimization
                self.constantPropagation(blocks[block_id])
            self.deadCodeElimination(blocks, symbols)
            new_statements = self.reconstructBody(blocks, labels)
            method.body.stmts = new_statements
        return self.program

    def reconstructBody(self, blocks : Dict[int,BlockInfo], labels : Dict[str, int]) -> List[Stmt3]:
        statements = []
        for block_id in sorted(blocks.keys()):
            for label in labels:
                if labels[label] == block_id:
                    statements.append(Label3(label))
                    break
            for point in blocks[block_id].points:
                statements.append(point.inst)
        return statements


    def top(self):
        return "#" # use # to represent top, for no reason other than convenient

    def bottom(self):
        return "$" # use $ to represent bottom, for no reason other than convenient  

    def isTop(self, str : str):
        return str == "#"

    def isBotoom(self, str : str):
        return str == "$" 

    def newAssignStmt(self, type :str, id : str, var : str, valMap : Dict[str, str]):
        if var in valMap and not self.isTop(valMap[var]):
            valMap[id] = valMap[var]
            if "." not in valMap[var]:
                return TypeAssign3(type, id, valMap[var])
            else:
                obj, field = valMap[var].split(".")
                return TypeAssignAtomAccess3(type, id, obj, field)
        return None

    def constantPropagation(self, block : BlockInfo):
        valMap = {}
        # update value map sequentially
        for i,point in enumerate(block.points):
            stmt = point.inst
            if isinstance(stmt, TypeAssignNew3):
                valMap[stmt.id] = self.top()
            elif isinstance(stmt, TypeAssignAtomAccess3):
                rhs = stmt.obj + "." + stmt.field
                valMap[stmt.id] = rhs
                newStmt = self.newAssignStmt(stmt.type, stmt.id, rhs, valMap)
                point.inst = newStmt if newStmt else point.inst
            elif isinstance(stmt, TypeAssignCall3):
                valMap[stmt.id] = self.top()
            elif isinstance(stmt, TypeAssign3):
                valMap[stmt.id] = stmt.value
                newStmt = self.newAssignStmt(stmt.type, stmt.id, stmt.value, valMap)
                point.inst = newStmt if newStmt else point.inst
            elif isinstance(stmt, Assign3):
                valMap[stmt.id] = stmt.result
                if stmt.result in valMap and not self.isTop(valMap[stmt.result]):
                    valMap[stmt.id] = valMap[stmt.result]
                    point.inst = Assign3(stmt.id, valMap[stmt.result])
            elif isinstance(stmt, BinaryOp3):
                # replace
                if stmt.lhs in valMap and not self.isTop(valMap[stmt.lhs]):
                    lhs = valMap[stmt.lhs]
                else:
                    lhs = stmt.lhs

                if stmt.rhs in valMap and not self.isTop(valMap[stmt.rhs]):
                    rhs = valMap[stmt.rhs]
                else:
                    rhs = stmt.rhs

                if (lhs != stmt.lhs or rhs != stmt.rhs) and "." not in lhs and "." not in rhs:
                    point.inst = BinaryOp3(stmt.type, stmt.target, lhs, stmt.op, rhs)

                # evaluate
                if lhs.isdigit() and rhs.isdigit():
                    if stmt.op == "+" or stmt.op == "-" or stmt.op == "*" or stmt.op == ".":
                        op = "//" if stmt.op == "/" else stmt.op
                        valMap[stmt.target] = str(eval(lhs + op + rhs)) # yo, have fun with command injection bypass
                        point.inst = TypeAssign3("Int", stmt.target, valMap[stmt.target])
                    elif stmt.op == ">" or stmt.op == ">=" or stmt.op == "==" or stmt.op == "<" or stmt.op == "<=":
                        valMap[stmt.target] = str(eval(lhs+stmt.op+rhs)).lower()
                        point.inst = TypeAssign3("Bool", stmt.target, valMap[stmt.target])
                elif lhs.startswith("\"") and rhs.startswith("\""):
                    if stmt.op == "+":
                        valMap[stmt.target] = lhs[:-1] + rhs[1:]
                        point.inst = TypeAssign3("String", stmt.target, valMap[stmt.target])
                elif (lhs == "true" or lhs == "false") and (rhs == "true" or rhs == "false"):
                    if stmt.op == "&&":
                        lhs = lhs[0].upper() + lhs[1:]
                        rhs = rhs[0].upper() + rhs[1:]
                        valMap[stmt.target] = str(eval(lhs + " and " + rhs)).lower()
                        point.inst = TypeAssign3("Bool", stmt.target, valMap[stmt.target])
                    elif stmt.op == "||":
                        lhs = lhs[0].upper() + lhs[1:]
                        rhs = rhs[0].upper() + rhs[1:]
                        valMap[stmt.target] = str(eval(lhs + " or " + rhs)).lower()
                        point.inst = TypeAssign3("Bool", stmt.target, valMap[stmt.target])
                    else:
                        assert False
            elif isinstance(stmt, Return3):
                if stmt.id and stmt.id in valMap:
                    point.inst = Return3(valMap[stmt.id])
            elif isinstance(stmt, Println3):
                if stmt.id in valMap:
                    point.inst = Println3(valMap[stmt.id])
            elif isinstance(stmt, Readln3):
                if stmt.id in valMap:
                    point.inst = Readln3(valMap[stmt.id])
            elif isinstance(stmt, IfGoto3):
                if stmt.cond in valMap:
                    point.inst = IfGoto3(valMap[stmt.cond], stmt.label)
                    if valMap[stmt.cond] == "true":
                        point.inst = Goto3(stmt.label)
            elif isinstance(stmt, UnaryOp3):
                if stmt.operand in valMap:
                    valMap[stmt.operand] = self.top() #
            # TODO: optimize unaryOp3 now
            # point.varMap = valMap.copy() # only needed in global constant propagation


    def deadCodeElimination(self, blocks : Dict[int, BlockInfo], symbols : Set[str]):
        self.livenessAnalysis(blocks, symbols)
        for block in blocks.values():
            valid = [True] * len(block.points)
            for (i,point) in enumerate(block.points):
                stmt = point.inst
                if i != len(block.points) - 1:
                    aliveOut = block.points[i+1].alive
                else:
                    aliveOut = block.outAlive

                if isinstance(stmt, TypeAssignNew3):
                    if stmt.id not in aliveOut:
                        valid[i] = False
                elif isinstance(stmt, TypeAssignCall3):
                    pass
                elif isinstance(stmt, TypeAssignAtomAccess3):
                    if stmt.id not in aliveOut:
                        valid[i] = False
                elif isinstance(stmt, TypeAssign3):
                    if stmt.id not in aliveOut:
                        valid[i] = False
                elif isinstance(stmt, Assign3):
                    if (stmt.id not in aliveOut) and (stmt.id in symbols):
                        valid[i] = False
                elif isinstance(stmt, BinaryOp3):
                    if stmt.target not in aliveOut:
                        valid[i] = False
                elif isinstance(stmt, UnaryOp3):
                    if stmt.target not in aliveOut:
                        valid[i] = False
                elif isinstance(stmt, IfGoto3):
                    if stmt.cond == "false":
                        valid[i] = False

            new_sequence = []
            for i,point in enumerate(block.points):
                if valid[i]:
                    new_sequence.append(point)
            block.points = new_sequence



    def livenessAnalysis(self, blocks : Dict[int, BlockInfo], symbols : Set[str]):
        update = True
        while update:
            update = False
            for block in reversed(list(blocks.values())):
                for i,point in reversed(list(enumerate(block.points))):
                    alive = set() # variables that will live before this point

                    # rule 1: out = union(successor_in)
                    if i == len(block.points) - 1:
                        for block_id in list(block.outs):
                            alive = alive | blocks[block_id].getInAlive()
                        if block.outAlive != alive:
                            update = True
                            block.outAlive = alive
                    else:
                        alive = block.points[i+1].alive

                    die, live = self.liveChange(point.inst, symbols)

                    alive = (alive - die) | live

                    # rule 4: in = out
                    if point.alive != alive:
                        update = True
                        point.alive = alive


    def liveChange(self, stmt : Stmt3, symbols : Set[str]) -> Tuple[Set[str], Set[str]]:
        # rule 2: if assigned, then die 
        # rule 3: if refered, then live
        die = set()
        live = set()

        def liveAddVar(var):
            if var in symbols: # local variable
                live.add(var)
            elif not (var.isdigit() or var.startswith("\"") or var == "true" or var == "false"):
                live.add("this")

        if isinstance(stmt, IfGoto3):
            liveAddVar(stmt.cond)
        elif isinstance(stmt, Readln3):
            liveAddVar(stmt.id)
        elif isinstance(stmt, Println3):
            liveAddVar(stmt.id)
        elif isinstance(stmt, Return3):
            if stmt.id:
                liveAddVar(stmt.id)
        elif isinstance(stmt, TypeAssignAtomAccess3):
            die.add(stmt.id)
            liveAddVar(stmt.obj)
        elif isinstance(stmt, TypeAssignNew3):
            die.add(stmt.id)
        elif isinstance(stmt, TypeAssignCall3):
            die.add(stmt.id)
            for arg in stmt.args:
                liveAddVar(arg)
        elif isinstance(stmt, Assign3):
            if stmt.id in symbols:
                die.add(stmt.id)
            else:
                # implicit refer to global
                live.add("this")
            live.add(stmt.result)
        elif isinstance(stmt, TypeAssign3):
            die.add(stmt.id)
            liveAddVar(stmt.value)
        elif isinstance(stmt, BinaryOp3):
            die.add(stmt.target)
            liveAddVar(stmt.lhs)
            liveAddVar(stmt.rhs)
        elif isinstance(stmt, UnaryOp3):
            die.add(stmt.target)
            liveAddVar(stmt.operand)
        return (die, live)

    # get all symbols of a method
    def buildSymbols(self, method : CMethod3) -> Set[str]:
        symbols : Set[str] = set()
        for arg in method.formals:
            symbols.add(arg.id)
        for var in method.body.varDecls:
            symbols.add(var.id)
        for stmt in method.body.stmts:
            if isinstance(stmt, TypeAssign3):
                symbols.add(stmt.id)
            elif isinstance(stmt, BinaryOp3):
                symbols.add(stmt.target)
        return symbols


    def buildProgramPoints(self, block : Block3) -> Tuple[Dict[str, int], List[ProgramPoint]] :
        labels : Dict[str, int] = {}
        points : List[ProgramPoint] = []
        i = 0
        for stmt in block.stmts:
            # TODO: include varDecl so that it can be deleted on dead
            if isinstance(stmt, Label3):
                labels[stmt.label] = i
            else:
                points.append(ProgramPoint(stmt))
                i += 1
        return labels, points


    def buildCFG(self, labels : Dict[str, int], points : List[ProgramPoint]) -> Dict[int, BlockInfo]:
        cur = 0
        blocks : Dict[int, BlockInfo] = {}
        for i, point in enumerate(points):
            if i in labels.values():
                blocks[cur].addOut(i)
                cur = i
                if cur not in blocks:
                    blocks[cur] = BlockInfo()
                blocks[cur].addPoint(point)
            elif point.branch():
                if cur not in blocks:
                    blocks[cur] = BlockInfo()
                blocks[cur].addPoint(point)
                dest = labels[point.branch()]
                blocks[cur].addOut(dest)
                if dest not in blocks:
                    blocks[dest] = BlockInfo()
                blocks[dest].addIn(cur)
                cur = i + 1
            else:
                if cur not in blocks:
                    blocks[cur] = BlockInfo()
                blocks[cur].addPoint(point)
        return blocks