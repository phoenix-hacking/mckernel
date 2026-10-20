from pathlib import Path
import importlib.util,json,sys
sys.dont_write_bytecode=True
p=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('fixture_must_not_be_production',p/'current-sources/root_manual_snapshot_m03.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=json.loads((p/'native-control-packet-fixture/ROOT-SNAPSHOT-BINDINGS.json').read_bytes())
m.static_joins(b)
