
class Writer:
    def __init__(self, fd, onclose = None, indent = "    ", lftype = "\n"):
        self.fd      = fd
        self.onclose = onclose
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
        self.fd.write(self.indent * self.level)
        self.fd.write(self.curLine)
        self.fd.write(self.lftype)
        self.curLine = ""
    
    def line(self, text=""):
        self.write(text)
        self.newline()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.onclose: self.onclose(self)
