#!/usr/bin/env python3

import parser, writer, sysverilog, sys

assert __name__ == "__main__"

raw = parser.read_file("test/bus.yml")
bus = parser.AsymmetricBus.parse("bus_a", raw["bus_a"])
wr  = writer.Writer(sys.stdout)
sysverilog.build_intf(wr, bus)
