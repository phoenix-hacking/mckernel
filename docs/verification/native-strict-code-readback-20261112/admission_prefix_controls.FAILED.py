"""Focused saved-data controls for the one changed strict tool-chain consumer.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No installed namespace, flags/ioctl, subprocess, signal, issuer, account or native
operation. Original actual capsule/tool files are readonly and never rewritten.
Negative cases alter private in-memory copies only, never actual tool evidence.
Rejected worker01a1c48d/turn01a1ce01 collector request remains excluded.
"""
import ast,copy,hashlib,json,os,pathlib,stat,sys
PINS={'reader': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/phase0-usage-correction-1/normal-successor-1/strict-readback-1/admission-prefix-correction-1/readback_code.PROPOSED.py', 'bytes': 30537, 'sha256': '3110ed88d0af616c48450a64c3905dc085b0e7e311fb115a46851d29b20c8b1f'}, 'actual_capture': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/phase0-usage-correction-1/normal-successor-1/normal-operation-1/ROOT-EXEC-COMPLETION.ACTUAL.json', 'bytes': 8556, 'sha256': 'a18089209fb101b6368864d42827daaea828bed9baf3c88c82bf9eda36ddb17a'}, 'legacy_capture': {'path': '/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-graph-fixed30-adoption-publicabi-max-1/receipt-method-correction-1/normal-operation-1/ROOT-EXEC-COMPLETION.ACTUAL.json', 'bytes': 8310, 'sha256': '0ec96c7f198acc029fc2067dd17bf433eeaabb49d90a3b1092202cb873c2942e'}, 'original_initial_tool': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/phase0-usage-correction-1/normal-successor-1/normal-operation-1/ROOT-ACTUAL-EXECUTION-1/ROOT-TOOL-INITIAL.json', 'bytes': 1074, 'sha256': '370908feb10653a37a18b4cd6a1baff06db2b2a5950c3408ad965e62aedf513c'}, 'original_final_tool': {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/phase0-usage-correction-1/normal-successor-1/normal-operation-1/ROOT-ACTUAL-EXECUTION-1/ROOT-TOOL-FINAL.json', 'bytes': 2303, 'sha256': '55e9ebce28e1cb19bf085585939fb0cfe64ea9080a52885e410621cb4ca4954b'}}

def pinned(name):
    row=PINS[name];raw=pathlib.Path(row['path']).read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name+' exact source/input pin'
    return raw

raw=pinned('reader');tree=ast.parse(raw)
assignments={node.targets[0].id:node.value for node in tree.body if isinstance(node,ast.Assign) and
             len(node.targets)==1 and isinstance(node.targets[0],ast.Name)}
names={'need','sha','canon','unique','parse','hex64','ident','stable','Handles','open_exact',
       'read_fd','read_regular','ref','check_tool_chain','retained_info','rethrow'}
selected=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
assert {node.name for node in selected}==names,'exact changed consumer and real readonly/closure dependencies'
actual=json.loads(pinned('actual_capture'));legacy=json.loads(pinned('legacy_capture'))
# Recheck original raw source files; no filtered/recombined tool result is saved.
pinned('original_initial_tool');pinned('original_final_tool')
holders=[]

def namespace(record,historical=False):
    ns={'os':os,'stat':stat,'sys':sys,'json':json,'hashlib':hashlib,'RETAINED_FAILURES':[]}
    for name in ('SCOPE','SCHEMA','LIMIT','ADMISSION_PREFIX','REQUEST_SHA','ISSUER_SHA'):
        ns[name]=ast.literal_eval(assignments[name])
    # The legacy case uses its genuine qualified source-selection values. The
    # changed function and original raw three-line result remain exact.
    ns['HERE']=pathlib.Path(ast.literal_eval(assignments['HERE'].args[0]))
    if historical:
        ns.update(HERE=pathlib.Path(record['argv'][3]).parent,
                  REQUEST_SHA=record['request_sha256'],ISSUER_SHA=record['issuer_sha256'])
    exec(compile(ast.Module(body=selected,type_ignores=[]),PINS['reader']['path'],'exec'),ns)
    real_handles=ns['Handles']
    def tracked_handles():
        value=real_handles();holders.append(value);return value
    ns['Handles']=tracked_handles
    return ns

base=namespace(actual);prefix=base['ADMISSION_PREFIX']['prefix_utf8']
assert actual['tool_calls'][0]['result']['output'].startswith(prefix+'\n'),'exact prefix exists in untouched first response'
results=[]
def closed_since(first):
    for owner in holders[first:]:
        assert owner.close_errors==[] and all(row['state']=='VERIFIED_CLOSED' and row['fd'] is None for row in owner.records),'own provenance descriptors not positively closed'

def run_case(label,record,expected=None,ns=None):
    ns=base if ns is None else ns;first=len(holders)
    try:
        result=ns['check_tool_chain'](record)
    except ValueError as error:
        assert expected is not None and expected in str(error),label+' wrong fixed refusal category'
    else:
        assert expected is None,label+' invalid in-memory fixture accepted'
        expected_records=[json.loads(x) for x in ''.join(row['result']['output'] for row in record['tool_calls']).splitlines()]
        if len(expected_records)==4:expected_records=expected_records[1:]
        assert result==tuple(expected_records),label+' returned caller records differ'
    closed_since(first);results.append({'case':label,'result':'PASS'})

run_case('actual_unmodified_four_line_accept',actual)
run_case('qualified_unmodified_three_line_accept',legacy,ns=namespace(legacy,historical=True))
record=copy.deepcopy(actual)
record['tool_calls'][0]['result']['output']=record['tool_calls'][0]['result']['output'].replace(prefix,prefix.replace('EXEC_ONCE','EXEC_TWICE'),1)
run_case('changed_prefix_bytes_refuse',record,'exact actual Root admission prefix differs')
record=copy.deepcopy(actual);record['tool_calls'][0]['result']['output']=prefix+'\n'+record['tool_calls'][0]['result']['output']
run_case('duplicate_prefix_refuse',record,'full normal Root tool output requires all three actual caller records')
record=copy.deepcopy(actual);value=record['tool_calls'][0]['result']['output']
record['tool_calls'][0]['result']['output']=value[len(prefix)+1:]+prefix+'\n'
run_case('nonfirst_prefix_refuse',record,'exact actual Root admission prefix differs')
record=copy.deepcopy(actual);record['Root_orchestration_source']['sha256']='0'*64
run_case('source_reference_drift_refuse',record,'actual Root prefix source or admission reference differs')
record=copy.deepcopy(actual);record['Root_admission']['sha256']='0'*64
run_case('admission_reference_drift_refuse',record,'actual Root prefix source or admission reference differs')
record=copy.deepcopy(actual);record['actual_preissuer_admission_status']['jobs']=2
run_case('prefix_metadata_drift_refuse',record,'actual Root prefix metadata or original session differs')
real_read=base['read_regular']
try:
    def changed_source(path,handles,*args,**kwargs):
        body,st=real_read(path,handles,*args,**kwargs)
        if path==base['ADMISSION_PREFIX']['source']['path']:body+=b'\n'
        return body,st
    base['read_regular']=changed_source
    run_case('source_content_drift_refuse',copy.deepcopy(actual),'actual Root prefix source bytes or identity differs')
finally:base['read_regular']=real_read
try:
    def changed_admission(path,handles,*args,**kwargs):
        body,st=real_read(path,handles,*args,**kwargs)
        if path==base['ADMISSION_PREFIX']['admission']['path']:body+=b'\n'
        return body,st
    base['read_regular']=changed_admission
    run_case('admission_content_drift_refuse',copy.deepcopy(actual),'actual Root prefix admission bytes or identity differs')
finally:base['read_regular']=real_read
assert len(results)==10,'exact focused control count'
# Saved inputs remain byte-identical after every acceptance/refusal control.
for key in ('actual_capture','legacy_capture','original_initial_tool','original_final_tool'):pinned(key)
print(json.dumps({'kind':'mckernel-strict-reader-exact-admission-prefix-new-controls-v1',
                  'reader_sha256':PINS['reader']['sha256'],'actual_capture_sha256':PINS['actual_capture']['sha256'],
                  'prefix_sha256':base['ADMISSION_PREFIX']['prefix_sha256'],
                  'cases':results,'count':len(results),'original_saved_inputs_unmodified':True,
                  'all_new_provenance_read_handles_positively_closed':True,
                  'installed_namespace_or_producer_native_execution':False,
                  'old24body_suite_replayed':False},sort_keys=True))
