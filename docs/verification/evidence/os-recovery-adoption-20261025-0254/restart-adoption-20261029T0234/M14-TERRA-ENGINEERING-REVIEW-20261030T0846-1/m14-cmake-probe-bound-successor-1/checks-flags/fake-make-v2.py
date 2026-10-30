#!/usr/bin/python3
import os,pathlib,sys
if sys.argv[1:] == ["--version"]:
 pathlib.Path(os.environ["MOCK_VERSION_MARKER"]).write_text("yes")
 print("Other Make" if os.environ["MOCK_MODE"]=="notgnu" else "GNU Make 4.4")
 sys.exit(0)
p=pathlib.Path(sys.argv[sys.argv.index("-C")+1]);(p/"make-called").write_text("yes")
mode=os.environ["MOCK_MODE"]
if mode in ("success","fail","wrongmap"): (p/"driver.ko").write_bytes(bytes.fromhex(os.environ["MOCK_ELF"]))
if mode=="fail": sys.exit(7)
