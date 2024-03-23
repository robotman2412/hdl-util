
from parser import *
from writer import *

class Entity:
    def __init__(self, typ: str, id: str, desc: str, params: list[Parameter], signals: list[Signal], body: list):
        self.typ     = typ
        self.id      = id
        self.desc    = desc
        self.params  = params
        self.signals = signals
        self.body    = body
        self.vars    = {}
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
    
    def build_param(self, writer: Writer, param: Parameter, suffix: str = ';'):
        if param.desc:
            line_comment(writer, param.desc)
        writer.line(f"parameter {param.id} = {param.default}{suffix}")
    
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
        writer.write(f" {signal.id}{suffix}")
        if type(signal) is BusInstance:
            if not (signal.count.typ == "const" and signal.count.args == 1):
                writer.write(f"[{signal.count.build(self.vars)}]")
        writer.newline()
    
    def build_body(self, writer: Writer, stmt: Signal|Parameter):
        if type(stmt) is Signal:
            self.build_signal(writer, stmt)
        elif type(stmt) is Parameter:
            self.build_param(writer, stmt)
        elif type(stmt) is Assign:
            writer.line(f"assign {self.vars[stmt.var]} = {stmt.val.build(self.vars)};")
        elif type(stmt) is Block:
            if stmt.clock:
                writer.line(f"always @(posedge {self.vars[stmt.clock]}) begin")
            else:
                writer.line("always @(*) begin")
            writer.line("end")
        elif callable(stmt):
            stmt(writer)
        else:
            stmt.build(writer)
    
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
            lambda writer: modport(writer, bus, bus.ctl, {"input": "input", "output": "output"}),
            lambda writer: modport(writer, bus, bus.dev, {"input": "output", "output": "input"})
        ]
    ).build(writer)

def build_active(writer: Writer, ent: ActiveEntity, map: dict):
    Entity("module", ent.id, ent.desc, ent.params, ent.signals, ent.body).build(writer)

def build(writer: Writer, map: dict, id: str):
    if type(map[id]) is AsymmetricBus:
        build_intf(writer, map[id], map)
    elif issubclass(type(map[id]), ActiveEntity):
        build_active(writer, map[id], map)
