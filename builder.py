
import sysverilog

def builder():
    return sysverilog

def o_sqrt(x):  return builder().o_sqrt(x)
def o_clog2(x): return builder().o_clog2(x)
def o_not(x):   return builder().o_not(x)
def o_and(x):   return builder().o_and(x)
def o_or(x):    return builder().o_or(x)

class Writer:
    def __init__(self, fd, indent = "    ", newline = "\n"):
        self.fd      = fd
        self.indent  = indent
        self.level   = 0
        self.newline = newline
    
    def pushIndent(self):
        self.indent += 1
    
    def popIndent(self):
        self.indent -= 1
    
    def line(self, text):
        self.fd.write(self.indent * self.level)
        self.fd.write(text)
        self.fd.write(self.newline)
