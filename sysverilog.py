
import parser, builder

def o_sqrt(x):  return "$sqrt(" + x + ")"
def o_clog2(x): return "$clog2(" + x + ")"
def o_not(x):   return "!" + x
def o_and(x):   return "&&" + x
def o_or(x):    return "||" + x

def line_comment(writer: builder.Writer, text: str):
    for line in text.splitlines():
        writer.line("// " + line)

def build_intf(writer: builder.Writer, id: str, bus: parser.AsymmetricBus):
    if bus.desc: line_comment(writer, bus.desc)
    if bus.clk.typ == "bus_clock":
        writer.line(f"interface {id}(")
        writer.pushIndent()
        writer.popIndent()
        writer.line(");")
    else:
        writer.line(f"interface {id};")
    writer.line("endinterface")
