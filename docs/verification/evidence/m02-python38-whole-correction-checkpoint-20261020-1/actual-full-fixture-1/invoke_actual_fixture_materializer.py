from pathlib import Path
import importlib.util,json,sys
sys.dont_write_bytecode=True
p=Path(__file__).resolve().parent/'current-sources'
s=importlib.util.spec_from_file_location('actual_fixture_materializer',p/'materialize_current_m02_once.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
c=json.loads((p/'CURRENT-SOURCE-CONTEXT.json').read_bytes())
m.materialize(c,dict(path=None,sha256=None,bytes=None),None,True)
