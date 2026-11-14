"""One actual producer/consumer body boundary check, never physical acceptance.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No root/proc/census/Docker/signals/app/producer-main/decoder.project invocation.
"""
import ast,base64,copy,hashlib,json,os,stat,sys
from pathlib import Path
def need(ok,why):
    if not ok:raise AssertionError(why)
def exact(row):
    raw=Path(row['path']).read_bytes();need(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'exact bound source/evidence');return raw
def definitions(raw,names):
    tree=ast.parse(raw);nodes=[copy.deepcopy(n)for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names];need({n.name for n in nodes}==set(names),'actual complete helper selection');return nodes
need(len(sys.argv)==3,'exact bindings path/hash')
raw=Path(sys.argv[1]).read_bytes();need(hashlib.sha256(raw).hexdigest()==sys.argv[2],'binding hash');b=json.loads(raw)
producer=exact(b['producer']);decoder=exact(b['decoder']);pre=json.loads(exact(b['actual_prestate']));exported=json.loads(exact(b['actual_root_receipt_export']))
# Execute the exact actual producer FD reader/formatter, not a rewritten model.
pg=dict(Path=Path,os=os,stat=stat,base64=base64,hashlib=hashlib,json=json,CAP=1<<20,need=need)
exec(compile(ast.fix_missing_locations(ast.Module(body=definitions(producer,['full9','sha','preserved_snapshot','canonical']),type_ignores=[])),b['producer']['path'],'exec'),pg)
dg=dict(Path=Path,base64=base64,hashlib=hashlib,stat=stat,json=json,need=need,FULL9=('device','inode','mode','nlink','uid','gid','size','mtime_ns','ctime_ns'))
exec(compile(ast.fix_missing_locations(ast.Module(body=definitions(decoder,['raw_original','root_proof_bytes']),type_ignores=[])),b['decoder']['path'],'exec'),dg)
source_rows=pre['transaction_paths']+[pre['cleanup_source'],pre['release']];need(len(source_rows)==len({r['path']for r in source_rows})==9,'genuine nine inputs');wire=[]
for row in source_rows:
    need(row['stable_full9']is True and row['named_before']==row['fd_before']==row['fd_after']==row['named_after'] and row['bytes']==row['fd_before']['size'],'authenticated actual prestate full9/byte count')
    if row['kind']=='regular':
        expected=base64.b64decode(row['raw_base64'],validate=True);need(row['raw_complete']is True and len(expected)==row['bytes'] and hashlib.sha256(expected).hexdigest()==row['sha256'],'authenticated actual retained bytes')
    else:
        need(row['kind']=='regular_hash_only' and row['path'].endswith('/numa-insert-clear-image-terminal-20261021-1.docker-logs.capture') and 'raw_base64'not in row,'exact observed hash-only log row');expected=None
    actual,observed=pg['preserved_snapshot'](dict(path=row['path'],sha256=row['sha256'],full9=row['fd_before']),export=True)
    need(len(observed)==row['bytes'] and hashlib.sha256(observed).hexdigest()==row['sha256'] and actual['full9']==row['fd_before'],'actual producer FD/full9/retained hash join')
    if expected is not None:need(observed==expected,'actual producer and retained complete bytes')
    need(dg['raw_original'](actual,actual['raw_base64'])==observed,'actual decoder nested full9/raw bytes')
    wire.append(actual)
# Execute the exact actual decoder nine-row predicate too: UID/GID come from
# the genuine current files, never a fictional root-owned fixture.
project=next(n for n in ast.parse(decoder).body if isinstance(n,ast.FunctionDef)and n.name=='project')
loops=[n for n in project.body if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='row'and any(isinstance(k,ast.Constant)and k.value=='full9 original preservation'for k in ast.walk(n))]
need(len(loops)==1,'unique actual preservation predicate');dg['rows']=wire
exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(loops[0])],type_ignores=[])),b['decoder']['path'],'exec'),dg)
need(exported['status']=='PASS_READ_ONLY_TWO_RECEIPTS','actual two receipt export');proofs={};refs=[]
for role in ('prepared','complete'):
    row=exported[role];need(row['status']=='PASS_EXACT_ROOT_RECEIPT_READ_ONLY' and row['stable_full9']is True and row['named_before']==row['fd_before']==row['fd_after']==row['named_after'],'genuine root receipt full9')
    desc={k:row[k]for k in ('path','sha256','bytes')};proofs[desc['path']]=dict(desc,raw_base64=row['raw_base64']);refs.append(desc)
    need(dg['root_proof_bytes']({'evidence_raw_exports':proofs},desc)==base64.b64decode(row['raw_base64'],validate=True),'actual decoder root export, no original open')
need(refs[1]['sha256']=='2dc61852874e32c0c3bd706e2175e150abcbb35a4cbdb63a70ce3a8cd7be9067','genuine complete authority')
# Real producer canonical formatter includes LF; compare the exact same
# source-level convention against authenticated actual plan/release values.
for row in source_rows:
    if row.get('json_parse') is not None and row['path'].endswith(('.json','.plan.json')):
        value=json.loads(base64.b64decode(row['raw_base64'],validate=True));need(pg['canonical'](value)==json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n','actual canonical LF formatter')
print(json.dumps(dict(status='PASS_ACTUAL_NINE_INPUT_PRODUCER_TO_DECODER_AND_TWO_ROOT_EXPORT_HELPERS_ONLY',actual_preserved_rows=len(wire),actual_root_receipts=len(refs),producer=b['producer'],decoder=b['decoder'],physical_acceptance=False,guest_runs=0,root_operations=0,mutation=False,producer_main_called=False,physical_project_called=False),sort_keys=True))
