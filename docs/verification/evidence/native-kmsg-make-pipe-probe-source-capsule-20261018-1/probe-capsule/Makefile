# Private tool-only recursive jobserver probe. No target compiler or Linux make.
.PHONY: all branch_a branch_b child_a child_b
all: branch_a branch_b
branch_a:
	+$(MAKE) --no-print-directory -f /probe/Makefile child_a
branch_b:
	+$(MAKE) --no-print-directory -f /probe/Makefile child_b
child_a:
	+/usr/bin/python3 /probe/probe.py --child a
child_b:
	+/usr/bin/python3 /probe/probe.py --child b
