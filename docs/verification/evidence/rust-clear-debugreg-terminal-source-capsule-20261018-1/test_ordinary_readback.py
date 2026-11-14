import importlib.util,json,tempfile,types
from pathlib import Path
P=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('ordinary',P/'ordinary_readback.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
summary=m.module();assert m.observe(summary)['status']=='PENDING_ORDINARY_READABILITY'
with tempfile.TemporaryDirectory(dir=P) as d:
 paths=Path(d)
 for name in summary.NAMES:(paths/name).write_text('{}')
 calls=[]
 fake=types.SimpleNamespace(OUTPUT=paths,NAMES=summary.NAMES,read_all=lambda:calls.append('stable-read') or {},summarize=lambda raw:calls.append('actual-consumer') or {'status':'fixture'},canonical=summary.canonical)
 assert m.observe(fake)=={'status':'fixture'} and calls==['stable-read','actual-consumer']
 (paths/summary.NAMES[0]).unlink();calls.clear()
 assert m.observe(fake)['status']=='PENDING_ORDINARY_READABILITY' and not calls
print(json.dumps(dict(status='PASS_CONDITIONAL_READBACK',positive=1,refusals=2)))
