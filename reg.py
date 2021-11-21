# Ye Guoquan, A0188947A
from ir3 import *
from typing import List, Set, Dict, Tuple


class ProgramPoint:
	def __init__(self, inst : Stmt3):
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


class RegisterAllocator:
	def __init__(self, method : CMethod3):
		self.method = method
		self.vars : Set[str] = set()
		self.points : List[ProgramPoint] = []
		self.labels : Dict[str, int] = {}
		self.blocks : Dict[int, BlockInfo] = {} 
		self.inference : Dict[str, Set[str]] = {}
		self.regMap : Dict[str, str] = {}
		self.build()

	def build(self):
		#print("buildVars")
		self.buildVars()
		#print("buildProgramPoints")
		self.buildProgramPoints()
		#print("buildCFG")
		self.buildCFG()
		#print("livenessAnalysis")
		self.livenessAnalysis()
		#print("buildInference")
		self.buildInference()
		#print("graphColoring")
		self.graphColoring()

	def buildVars(self):
		for arg in self.method.formals:
			self.vars.add(arg.id)
		for var in self.method.body.varDecls:
			self.vars.add(var.id)
		for stmt in self.method.body.stmts:
			if isinstance(stmt, TypeAssign3):
				self.vars.add(stmt.id)
			elif isinstance(stmt, BinaryOp3):
				self.vars.add(stmt.target)

	def buildProgramPoints(self):
		i = 0
		for stmt in self.method.body.stmts:
			if isinstance(stmt, Label3):
				self.labels[stmt.label] = i
			else:
				self.points.append(ProgramPoint(stmt))
				i += 1

	def buildCFG(self):
		cur = 0
		for i, point in enumerate(self.points):
			if i in self.labels.values():
				self.blocks[cur].addOut(i)
				cur = i
				if cur not in self.blocks:
					self.blocks[cur] = BlockInfo()
				self.blocks[cur].addPoint(point)
			elif point.branch():
				if cur not in self.blocks:
					self.blocks[cur] = BlockInfo()
				self.blocks[cur].addPoint(point)
				dest = self.labels[point.branch()]
				self.blocks[cur].addOut(dest)
				if dest not in self.blocks:
					self.blocks[dest] = BlockInfo()
				self.blocks[dest].addIn(cur)
				cur = i + 1
			else:
				if cur not in self.blocks:
					self.blocks[cur] = BlockInfo()
				self.blocks[cur].addPoint(point)


	def livenessAnalysis(self):
		update = True
		while update:
			update = False
			for block in reversed(list(self.blocks.values())):
				for i,point in reversed(list(enumerate(block.points))):
					alive = set() # variables that will live before this point

					# rule 1: out = union(successor_in)
					if i == len(block.points) - 1:
						for block_id in list(block.outs):
							alive = alive | self.blocks[block_id].getInAlive()
						if block.outAlive != alive:
							update = True
							block.outAlive = alive
					else:
						alive = block.points[i+1].alive

					die, live = self.liveChange(point.inst)

					alive = (alive - die) | live

					# rule 4: in = out
					if point.alive != alive:
						update = True
						point.alive = alive

	def liveChange(self, stmt : Stmt3) -> Tuple[Set[str], Set[str]]:
		# rule 2: if assigned, then die 
		# rule 3: if refered, then live
		die = set()
		live = set()

		def liveAddVar(var):
			if var in self.vars: # local variable
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
			if "." in stmt.id:
				# atom access
				obj = stmt.id.split(".")[0]
				liveAddVar(obj)
			elif stmt.id in self.vars:
				die.add(stmt.id)
			else:
				# implicit refer to global
				live.add("this")

			if "." in stmt.result:
				# atom access
				obj = stmt.result.split(".")[0]
				liveAddVar(stmt.obj)
			elif stmt.result in self.vars:
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


	def buildInference(self):
		for arg in self.vars:
			self.inference[arg] = set()

		for block in self.blocks.values():
			for point in block.points:
				for var in list(point.alive):
					self.inference[var] |= (point.alive - {var})
			for var in block.outAlive:
				self.inference[var] |= (block.outAlive - {var})

	def graphColoring(self):
		stack : List[Tuple[str, Set[str]]] = []
		spill : Set[str] = set()

		remaining = list(self.vars)
		while remaining:
			select = False
			for var in remaining:
				if len(self.inference[var]) < 7:
					select = True
					stack.append((var, self.inference[var]))
					remaining.remove(var)
					for neighbour in self.inference[var]:
						self.inference[neighbour].remove(var)

			if not select: # all >= 7, randomly pick one to spill
				var = remaining.pop()
				spill.add(var)
				stack.append((var, self.inference[var]))
				for neighbour in self.inference[var]:
					self.inference[neighbour].remove(var)

		fullSet = {"v1", "v2", "v3", "v4", "v5", "v6", "v7"}

		while stack:
			(var, edges) = stack.pop()
			self.inference[var] = edges
			for neighbour in list(edges):
				self.inference[neighbour].add(var)

			if var not in spill:
				colors = set()
				for neighbour in list(edges): 
					if neighbour in self.regMap:
						colors.add(self.regMap[neighbour])
				colors = fullSet - colors
				self.regMap[var] = colors.pop()

		for var in spill:
			self.regMap[var] = "spill"








