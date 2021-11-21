# Ye Guoquan, A0188947A
import sys
import argparse
from typing import Dict, Tuple
from lex import Lexer
from parse import Parser
from gen import Checker
from ir3 import IR3
from arm import ArmGen
from optimize import Optimizer


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('input', help='input file')
    argparser.add_argument('-O', '--optimize', help='optimize program', action='store_true')
    args = argparser.parse_args()
    source_file = args.input
    with open(source_file) as f:
        source_code = f.read()
    lexer = Lexer(source_code)
    parser = Parser(lexer)
    astree = parser.parse()
    checker = Checker().check(astree)
    IR3 = IR3(astree).generateIR3()
    if args.optimize:
    	assembly = ArmGen(Optimizer(IR3).optimize()).genArm()
    else:
    	assembly = ArmGen(IR3).genArm()
    assembly.print()
