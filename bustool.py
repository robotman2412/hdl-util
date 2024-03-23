#!/usr/bin/env python3

import parser, writer, sysverilog, sys, argparse

def make_writer(path: str):
    if path == '-':
        return writer.Writer(sys.stdout)
    else:
        return writer.Writer(open(path), lambda x: x.fd.close())

def run(outfile: str, srcfile: str):
    map = parser.parse_file(srcfile)
    with make_writer(outfile) as wr:
        for id in map:
            map[id].generate()
            sysverilog.build(wr, map, id)

if __name__ == "__main__":
    ap = argparse.ArgumentParser("bustool.py")
    ap.add_argument("--outfile", "-o", action="store", help="The file to output to, - is stdout", default="-")
    ap.add_argument("srcfile", action="store", help="The bus definition file to process.")
    args = ap.parse_args()
    run(args.outfile, args.srcfile)
