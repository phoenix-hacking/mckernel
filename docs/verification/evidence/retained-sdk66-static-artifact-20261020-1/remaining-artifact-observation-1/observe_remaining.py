"""Read-only remaining artifact observation. Never imports execution code or starts tools."""
import ast,hashlib,json,re,shlex,stat,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
N=HERE.parent
DRIVER_SHA='c08b212ccf80084d4951998f95a40f36082cb7b05ff1f68589e4239de57e53d1'
RECEIPT_SHA='52fb7eaf42a02937c182ccb014661b1bb7781b40bd539896952bd0c8aac9ea34'

def main():
    out=HERE/'output'
    assert not out.exists()
    qraw=(N/'request.json').read_bytes()
    assert hashlib.sha256(qraw).hexdigest()=='0eadaeb0f92725889ad3735af17816552e43b1d4316528f63335788e1fb42c42'
    q=json.loads(qraw)
    candidate=Path(q['candidate_root']);inputs=Path(q['input_root'])
    driver=Path(q['driver']['path']);raw=driver.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==DRIVER_SHA==q['driver']['sha256']
    rp=candidate/'evidence/receipt.json';rraw=rp.read_bytes()
    assert hashlib.sha256(rraw).hexdigest()==RECEIPT_SHA
    receipt=json.loads(rraw)
    assert receipt['status']=='FAIL' and receipt['make_returncode']==0
    assert receipt['error']=='ValueError: MM provider D/U mismatch: mcctrl_rust.o:mckernel_inherited_mmap_write_lock'
    tree=ast.parse(raw)
    names={'require','digest','plain','relative_path','files','closure','modinfo','source_bindings','module_order','provider_symbols','actual_mm_provider_check','outputs'}
    constants={'MODULES','MM_BRIDGES','RELEASE','KERNEL'}
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:
            if node.name=='actual_mm_provider_check':
                text=ast.get_source_segment(raw.decode(),node)
                before='if (defs,undefs)!=(expected_defs,expected_undefs):'
                after='if (defs,undefs)!=(expected_defs, (1 if symbol == "mckernel_inherited_mmap_write_unlock" else 0) if name == "mcctrl_rust.o" else expected_undefs):'
                assert text.count(before)==1
                node=ast.parse(text.replace(before,after)).body[0]
            nodes.append(node)
        elif isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in constants:
            ast.literal_eval(node.value);nodes.append(node)
    assert {n.name for n in nodes if isinstance(n,ast.FunctionDef)}==names
    ns=dict(Path=Path,hashlib=hashlib,json=json,re=re,shlex=shlex,stat=stat,struct=struct)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned-pure-artifact-parsers>','exec'),ns)
    actual=ns['files'](candidate/'modules')
    assert set(actual)==set(receipt['retained_files'])
    for name,pin in receipt['retained_files'].items():
        p=actual[name];assert set(pin)=={'bytes','sha256'}
        assert p.stat().st_nlink==1 and p.stat().st_size==pin['bytes'] and ns['digest'](p)==pin['sha256']
    # Actual input rows are pinned too; no build/toolchain copies or command execution.
    mraw=(N/'materialization-files.json').read_bytes()
    assert hashlib.sha256(mraw).hexdigest()=='c78fb81c62dc544d439770b7b42077962bbb560a77e53b9e80124498d62e184f'
    rows=json.loads(mraw);assert len(rows)==81
    for row in rows:
        p=Path(row['destination']);pin=row['source']
        assert p.stat().st_nlink==1 and p.stat().st_size==pin['bytes'] and ns['digest'](p)==pin['sha256']
    praw=Path(q['preparation']['path']).read_bytes()
    assert hashlib.sha256(praw).hexdigest()=='f642daedc6c3fbbb3b46b98860ca745e83856d258e8a36a225d31f8b987711ea'==q['preparation']['sha256']
    manifest=json.loads(praw)
    ns['closure'](manifest,candidate)
    artifacts=ns['outputs'](candidate,inputs)
    report=dict(status='PASS_REMAINING_ARTIFACT_OBSERVATION_ONLY',original_driver_status='FAIL_PRESERVED',driver_sha256=DRIVER_SHA,receipt_sha256=RECEIPT_SHA,retained_files=len(actual),materialization_rows=len(rows),artifacts=artifacts,explicit_rust_leaf_undefined_vector={'mckernel_inherited_mmap_write_lock':0,'mckernel_inherited_mmap_write_unlock':1,'mckernel_inherited_vma_start_write':0},limitations=['Dormant host non-null CREATE_PPD/adopt candidate/private paths remain unselected or EOPNOTSUPP; no default consumer proof.','lock/vma absent Rust references do not establish live MM operation; unlock reference is only static linkage evidence.','No positive CREATE_PPD, MM operation, guest/native, default activation, ACK, production or compute-C retirement acceptance.'],application_acceptance=False,production_acceptance=False,default_consumer_acceptance=False,native_acceptance=False,compiler_calls=0)
    # All reads and predicates finish before the only new output mutation.
    out.mkdir(mode=0o700)
    with (out/'report.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(status=report['status'],retained_files=len(actual),modules=len(artifacts),report_sha256=ns['digest'](out/'report.json'))))
if __name__=='__main__':main()
