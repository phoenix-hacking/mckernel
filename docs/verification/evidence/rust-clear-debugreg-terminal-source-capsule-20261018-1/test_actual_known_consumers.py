from pathlib import Path
import ast,copy,hashlib,importlib.util,json
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('actual_cleanup',P/'cleanup.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
physical=json.loads((P/'actual-physical-bindings.json').read_bytes());q=m.parse(m.read_bounded(m.REQUEST));m.CANDIDATE=m.image_request_binding(q);obs=dict(candidate_root=m.observe_identity(m.CANDIDATE));selected={str(p):m.observe_identity(p) for p in (m.NAMESPACE/'thin-inputs.json',m.NAMESPACE/'materialization-receipt.json')};checks=[]
m.typed_source_binding(q,obs,selected);checks.append('actual typed source production predicate accepts real manifest receipt request and inode')
for case in ('derivative','materialization','inode','manifest-row','receipt-row'):
 badq=copy.deepcopy(q);bado=copy.deepcopy(obs);bads=copy.deepcopy(selected)
 if case in ('derivative','materialization'):badq['source_derivative_sha256' if case=='derivative' else 'materialization_sha256']='0'*64
 elif case=='inode':bado['candidate_root']['inode']+=1
 else:bads[str(m.NAMESPACE/('thin-inputs.json' if case=='manifest-row' else 'materialization-receipt.json'))]['sha256']='0'*64
 try:m.typed_source_binding(badq,bado,bads)
 except m.Refusal:checks.append('reject typed '+case)
 else:raise AssertionError('accepted bad typed '+case)
target=dict(physical['target'],exit_code=0,image_id=q['image_id']);m.validate_attempt_binding(target,physical['request']);checks.append('actual request and exact owner CID nonce PID start accepts')
for key in ('owner_pid','owner_starttime','container_id'):
 bad=copy.deepcopy(target);bad[key]=bad[key]+1 if key=='owner_pid' else '0'*len(str(bad[key]))
 try:m.validate_attempt_binding(bad,physical['request'])
 except m.Refusal:checks.append('reject target '+key)
 else:raise AssertionError('accepted bad target')
for path,key in ((m.ATTEMPT,'common'),(m.SHARED,'shared')):m.image_record_binding(path,physical[key],m.parse(m.read_bounded(path)),q,target,Path('/proc/sys/kernel/random/boot_id').read_text().strip())
inspection=m.parse(m.read_bounded(Path(physical['terminal_inspection']['path'])));m.EXPECTED_CONTAINER=inspection;m.validate_container_profile(inspection);m.image_receipt_binding(m.parse(m.read_bounded(m.TERMINAL)),m.parse(m.read_bounded(Path(physical['guard']['path']))),target,inspection,physical['owner']['sha256']);checks.append('actual common shared profile owner and guard consumers accept exact retained records')
# Execute exact configure source-join statements in their actual module globals.
n=next(n for n in ast.parse((P/'cleanup.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='configure');start=next(i for i,x in enumerate(n.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='joins' for t in x.targets));end=next(i for i in range(start,len(n.body)) if isinstance(n.body[i],ast.If) and ast.unparse(n.body[i].test).startswith('selected_map[str(ROOT_TERMINAL)]'))
body=n.body[start:end];definition=ast.FunctionDef(name='actual_source_join_body',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='request'),ast.arg(arg='selected_map'),ast.arg(arg='target'),ast.arg(arg='client_rows')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body+[ast.Return(value=ast.Constant(value=True))],decorator_list=[]);program=ast.fix_missing_locations(ast.Module(body=[definition],type_ignores=[]));m.ROOT_TERMINAL=Path(physical['guard']['path']);exec(compile(program,'actual configure source-join statements','exec'),m.__dict__)
rows={r['path']:r for r in physical.values() if isinstance(r,dict) and 'path' in r and 'sha256' in r}
needed=[m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json',m.OUTPUT/'output/build/kernel/mckernel.img',m.OUTPUT/'evidence/artifacts/mckernel.img']+[Path(q[k]) for k in ('driver_path','provenance_path','host_owner_path','source_manifest','toolchain_manifest','gitlink_manifest')]+[Path(x['status_path']) for x in physical['client_ledger']]
rows.update({str(p):m.observe_identity(p) for p in needed});assert m.actual_source_join_body(q,rows,target,physical['client_ledger']);checks.append('actual configure selected real request full source and eight-client joins accepts')
for key in ('host_owner_path','toolchain_manifest'):
 for missing in (True,False):
  bad=copy.deepcopy(rows)
  if missing:del bad[q[key]]
  else:bad[q[key]]['sha256']='0'*64
  try:m.actual_source_join_body(q,bad,target,physical['client_ledger'])
  except m.Refusal:checks.append('reject '+key+(' missing' if missing else ' hash'))
  else:raise AssertionError('bad actual source join accepted')
report=dict(status='PASS_REAL_KNOWN_CONSUMERS_ONLY',checks=checks,source_rows=11,clients=8,root=False,docker=False,copy=False,cleanup=False)
(P/'actual-known-consumer-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status=report['status'],checks=len(checks))))
