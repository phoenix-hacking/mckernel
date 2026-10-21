#!/usr/bin/env python3
"""Existing finite runtime binding transaction, late instance DATA only.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Never imports/runs candidate code, snapshot, owner, compiler, guest or root commands.
Root grants ordinary source binding only after actual independent physical review.
"""
from pathlib import Path
import argparse, ast, hashlib, json, os, stat

D=Path(__file__).resolve().parent
OUT=D/'physical-bound-1'
CODE=('bind_numa_native_packet.py','root_manual_snapshot_threads.py',
      'current_numa_image_physical.py','check_current_whole_caller.py',
      'native-packet-1/review_final_threads_release.py',
      'native-packet-1/root-run-exact-readonly-stage.py')
FD_FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def need(ok,why):
    if not ok: raise ValueError(why)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def ref(p):
    p=Path(p); raw=p.read_bytes(); return dict(path=str(p),sha256=sha(raw),bytes=len(raw))
def checked(row):
    need(type(row) is dict and set(row)=={'path','sha256','bytes'} and row['path'] is not None,'genuine late reference pending')
    need(ref(row['path'])==row,'exact actual selected bytes: '+str(row['path']))
    return json.loads(Path(row['path']).read_bytes())
def write(p,raw):
    with p.open('xb') as stream: stream.write(raw)
    p.chmod(0o600)
def js(p,value): write(p,(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
def bind_global(text,value):
    tree=ast.parse(text)
    nodes=[n for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='EXPECTED_INSTANCE']
    need(len(nodes)==1 and ast.literal_eval(nodes[0].value) is None,'one pending instance literal')
    node=nodes[0]; lines=text.splitlines(keepends=True); lines[node.lineno-1:node.end_lineno]=['EXPECTED_INSTANCE = '+repr(value)+'\n']; bound=''.join(lines)
    functions=lambda source:[ast.dump(n,include_attributes=False) for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
    need(functions(text)==functions(bound),'all reviewed decoder functions/classes immutable')
    return bound

def main():
    ap=argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--bindings',required=True); ap.add_argument('--bindings-sha256',required=True)
    args=ap.parse_args(); raw=Path(args.bindings).read_bytes()
    need(sha(raw)==args.bindings_sha256,'exact root-bound late DATA')
    binding=json.loads(raw); need(set(binding)=={'physical_mapping','physical_report'},'only two genuine late authority refs')
    mapping=checked(binding['physical_mapping']); report=checked(binding['physical_report'])
    need(mapping['schema']=='mckernel.current-numa-image.known-kind-physical-consumer-mapping.v1' and mapping['status']=='PASS_INDEPENDENT_CURRENT_NUMA_PHYSICAL_REPORT_MAPPING' and mapping['implementation_ownership'] is False and mapping['reviewer'],'actual independent mapping')
    authorities=mapping['genuine_current_authorities']
    need(authorities['original_physical']==binding['physical_report'],'actual report/mapping join')
    need(report['schema']=='mckernel.independent-current-numa-image-cleanup-physical-release-review.v1' and report['status']=='PASS_ACTUAL_CURRENT_NUMA_IMAGE_CLEANUP_POSTJOIN_AND_POSITIVE_PHYSICAL_RETIREMENT' and report['decision']=='PASS_POSITIVE_CURRENT_NUMA_IMAGE_OWNER_AND_RECORD_RETIREMENT','qualified actual current physical report kind')
    for name in ('physical_release','retired','record_release_complete','terminal','container_absent','common_shared_records_absent','owned_inner_groups_empty','controller_terminal','root_mutex_available'):
        need(report[name] is True,'positive actual '+name)
    need(report['lease_retained'] is False and report['implementation_ownership'] is False,'physical report scope')
    for name in ('native_acceptance','runtime_acceptance','application_acceptance'):
        need(report[name] is False,'no fabricated native/application acceptance')
    controller=mapping['controller_terminal_contract']
    need(controller['kind']=='tool-owned-unified-exec-terminal' and controller['decision']=='PASS_TOOL_TERMINAL_AND_SINGLE_CHILD_CONTROL_FLOW' and controller['implementation_ownership'] is False and controller['reviewer'],'same qualified tool-owned controller representation')
    pairs=authorities['controller_terminal_receipts']
    need(pairs==report['controller_terminal_receipts'] and [pair['role'] for pair in pairs]==['cleanup','postjoin'] and len(report['positive_closed_births'])==2,'exact raw pairs and TWO observed innerbirths')
    expected={}
    for pair in pairs:
        first=checked(pair['started']); last=checked(pair['completed'])
        need(first['event']['method']=='item/started' and last['event']['method']=='item/completed','genuine raw protocol event kinds')
        a=first['event']['params']['item']; z=last['event']['params']['item']
        need(all(a[key]==z[key] for key in ('type','id','command','cwd','processId','source','commandActions')),'exact start/completion identity')
        need(z['type']=='commandExecution' and z['source']=='unifiedExecStartup' and z['status']=='completed' and type(z['exitCode']) is int and z['exitCode']==0,'genuine tool terminal0')
        expected[pair['role']]=(z['id'],z['processId'],z['durationMs'])
    counts=mapping['current_actual_counts']
    instance=dict(mapping=binding['physical_mapping'],physical_report=binding['physical_report'],tool_terminals=expected,execution_review_sha256=authorities['execution_review']['sha256'],cleanup_engine_sha256=authorities['source_cleanup_engine']['sha256'],selected_files=counts['selected_files'],objects=counts['postreader_actual_objects'],roles=counts['finite_roles'])
    # Preserve the frozen bodies; bind exactly one declared top-level literal.
    freeze=json.loads((D/'RUNTIME-BODY-FREEZE.json').read_bytes())
    pinned={row['path']:row for row in freeze['files']}
    need(not os.path.lexists(OUT),'fresh final source/data namespace')
    prepared={}
    for name in CODE:
        path=D/name; need(ref(path)==pinned[str(path)],'frozen body source drift '+name)
        text=path.read_text()
        if name=='current_numa_image_physical.py': text=bind_global(text,instance)
        prepared[name]=text.encode()
    config_path=D/'STATIC-NONTEMPORAL-INPUTS.PENDING-PHYSICAL.json'
    need(ref(config_path)==pinned[str(config_path)],'accepted normalization DATA drift')
    cfg=json.loads(config_path.read_bytes())
    cfg.update(latest_physical=binding['physical_report'],physical_consumer_mapping=binding['physical_mapping'],status='ACTUAL_CURRENT_NORMALIZATION_AND_PHYSICAL_MAPPING_BOUND_NO_RUNTIME_RELEASE')
    OUT.mkdir(mode=0o700); (OUT/'native-packet-1').mkdir(mode=0o700)
    for name,raw in prepared.items(): write(OUT/name,raw)
    js(OUT/'STATIC-NONTEMPORAL-INPUTS.json',cfg)
    js(OUT/'CURRENT-PHYSICAL-MAPPING-BINDING.json',binding['physical_mapping'])
    js(OUT/'CURRENT-PHYSICAL-COMPANION-ACCEPTANCE.json',binding['physical_mapping'])
    js(OUT/'CURRENT-PHYSICAL-DECODER-SOURCE.json',ref(OUT/'current_numa_image_physical.py'))
    qualified=cfg['runtime_source_refs']
    need(len(qualified)==6 and len({row['path'] for row in qualified})==6,'complete qualified SIX source references')
    expected_hashes={row['path']:row['sha256'] for row in qualified}
    expected_hashes.update({str(OUT/name):ref(OUT/name)['sha256'] for name in ('root_manual_snapshot_threads.py','current_numa_image_physical.py')})
    need(len(expected_hashes)==8,'complete EIGHT selected runtime sources')
    identities={}
    for name,expected_sha in expected_hashes.items():
        path=Path(name); fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        try:
            before=os.fstat(fd); digest=hashlib.sha256()
            while True:
                chunk=os.read(fd,1<<20)
                if not chunk: break
                digest.update(chunk)
            after=os.fstat(fd); named=path.lstat()
            need(stat.S_ISREG(before.st_mode) and all(getattr(before,key)==getattr(after,key)==getattr(named,key) for key in FD_FIELDS),'complete stable source full9 FD '+name)
            need(digest.hexdigest()==expected_sha,'selected genuine source hash '+name)
            identities[name]={key:getattr(before,key) for key in FD_FIELDS}
        finally: os.close(fd)
    js(OUT/'RUNTIME-SOURCE-FD-IDENTITIES.json',dict(schema='mckernel.current-native.selected-runtime-source-full-fd-identities.v1',identities=identities))
    names=list(CODE)+['STATIC-NONTEMPORAL-INPUTS.json','RUNTIME-SOURCE-FD-IDENTITIES.json','CURRENT-PHYSICAL-MAPPING-BINDING.json','CURRENT-PHYSICAL-COMPANION-ACCEPTANCE.json','CURRENT-PHYSICAL-DECODER-SOURCE.json']
    js(OUT/'CHECK-INPUT-PINS.json',[ref(OUT/name) for name in names]+[binding['physical_mapping'],binding['physical_report']])
    js(OUT/'BOUND-SOURCE-DATA-REFS.json',dict(status='SOURCE_AND_ACTUAL_DATA_BOUND_ONLY_NO_RUNTIME_RELEASE',files=[ref(OUT/name) for name in names+['CHECK-INPUT-PINS.json']],late_authorities=binding))
    print(json.dumps(ref(OUT/'BOUND-SOURCE-DATA-REFS.json'),sort_keys=True))
if __name__=='__main__': main()
