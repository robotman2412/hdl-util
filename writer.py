
class Writer:
    def __init__(self, fd, indent = "    ", lftype = "\n"):
        self.fd      = fd
        self.indent  = indent
        self.level   = 0
        self.lftype  = lftype
        self.curLine = ""
    
    def pushIndent(self):
        self.level += 1
    
    def popIndent(self):
        self.level -= 1
    
    def write(self, text):
        self.curLine += str(text)
    
    def newline(self):
        if len(self.curLine):
            self.fd.write(self.indent * self.level)
            self.fd.write(self.curLine)
            self.fd.write(self.lftype)
        self.curLine = ""
    
    def line(self, text):
        self.write(text)
        self.newline()
