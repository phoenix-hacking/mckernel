from pathlib import Path
import ast,hashlib,json
P=Path(__file__).resolve().parent
def function(source,name):
 n=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
 return '\n'.join(source.splitlines()[n.lineno-1:n.end_lineno])+'\n'
old=(P/'preimages/cleanup_pass_image.py').read_text();new=(P/'coupled/cleanup_pass_image.py').read_text()
functions={name:(hashlib.sha256(ast.dump(ast.parse(function(old,name)),include_attributes=False).encode()).hexdigest(),function(new,name)) for name in ('validate_process_report','process_absent','terminal_result','recover','main')}
proc=(P/'proc_v2.py').read_text();sha=hashlib.sha256(proc.encode()).hexdigest()
header='''"""Source-only coupled proc.v2 amendment; no root/runtime actions."""\nimport ast,hashlib\n'''
helper=header+'PROC='+repr(proc)+'\nFUNCTIONS='+repr(functions)+'\n'
helper+='CHECKER_OLD='+repr("'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT, 'process_reports': PROCESS_REPORTS}")+'\nCHECKER_NEW='+repr("'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT}")+'\n'
helper+='''def amend_engine(text):
    tree=ast.parse(text);lines=text.splitlines(keepends=True);changes=[]
    for name,(expected,replacement) in FUNCTIONS.items():
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name]
        if len(nodes)!=1:raise ValueError('amendment function boundary '+name)
        n=nodes[0];actual=ast.dump(ast.Module(body=[n],type_ignores=[]),include_attributes=False)
        if hashlib.sha256(actual.encode()).hexdigest()!=expected:raise ValueError('amendment preimage '+name)
        changes.append((n.lineno-1,n.end_lineno,replacement))
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROC_CODE' for t in n.targets))
    if hashlib.sha256(ast.literal_eval(node.value).encode()).hexdigest()!='24e27a493a84a1ab6c3d22a5248ae456288fa590fc93e31b3fb5a0a29d8659af':raise ValueError('amendment PROC preimage')
    changes.append((node.lineno-1,node.end_lineno,'PROC_CODE = '+repr(PROC)+'\\nPROC_LIMIT = 4 << 20\\nPROCESS_REPORTS = []\\nPROCESS_TOTAL_LIMIT = 16 << 20\\n'))
    for start,end,replacement in sorted(changes,reverse=True):lines[start:end]=[replacement]
    result=''.join(lines)
    result=once(result,"'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT}","'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT, 'process_reports': PROCESS_REPORTS}")
    ast.parse(result);return result

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('amendment exact consumer boundary '+old[:60])
    return text.replace(old,new)
def amend_consumer(name,text):
    if name=='observe_current_pass_image_retirement.py':
        text=once(text,"            raw=out.getvalue().encode();need(len(raw)<=m.LIMIT,'process observation bound')\\n            m.validate_process_report(m.parse(raw),NONCE,caller)\\n            store('process-%02d.json'%len([p for p in OUTPUT.iterdir() if p.name.startswith('process-')]),raw)","            raw=out.getvalue().encode();need(len(raw)<=m.PROC_LIMIT,'process observation bound')\\n            store('process-%02d.json'%len([p for p in OUTPUT.iterdir() if p.name.startswith('process-')]),raw)\\n            m.validate_process_report(m.parse(raw),NONCE,caller)")
    elif name=='check_actual_fresh_preflight.py':
        text=once(text,'result.update(source_sha256=SOURCE_SHA,','result.update(process_reports=m.PROCESS_REPORTS,source_sha256=SOURCE_SHA,')
    elif name=='postjoin_readback.py':
        text=once(text,'members=5,actual_object_rows=actual,','members=5,process_reports=m.PROCESS_REPORTS,actual_object_rows=actual,')
        text=once(text,'    try:return m.census()','    try:return m.census()\\n    except BaseException:\\n        sys.stderr.write(json.dumps(dict(status=\"POSTJOIN_PROCESS_CENSUS_REFUSAL\",process_reports=m.PROCESS_REPORTS),sort_keys=True)+\"\\\\n\");sys.stderr.flush()\\n        raise')
    elif name=='check_current_pass_bodies.py':
        text=once(text,'right=ast.parse(engine)','right=ast.parse(engine.replace('+repr(CHECKER_OLD)+','+repr(CHECKER_NEW)+'))')
        text=text.replace("24e27a493a84a1ab6c3d22a5248ae456288fa590fc93e31b3fb5a0a29d8659af",hashlib.sha256(PROC.encode()).hexdigest())
        text=once(text,"  else:assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name","  else:\\n   if name=='recover':\\n    additions=[n for n in ast.walk(b) if isinstance(n,ast.Dict) and any(isinstance(k,ast.Constant) and k.value=='process_reports' for k in n.keys)]\\n    assert len(additions)==2\\n    for n in additions:\\n     i=next(i for i,k in enumerate(n.keys) if isinstance(k,ast.Constant) and k.value=='process_reports');assert isinstance(n.values[i],ast.Name) and n.values[i].id=='PROCESS_REPORTS';del n.keys[i];del n.values[i]\\n   assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name")
    ast.parse(text);return text
'''
(P/'apply_coupled_amendment.py').write_text(helper)
# Verify source transform reproduces private edits exactly before path pin binding.
ns={};exec(compile(helper,'<source only amendment>','exec'),ns)
assert ns['amend_engine'](old)==new
for name in ('observe_current_pass_image_retirement.py','postjoin_readback.py','check_actual_fresh_preflight.py'):
 assert ns['amend_consumer'](name,(P/'preimages'/name).read_text())==(P/'coupled'/name).read_text(),name
s=(P/'preimages/prepare_existing_current_terminal_sources.FRESH-CORRECTION-1.py').read_text()
ref=dict(path=str(P/'apply_coupled_amendment.py'),sha256=hashlib.sha256(helper.encode()).hexdigest())
needle="    t=b['terminal']; case=json.loads(checked(t['case'])); retirement=json.loads(checked(t['retained_review'])); artifact=json.loads(checked(t['artifact_acceptance']))"
replace=needle+"\n    amendment_raw=pinned(Path("+repr(ref['path'])+"),"+repr(ref['sha256'])+"); amendment={}\n    exec(compile(amendment_raw,'<pinned proc.v2 source amendment>','exec'),amendment)"
assert s.count(needle)==1;s=s.replace(needle,replace)
s=s.replace("    source(p/'cleanup_pass_image.py',engine);", "    engine=amendment['amend_engine'](engine)\n    source(p/'cleanup_pass_image.py',engine);")
s=s.replace("    source(p/'observe_current_pass_image_retirement.py',observer);", "    observer=amendment['amend_consumer']('observe_current_pass_image_retirement.py',observer)\n    source(p/'observe_current_pass_image_retirement.py',observer);")
s=s.replace("        source(p/name,text)","        text=amendment['amend_consumer'](name,text)\n        source(p/name,text)")
ast.parse(s);(P/'coupled/prepare_existing_current_terminal_sources.FRESH-CORRECTION-1.py').write_text(s)
(P/'AMENDMENT-IDENTITY.json').write_text(json.dumps(dict(proc_sha256=sha,amendment=ref,status='SOURCE_ONLY_NO_EXECUTION_RELEASE'),indent=2)+'\n')
