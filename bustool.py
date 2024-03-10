#!/usr/bin/env python3

import yaml, math


def reflect_repr(instance):
    """__repr__() implementation for classes that directly set their member variables from constructor parameters."""
    code     = type(instance).__init__.__code__
    argnames = code.co_varnames[1:code.co_argcount]
    return type(instance).__name__ + "(" + ", ".join(str(getattr(instance, x)) for x in argnames) + ")"


class Span:
    __repr__ = reflect_repr
    def __init__(self, msb: int, lsb: int):
        if msb < lsb:
            raise ValueError("MSB should be higher than LSB")
        self.msb   = msb
        self.lsb   = lsb
        self.width = msb - lsb + 1
    
    @staticmethod
    def parse(raw):
        if '-' in raw:
            s = raw.split('-')
            return Span(int(s[0]), int(s[1]))
        else:
            v = int(raw)
            return Span(v, v)
    
    @staticmethod
    def default():
        return Span(0, 0)


class Parameter:
    __repr__ = reflect_repr
    def __init__(self, desc: str, default: str):
        self.desc    = desc
        self.default = default
    
    @staticmethod
    def parse(raw):
        return Parameter(raw["desc"] if "desc" in raw else None, raw["default"])


class Operator:
    def __init__(self, name, precedence, builder, func, min_args = 2, max_args = 2**32):
        self.name       = name
        self.precedence = precedence
        self.builder    = builder
        self.func       = func
        self.min_args   = min_args
        self.max_args   = max_args
    
    def check_argc(self, n):
        if not self.min_args <= n <= self.max_args:
            raise ValueError("Invalid number of arguments for " + self.name)
    
    def __call__(self, args: list[int]):
        self.check_argc(len(args))
        return self.func(args)
    
    def __repr__(self):
        return self.name
    
    def build(self, args: list[str]):
        self.check_argc(len(args))
        if self.builder[0] == '$':
            return self.builder + "(" + ", ".join(args) + ")"
        elif self.max_args == 1:
            return self.builder + args[0]
        else:
            return (' ' + self.builder + ' ').join(args)

def _product(args: list[int]):
    n = 1
    for i in args: n *= i
    return n

def _clog2(args: list[int]):
    return math.ceil(math.log2(args[0]))

operators = {
    "$sum":   Operator("sum",   8,  "+",  sum),
    "$prod":  Operator("prod",  8,  "*",  _product),
    
    "$sqrt":  Operator("sqrt",  10, "$sqrt",  lambda x: math.sqrt(x[0]), 1, 1),
    "$clog2": Operator("clog2", 10, "$clog2", _clog2, 1, 1),
    
    "$not":   Operator("not",   10, "!",  lambda x: not x[0],      1, 1),
    "$and":   Operator("and",   1,  "&&", lambda x: x[0] and x[1], 2, 2),
    "$or":    Operator("or",    0,  "||", lambda x: x[0] or  x[1], 2, 2),
    
    "$notb":  Operator("notb",  0,  "~",  lambda x: ~x[0],         1, 1),
    "$andb":  Operator("andb",  4,  "&",  lambda x: x[0] &   x[1], 2, 2),
    "$orb":   Operator("orb",   2,  "|",  lambda x: x[0] |   x[1], 2, 2),
    "$xorb":  Operator("xorb",  3,  "^",  lambda x: x[0] ^   x[1], 2, 2),
    "$shl":   Operator("shl",   7,  "<<", lambda x: x[0] or  x[1], 2, 2),
    "$shr":   Operator("shr",   7,  ">>", lambda x: x[0] or  x[1], 2, 2),
    
    "$add":   Operator("add",   8,  "+",  lambda x: x[0] +  x[1], 2, 2),
    "$sub":   Operator("sub",   8,  "-",  lambda x: x[0] -  x[1], 2, 2),
    "$mul":   Operator("mul",   9,  "*",  lambda x: x[0] *  x[1], 2, 2),
    "$div":   Operator("div",   9,  "/",  lambda x: x[0] // x[1], 2, 2),
    "$mod":   Operator("mod",   9,  "%",  lambda x: x[0] %  x[1], 2, 2),
    
    "$gt":    Operator("gt",    6,  ">",  lambda x: x[0] >  x[1], 2, 2),
    "$lt":    Operator("lt",    6,  "<",  lambda x: x[0] <  x[1], 2, 2),
    "$ge":    Operator("ge",    6,  ">=", lambda x: x[0] >= x[1], 2, 2),
    "$le":    Operator("le",    6,  "<=", lambda x: x[0] <= x[1], 2, 2),
    "$eq":    Operator("eq",    5,  "==", lambda x: x[0] == x[1], 2, 2),
    "$ne":    Operator("ne",    5,  "!=", lambda x: x[0] != x[1], 2, 2),
}


class Expression:
    __repr__ = reflect_repr
    def __init__(self, typ: str|Operator, args: list|int|str):
        self.typ        = typ
        self.args       = args
        self.precedence = 11
        if type(typ) is Operator:
            self.precedence = self.typ.precedence
    
    @staticmethod
    def parse(raw):
        global operators
        if type(raw) is str:
            return Expression("var", raw)
        elif type(raw) is int:
            return Expression("const", raw)
        elif type(raw) is not dict:
            raise ValueError("Expected int, str or dict")
        elif len(raw) != 1:
            raise ValueError("Expected exactly one operator")
        for key in raw:
            if key not in operators:
                raise ValueError("Unknown operator: " + key)
            val = raw[key]
            if type(val) is list:
                operators[key].check_argc(len(val))
                return Expression(operators[key], [Expression.parse(x) for x in val])
            else:
                operators[key].check_argc(1)
                return Expression(operators[key], [Expression.parse(val)])
    
    def eval(self, vars: dict = {}):
        if self.typ == "var":
            return vars[self.args]
        elif self.typ == "const":
            return self.args
        elif type(self.typ) is not Operator:
            raise ValueError("Invalid expression type: " + repr(self.typ))
        return int(self.typ([x.eval(vars) for x in self.args]))
    
    def build(self, vars: dict = {}):
        if self.typ == "var":
            return vars[self.args]
        elif self.typ == "const":
            return str(self.args)
        elif type(self.typ) is not Operator:
            raise ValueError("Invalid expression type: " + repr(self.typ))
        
        tmp = [x.build(vars) for x in self.args]
        for i in range(len(self.args)):
            if self.args[i].precedence < self.precedence:
                tmp[i] = "(" + tmp[i] + ")"
        
        return self.typ.build(tmp)


f    = open("test/expr.yml", "r")
raw  = yaml.safe_load(f)
x    = Expression.parse(raw)
vars = {"is_ok": "is.ok", "is_fine": "is.fine"}
print(x.build(vars))
