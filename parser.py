
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
        if callable(self.builder):
            return self.builder(self, args)
        elif self.builder[0] == '$':
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

def _bitslice(args: list[int]):
    val = args[0]
    msb = args[1]
    lsb = args[2]
    return (val >> lsb) & ((1 << (msb - lsb)) - 1)

def _index(args: list[int]):
    val = args[0]
    msb = args[1]
    return (val >> msb) & 1

def _slb(oper: Operator, args: list[str]):
    tmp = []
    for x in args[1:]:
        if x[0] == '(' and x[-1] == ')':
            tmp.append(x[1:-1])
        else:
            tmp.append(x)
    return f"{args[0]}[{':'.join(tmp)}]"

def _ifb(oper: Operator, args: list[str]):
    return f"{args[0]} ? {args[1]} : {args[2]}"

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
    "$shl":   Operator("shl",   7,  "<<", lambda x: x[0] <<  x[1], 2, 2),
    "$shr":   Operator("shr",   7,  ">>", lambda x: x[0] >>  x[1], 2, 2),
    
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
    
    "$if":    Operator("if",    -1, _ifb, lambda x: x[1] if x[0] else x[2], 3, 3),
    "$set":   Operator("set",   -2, "=",  lambda x: x[1], 2, 2),
    "$slice": Operator("slice", 10, _slb, _bitslice, 3, 3),
    "$index": Operator("index", 10, _slb, _index, 2, 2)
}


class Expression:
    def __init__(self, typ: str|Operator, args: list|int|str = None):
        if args == None:
            args = typ
            typ  = "raw"
        if typ in operators:
            typ = operators[typ]
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
        elif self.typ == "raw":
            return self.args
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
    def __init__(self, msb: Expression = None, lsb: Expression = None):
        if msb == None and lsb == None:
            self.msb = self.lsb = Expression("const", 0)
        elif lsb == None:
            if msb.typ == "const":
                self.msb = Expression("const", msb.args-1)
            else:
                self.msb = Expression(operators["$sub"], [msb, Expression("const", 1)])
            self.lsb = Expression("const", 0)
        else:
            self.msb = msb
            self.lsb = lsb
    
    def build(self, vars: dict) -> str:
        return f"[{self.msb.build(vars)}:{self.lsb.build(vars)}]"
    
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
            return Span(Expression.parse(raw))
    
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
    
    def build(self, ref):
        return self.sigid if self.typ == "ext_clk" else f"{ref}.{self.sigid}"


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
    def __init__(self, id: str, desc: str, span: Span, count = Expression("const", 1), time = Expression("const", 0), dir: str = "input", masked: bool = False):
        self.id     = id
        self.desc   = desc
        self.span   = span
        self.count  = count
        self.time   = time
        self.dir    = dir
        self.masked = masked
    
    @staticmethod
    def parse(id, raw):
        if "dir" in raw:
            assert raw["dir"] in ["input", "output"]
        return Signal(
            id,
            raw["desc"] if "desc" in raw else None,
            Span.parse(raw["span"]) if "span" in raw else Span.default(),
            Expression.parse(raw["count"]) if "count" in raw else Expression("const", 0),
            Expression.parse(raw["time"]) if "time" in raw else Expression("const", 0),
            raw["dir"] if "dir" in raw else None,
            raw["masked"] if "masked" in raw else False
        )


class AsymmetricBus:
    __repr__ = reflect_repr
    def __init__(self, id: str, desc: str, ctl: str, dev: str, params: list[Parameter], trans: TransSpec, clk: ClockSpec, addr: str, signals: list[Signal]):
        self.id      = id
        self.desc    = desc
        self.ctl     = ctl
        self.dev     = dev
        self.params  = params
        self.trans   = trans
        self.clk     = clk
        self.addr    = addr
        self.signals = signals
    
    def analyze(self, map: dict):
        pass
    def generate(self):
        pass
    
    def getsignal(self, id: str) -> Signal|None:
        for sig in self.signals:
            if sig.id == id:
                return sig
        return None
    
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
            raw["addr"] if "addr" in raw else None,
            signals
        )


class Arbiter:
    __repr__ = reflect_repr
    def __init__(self, typ: str):
        self.typ = typ
    
    @staticmethod
    def parse(raw: dict):
        return Arbiter(raw["type"])


class BusInstance:
    __repr__ = reflect_repr
    def __init__(self, id: str, desc: str, bus: AsymmetricBus, is_ctl: bool, count: Expression = Expression("const", 1)):
        self.id     = id
        self.desc   = desc
        self.bus    = bus
        self.is_ctl = is_ctl
        self.count  = count


class GenVar:
    def __init__(self, id: str, desc: str = None):
        self.id   = id
        self.desc = desc


class Integer:
    def __init__(self, id: str, desc: str):
        self.id   = id
        self.desc = desc


class GenBlock:
    def __init__(self, body: list = []):
        self.body = body


class Block:
    def __init__(self, body: list = [], clock: str = None):
        self.body  = body
        self.clock = None


class Assign:
    def __init__(self, var: str, val: Expression):
        self.var = var
        self.val = val


class If:
    def __init__(self, cond: Expression, body):
        self.cond = cond
        self.body = body
        self.b_elif = []
        self.b_else = None
    def ElseIf(self, cond: Expression, body):
        self.b_elif.append((cond, body))
        return self
    def Else(self, body):
        self.b_else = body
        return self


class For:
    def __init__(self, init: Expression, cond: Expression, inc: Expression, body: list):
        self.init = init
        self.cond = cond
        self.inc  = inc
        self.body = body
    
    @staticmethod
    def simple(var: str, limit: Expression, body: list):
        return For(
            Expression(operators["$set"], [Expression("var", var), Expression("const", 0)]),
            Expression(operators["$lt"], [Expression("var", var), limit]),
            Expression(operators["$set"], [Expression("var", var), Expression(operators["$add"], [Expression("var", var), Expression("const", 1)])]),
            body
        )


class While:
    def __init__(self, cond: Expression, body):
        self.cond = cond
        self.body = body


class Instance:
    __repr__ = reflect_repr
    def __init__(self, typ: str, id: str, desc: str = None, params: dict[Expression|str] = {}, signals: dict[Expression] = {}):
        self.typ     = typ
        self.id      = id
        self.desc    = desc
        self.params  = params
        self.signals = signals


def HuPipelineReg(typ: str, id: str, depth: Expression, clk: Expression, d: Expression, q: Expression):
    return Instance("hu_pipeline_reg", id, None, {"regtype": typ, "depth": depth}, {"clk": clk, "d": d, "q": q})


def HuSelector(typ: str, id: str, width: Expression, sel: Expression, d: Expression, q: Expression):
    return Instance("hu_selector", id, None, {"seltype": typ, "width": width}, {"sel": sel, "d": d, "q": q})


class ActiveEntity:
    __repr__ = reflect_repr
    def __init__(self):
        self.params    = []
        self.signals   = []
        self.body      = []
        self.vars      = {}
    def analyze(self, map: dict):
        pass
    def generate(self):
        raise NotImplementedError()


class Crossbar(ActiveEntity):
    __repr__ = reflect_repr
    def __init__(self, id: str, desc: str, busid: str, arbiter: Arbiter, ctl_count: str|None, dev_count: str|None):
        self.id        = id
        self.desc      = desc
        self.busid     = busid
        self.arbiter   = arbiter
        self.bus       = None
        self.ctl_count = ctl_count
        self.dev_count = dev_count
        self.params    = []
        self.signals   = []
        self.body      = []
        self.vars      = {}
    
    def analyze(self, map: dict):
        self.bus       = map[self.busid]
        self.ctl_count = self.ctl_count or self.bus.ctl + "_count"
        self.dev_count = self.dev_count or self.bus.dev + "_count"
    
    @staticmethod
    def parse(id: str, raw: dict):
        return Crossbar(
            id,
            raw["desc"] if "desc" in raw else None,
            raw["bus"],
            Arbiter.parse(raw["arbiter"]),
            raw["ctl_count"] if "ctl_count" in raw else None,
            raw["dev_count"] if "dev_count" in raw else None
        )
    
    def generate(self):
        self.signals.append(BusInstance("ctl", None, self.bus, True))
        self.signals.append(BusInstance("dev", None, self.bus, False))


class BusMux(ActiveEntity):
    __repr__ = reflect_repr
    def __init__(self, id: str, desc: str, busid: str, dev_count: str|None, ctl_port: str, dev_port: str):
        self.id        = id
        self.desc      = desc
        self.busid     = busid
        self.bus: AsymmetricBus = None
        self.clock     = None
        self.dev_count = dev_count
        self.ctl_port  = ctl_port
        self.dev_port  = dev_port
        self.params    = []
        self.signals   = []
        self.body      = []
        self.vars      = {}
    
    def analyze(self, map: dict):
        self.bus       = map[self.busid]
        self.dev_count = self.dev_count or self.bus.dev + "_count"
        self.addr      = self.bus.getsignal(self.bus.addr)
        for param in self.bus.params:
            self.vars[param.id] = f"{self.ctl_port}.{param.id}"
    
    @staticmethod
    def parse(id: str, raw: dict):
        return BusMux(
            id,
            raw["desc"] if "desc" in raw else None,
            raw["bus"],
            raw["dev_count"] if "dev_count" in raw else None,
            raw["ctl_port"] if "ctl_port" in raw else "ctl",
            raw["dev_port"] if "dev_port" in raw else "dev"
        )
    
    def generate(self):
        # Module definition.
        self.params.append(Parameter(self.dev_count, f"Number of {self.bus.ctl} ports.", Expression("const", 2)))
        if self.bus.clk.typ == "ext_clock":
            clock = Signal(self.bus.clk.sigid, "Pipeline clock.", Span.default())
            self.signals.append(clock)
        else:
            clock = Signal(f"{self.ctl_port}.{self.bus.clk.sigid}", None, Span.default())
        self.signals.append(BusInstance(self.ctl_port, "Controller port.", self.bus, False))
        self.signals.append(BusInstance(self.dev_port, "Device ports.", self.bus, True, Expression("var", self.dev_count)))
        
        # Addressing logic.
        self.signals.append(Signal(f"map_addr", "Base addresses.", self.addr.span, Expression("var", self.dev_count)))
        self.signals.append(Signal(f"map_mask", "Address bitmasks.", self.addr.span, Expression("var", self.dev_count)))
        self.body.append(GenVar("x"))
        self.body.append(Signal(f"{self.dev_port}_sel", "Selected device.", Span(Expression("var", self.dev_count))))
        self.body.append(GenBlock([
            For.simple("x", Expression("var", self.dev_count), [
                Assign(f"{self.dev_port}_sel[x]", Expression("$eq", [
                    Expression("$andb", [
                        Expression("$index", [Expression("var", "map_addr"), Expression("var", "x")]),
                        Expression("$index", [Expression("var", "map_mask"), Expression("var", "x")])
                    ]),
                    Expression("$andb", [
                        Expression(f"{self.ctl_port}[x].{self.bus.addr}"),
                        Expression("$index", [Expression("var", "map_mask"), Expression("var", "x")])
                    ])
                ]))
            ])
        ]))
        
        # Outgoing connections.
        ls = []
        for v in self.bus.signals:
            if v.dir != "output": continue
            if v.masked:
                ls.append(Assign(f"{self.dev_port}[x].{v.id}", Expression("$if", [
                    Expression("$index", [Expression("var", f"{self.dev_port}_sel"), Expression("var", "x")]),
                    Expression(f"{self.ctl_port}[x].{v.id}"),
                    Expression("const", 0)
                ])))
            else:
                ls.append(Assign(f"{self.dev_port}[x].{v.id}", Expression(f"{self.ctl_port}[x].{v.id}")))
        self.body.append(GenBlock([For.simple("x", Expression("var", self.dev_count), ls)]))
        
        # Return connections.
        for v in self.bus.signals:
            if v.dir != "input": continue
            self.body.append(Signal(f"raw_{v.id}", "Raw return signals.", v.span, Expression("var", self.dev_count)))
        ls = []
        for v in self.bus.signals:
            if v.dir != "input": continue
            ls.append(Assign(f"raw_{v.id}[x]", Expression(f"{self.dev_port}[x].{v.id}")))
        self.body.append(GenBlock([For.simple("x", Expression("var", self.dev_count), ls)]))
        for v in self.bus.signals:
            if v.dir != "input": continue
            span = Span(Expression("var", self.dev_count))
            self.body.append(Signal(f"{self.dev_port}_sel_{v.id}", "Delayed selector signals.", span))
            self.body.append(HuPipelineReg(
                Expression("$slice", [Expression("bit"), span.msb, span.lsb]),
                f"plr_{v.id}",
                v.time if v.time else Expression("const", 0),
                Expression("var", clock.id),
                Expression("var", f"{self.dev_port}_sel"),
                Expression("var", f"{self.dev_port}_sel_{v.id}")
            ))
            self.body.append(HuSelector(
                Expression("$slice", [Expression("bit"), v.span.msb, v.span.lsb]),
                f"sel_{v.id}",
                Expression("var", self.dev_count),
                Expression("var", f"{self.dev_port}_sel_{v.id}"),
                Expression("var", f"raw_{v.id}"),
                Expression("var", f"{self.ctl_port}.{v.id}")
            ))


parseable = {
    "asymmetric_bus": AsymmetricBus,
    "crossbar": Crossbar,
    "multiplexer": BusMux
}


def read_file(path):
    with open(path, "r") as fd:
        return yaml.safe_load(fd)

def parse_file(path):
    raw  = read_file(path)
    map  = {}
    for k in raw:
        if "type" not in raw[k]:
            raise ValueError("Expected type")
        map[k] = parseable[raw[k]["type"]].parse(k, raw[k])
    for k in map:
        map[k].analyze(map)
    return map
