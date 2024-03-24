
from parser import *
from writer import *

class Entity:
    def __init__(self, typ: str, id: str, desc: str, params: list[Parameter], signals: list[Signal], body: list, vars: dict[str] = {}):
        self.typ     = typ
        self.id      = id
        self.desc    = desc
        self.params  = params
        self.signals = signals
        self.body    = body
        self.vars    = vars
        for param in self.params:
            if param.id in self.vars:
                raise ValueError(f"Multiple definitions of {param.id}")
            self.vars[param.id] = param.id
        for signal in self.signals:
            if signal.id in self.vars:
                raise ValueError(f"Multiple definitions of {signal.id}")
            if type(signal) is BusInstance:
                for subsig in signal.bus.signals:
                    self.vars[f"{signal.id}.{subsig.id}"] = f"{signal.id}.{subsig.id}"
            self.vars[signal.id] = signal.id
        for stmt in self.body:
            if type(stmt) in [Signal, Integer, GenVar, BusInstance]:
                if stmt.id in self.vars:
                    raise ValueError(f"Multiple definitions of {stmt.id}")
                self.vars[stmt.id] = stmt.id
            if type(stmt) is BusInstance:
                for subsig in stmt.bus.signals:
                    self.vars[f"{stmt.id}.{subsig.id}"] = f"{stmt.id}.{subsig.id}"
    
    def build_param(self, writer: Writer, param: Parameter, suffix: str = ';'):
        if param.desc:
            line_comment(writer, param.desc)
        writer.line(f"parameter {param.id} = {param.default}{suffix}")
    
    def build_var(self, writer: Writer, var: GenVar|Integer, typ: str):
        if var.desc:
            line_comment(writer, var.desc)
        writer.line(f"{typ} {var.id};")
    
    def build_signal(self, writer: Writer, signal: Signal|BusInstance, suffix: str = ';', is_port: bool = False):
        if signal.desc:
            line_comment(writer, signal.desc)
        if type(signal) is BusInstance:
            writer.write(f"{signal.bus.id}.{signal.bus.ctl if signal.is_ctl else signal.bus.dev}")
        else:
            if is_port:
                writer.write(f"{signal.dir} logic")
            else:
                writer.write("logic")
            if not signal.span.is_default():
                writer.write(f"[{signal.span.msb.build(self.vars)}:{signal.span.lsb.build(self.vars)}]")
        writer.write(f" {signal.id}")
        if not (signal.count.typ == "const" and signal.count.args == 1):
            writer.write(f"[{signal.count.build(self.vars)}]")
        writer.line(suffix)
    
    def build_block(self, writer: Writer, stmt, assign: str):
        if type(stmt) is GenVar:
            self.build_var(writer, stmt, "genvar")
        elif type(stmt) is Integer:
            self.build_var(writer, stmt, "integer")
        elif type(stmt) is Assign:
            writer.line(assign.format(stmt.var, stmt.val.build(self.vars)))
        elif type(stmt) is For:
            writer.line(f"for ({stmt.init.build(self.vars)}; {stmt.cond.build(self.vars)}; {stmt.inc.build(self.vars)}) begin")
            writer.pushIndent()
            for elem in stmt.body:
                self.build_block(writer, elem, assign)
            writer.popIndent()
            writer.line("end")
        elif type(stmt) is While:
            writer.line(f"while ({stmt.cond.build(self.vars)}) begin")
            writer.pushIndent()
            for elem in stmt.body:
                self.build_block(writer, elem, assign)
            writer.popIndent()
            writer.line("end")
        elif type(stmt) is If:
            writer.line(f"if ({stmt.cond.build(self.vars)}) begin")
            writer.pushIndent()
            for elem in stmt.body:
                self.build_block(writer, elem, assign)
            writer.popIndent()
            for entry in stmt.b_elif:
                writer.line(f"end else if ({entry[0].build(self.vars)}) begin")
                writer.pushIndent()
                for elem in entry[1]:
                    self.build_block(writer, elem, assign)
                writer.popIndent()
            if stmt.b_else:
                writer.line("end else begin")
                writer.pushIndent()
                for elem in stmt.b_else:
                    self.build_block(writer, elem, assign)
                writer.popIndent()
            writer.line("end")
        elif callable(stmt):
            stmt(self.vars, writer)
        else:
            raise ValueError(f"Cannot build {type(stmt)} in block")
    
    def build_body(self, writer: Writer, stmt):
        if type(stmt) is Signal:
            self.build_signal(writer, stmt)
        elif type(stmt) is Parameter:
            self.build_param(writer, stmt)
        elif type(stmt) is GenVar:
            self.build_var(writer, stmt, "genvar")
        elif type(stmt) is Integer:
            self.build_var(writer, stmt, "integer")
        elif type(stmt) is Assign:
            writer.line(f"assign {self.vars[stmt.var]} = {stmt.val.build(self.vars)};")
        elif type(stmt) is Block:
            if stmt.clock:
                writer.line(f"always @(posedge {self.vars[stmt.clock]}) begin")
                writer.pushIndent()
                for elem in stmt.body:
                    self.build_block(writer, elem, "{} <= {};")
            else:
                writer.line("always @(*) begin")
                writer.pushIndent()
                for elem in stmt.body:
                    self.build_block(writer, elem, "{} = {};")
            writer.popIndent()
            writer.line("end")
        elif type(stmt) is GenBlock:
            writer.line("generate")
            writer.pushIndent()
            for elem in stmt.body:
                self.build_block(writer, elem, "assign {} = {};")
            writer.popIndent()
            writer.line("endgenerate")
        elif type(stmt) is Instance:
            writer.write(stmt.typ)
            if stmt.params:
                writer.line("#(")
                writer.pushIndent()
                keys = list(stmt.params.keys())
                for i in range(len(keys)):
                    k = keys[i]
                    v = stmt.params[k]
                    writer.write(f".{k}({v if type(v) is str else v.build(self.vars)})")
                    if i < len(stmt.params) - 1:
                        writer.write(",")
                    writer.newline()
                writer.popIndent()
                writer.write(")")
            writer.line(f" {stmt.id} (")
            writer.pushIndent()
            keys = list(stmt.signals.keys())
            for i in range(len(keys)):
                k = keys[i]
                v = stmt.signals[k]
                writer.write(f".{k}({v if type(v) is str else v.build(self.vars)})")
                if i < len(stmt.signals) - 1:
                    writer.write(",")
                writer.newline()
            writer.popIndent()
            writer.line(");")
        elif callable(stmt):
            stmt(self.vars, writer)
        else:
            raise ValueError(f"Cannot build {type(stmt)} in entity body")
    
    def build(self, writer: Writer):
        # Start of definition.
        if self.desc:
            line_comment(writer, self.desc)
        writer.write(f"{self.typ} {self.id}")
        
        # Parameters list.
        if len(self.params):
            writer.line("#(")
            writer.pushIndent()
            for i in range(len(self.params)):
                self.build_param(writer, self.params[i], ',' if i < len(self.params)-1 else '')
            writer.popIndent()
            writer.write(")")
        
        # Port list.
        if len(self.signals):
            writer.line("(")
            writer.pushIndent()
            for i in range(len(self.signals)):
                self.build_signal(writer, self.signals[i], ',' if i < len(self.signals)-1 else '', True)
            writer.popIndent()
            writer.write(")")
        
        # End of definition.
        writer.line(";")
        
        # Body.
        writer.pushIndent()
        for stmt in self.body:
            self.build_body(writer, stmt)
        writer.popIndent()
        
        # End of body.
        writer.line(f"end{self.typ}")
        writer.line()

def line_comment(writer: Writer, text: str):
    for line in text.splitlines():
        writer.line("// " + str(line))

def build_intf(writer: Writer, bus: AsymmetricBus, map: dict):
    if bus.clk.typ == "bus_clock":
        clock = [Signal(bus.clk.sigid, None, Span.default(), Expression("const", 0), "input")]
    else:
        clock = []
    
    def modport(writer: Writer, bus: AsymmetricBus, id: str, map: dict):
        line_comment(writer, f"Signals from {id} perspective.")
        writer.write(f"modport {id} (")
        for i in range(len(bus.signals)):
            writer.write(f"{map[bus.signals[i].dir]} {bus.signals[i].id}")
            if i < len(bus.signals) - 1:
                writer.write(", ")
        writer.line(");")
    
    Entity(
        "interface",
        bus.id,
        bus.desc,
        bus.params,
        clock,
        bus.signals + [
            lambda vars, writer: modport(writer, bus, bus.ctl, {"input": "input", "output": "output"}),
            lambda vars, writer: modport(writer, bus, bus.dev, {"input": "output", "output": "input"})
        ]
    ).build(writer)

def build_active(writer: Writer, ent: ActiveEntity, map: dict):
    Entity("module", ent.id, ent.desc, ent.params, ent.signals, ent.body, ent.vars).build(writer)

def build(writer: Writer, map: dict, id: str):
    if type(map[id]) is AsymmetricBus:
        build_intf(writer, map[id], map)
    elif issubclass(type(map[id]), ActiveEntity):
        build_active(writer, map[id], map)
