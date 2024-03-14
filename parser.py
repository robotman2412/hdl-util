
import yaml, math


def reflect_repr(instance):
    """__repr__() implementation for classes that directly set their member variables from constructor parameters."""
    code     = type(instance).__init__.__code__
    argnames = code.co_varnames[1:code.co_argcount]
    return type(instance).__name__ + "(" + ", ".join(repr(getattr(instance, x)) for x in argnames) + ")"


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
    def __init__(self, typ: str|Operator, args: list|int|str):
        self.typ        = typ
        self.args       = args
        self.precedence = 11
        if typ == "var":
            self.vars = {args: args}
        elif type(typ) is Operator:
            self.precedence = self.typ.precedence
            self.vars = {}
            for x in self.args:
                for var in x.vars:
                    self.vars[var] = var
        else:
            self.vars = {}
    
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
    
    def __repr__(self):
        return self.build(self.vars)


class Parameter:
    __repr__ = reflect_repr
    def __init__(self, id: str, desc: str, default: Expression):
        self.id      = id
        self.desc    = desc
        self.default = default
    
    @staticmethod
    def parse(id: str, raw: dict):
        return Parameter(id, raw["desc"] if "desc" in raw else None, Expression.parse(raw["default"]))


class Span:
    __repr__ = reflect_repr
    def __init__(self, msb: Expression, lsb: Expression):
        self.msb   = msb
        self.lsb   = lsb
    
    def is_default(self) -> bool:
        if self.msb.typ != "const" or self.lsb.typ != "const":
            return False
        return self.msb.args == 0 and self.lsb.args == 0
    
    @staticmethod
    def parse(raw):
        if type(raw) in [list, tuple]:
            return Span(Expression.parse(raw[1]), Expression.parse(raw[0]))
        elif type(raw) is str and '-' in raw:
            s = raw.split('-')
            return Span(int(s[0]), int(s[1]))
        else:
            return Span(Expression.parse({"$sub": [raw, 1]}), Expression("const", 0))
    
    @staticmethod
    def default():
        return Span(Expression("const", 0), Expression("const", 0))


class ClockSpec:
    __repr__ = reflect_repr
    def __init__(self, typ: str, sigid: str, rising: bool):
        self.typ    = typ
        self.sigid  = sigid
        self.rising = rising
    
    @staticmethod
    def parse(raw):
        if type(raw) is not dict:
            raise ValueError("Invalid clock specification")
        if raw["edge"] not in ["rising", "falling"]:
            raise ValueError("Invalid clock edge")
        if raw["type"] not in ["ext_clock", "bus_clock"]:
            raise ValueError("Invalid clock type")
        return ClockSpec(raw["type"], raw["signal"], raw["edge"] == "rising")
    
    def build(self, ref, parent):
        return self.sigid if self.typ == "ext_clk" else parent.build_sigref(ref, self.sigid)


class TransSpec:
    __repr__ = reflect_repr
    def __init__(self, request: Expression, accept: Expression, stall: Expression):
        self.request = request
        self.accept  = accept
        self.stall   = stall
    
    @staticmethod
    def parse(raw):
        if type(raw) is not dict:
            raise ValueError("Invalid transaction specification")
        return TransSpec(
            Expression.parse(raw["request"]),
            Expression.parse(raw["accept"]) if "accept" in raw else Expression("const", 1),
            Expression.parse(raw["stall"])  if "stall"  in raw else Expression("const", 0),
        )


class Signal:
    __repr__ = reflect_repr
    def __init__(self, id: str, desc: str, span: Span, time: Expression, dir: str):
        self.id   = id
        self.desc = desc
        self.span = span
        self.time = time
        self.dir  = dir
    
    @staticmethod
    def parse(id, raw):
        if "dir" in raw:
            assert raw["dir"] in ["input", "output"]
        return Signal(
            id,
            raw["desc"] if "desc" in raw else None,
            Span.parse(raw["span"]) if "span" in raw else Span.default(),
            Expression.parse(raw["time"]) if "time" in raw else Expression("const", 0),
            raw["dir"] if "dir" in raw else None
        )


class AsymmetricBus:
    __repr__ = reflect_repr
    def __init__(self, id: str, desc: str, ctl: str, dev: str, params: list[Parameter], trans: TransSpec, clk: ClockSpec, signals: list[Signal]):
        self.id      = id
        self.desc    = desc
        self.ctl     = ctl
        self.dev     = dev
        self.params  = params
        self.trans   = trans
        self.clk     = clk
        self.signals = signals
    
    @staticmethod
    def parse(id: str, raw: dict):
        params = []
        if "parameters" in raw:
            for key in raw["parameters"]:
                params.append(Parameter.parse(key, raw["parameters"][key]))
        signals = []
        for key in raw["signals"]:
            signals.append(Signal.parse(key, raw["signals"][key]))
        return AsymmetricBus(
            id,
            raw["desc"] if "desc" in raw else None,
            raw["controller"],
            raw["device"],
            params,
            TransSpec.parse(raw["transaction"]),
            ClockSpec.parse(raw["clock"]),
            signals
        )


def read_file(path):
    with open(path, "r") as fd:
        return yaml.safe_load(fd)
