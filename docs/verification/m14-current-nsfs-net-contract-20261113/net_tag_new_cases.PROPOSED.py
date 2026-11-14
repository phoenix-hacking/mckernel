#!/usr/bin/python3
import ast,hashlib,json,pathlib,re
HERE=pathlib.Path(__file__).resolve().parent
GRAPH=HERE/'graph_observations.PROPOSED.py'
GRAPH_SHA='f0771de86d894f93639aba401f83e2e1595db5d63b642962db4e8b3735a1b06e'
EVIDENCE=HERE/'CURRENT-ROW-AND-PLATFORM.CONTRACT.json'
EVIDENCE_SHA='0a3b3a1be548f9448799f52d9b709b64d7e42e2bde05f9f5158457262269f17c'
NAMES={'require','decode_path','_mount_covers','MountTable','parse_mountinfo'}

def digest(raw):return hashlib.sha256(raw).hexdigest()

def changed_row(raw,index,replacements):
    rows=[line.split(' ') for line in raw.decode().splitlines()]
    for key,value in replacements.items():rows[index][key]=value
    return ('\n'.join(' '.join(row) for row in rows)+'\n').encode()

def main():
    source=GRAPH.read_bytes();assert digest(source)==GRAPH_SHA
    evidence_raw=EVIDENCE.read_bytes();assert digest(evidence_raw)==EVIDENCE_SHA
    evidence=json.loads(evidence_raw);row=evidence['exact_actual_CURRENT_row']
    assert row['row_1based']==92 and row['root_field']=='net:[4026531840]' and row['mountpoint_field']=='/run/docker/netns/default' and row['fstype']=='nsfs'
    tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in NAMES]
    assert len(nodes)==len(NAMES) and {n.name for n in nodes}==NAMES
    namespace={'__name__':'actual_net_nsfs_pure_parser_projection','re':re,'PurePosixPath':pathlib.PurePosixPath}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(GRAPH),'exec'),namespace)
    parse=namespace['parse_mountinfo']
    # IDs,parent,device,access/source are synthetic framing, NOT actual saved row.
    fields=['2','1','0:4',row['root_field'],row['mountpoint_field'],'rw','-','nsfs','nsfs','rw']
    raw=('1 1 8:1 / / rw - ext4 /dev/fixture rw\n'+' '.join(fields)+'\n').encode()
    expected_fields=[tuple(x.split(' ')) for x in raw.decode().splitlines()]
    observations=[]
    table=parse(raw)
    assert sorted(table.by_id)==[1,2] and list(table.all_rows)==expected_fields
    assert table.by_id[2]['root']==row['root_decoded'] and table.by_id[2]['point']==row['mountpoint_decoded']
    assert table.resolve(row['mountpoint_decoded'])['mount_id']==2
    assert table[row['mountpoint_decoded']]=={'mount_id':2,'parent_mount_id':1,'access':'rw'}
    observations.append({'id':'actual-current-net-operands-derived-fixture-all-fields-and-covering','result':'PASS'})
    for name,value in [('net-min-positive','net:[1]'),('net-max-uint32','net:[4294967295]')]:
        changed=parse(changed_row(raw,1,{3:value}));assert len(changed.by_id)==2 and changed.by_id[2]['root']==value
        observations.append({'id':name,'result':'PASS'})
    cases=[('net-zero',{3:'net:[0]'},'mount path fields'),('net-leading-zero',{3:'net:[01]'},'mount path fields'),('net-negative',{3:'net:[-1]'},'mount path fields'),('net-uint32-overflow',{3:'net:[4294967296]'},'mount path fields'),('net-trailing-text',{3:'net:[1]x'},'mount path fields'),('other-unqualified-tag',{3:'pid:[1]'},'mount path fields'),('net-root-on-ordinary-filesystem',{7:'tmpfs'},'mount path fields'),('net-relative-covering-point',{4:'run/docker/netns/default'},'mount path fields'),('net-invalid-device',{2:'0:x'},'mount device fields'),('net-ambiguous-access',{5:'ro,rw'},'ambiguous mount access')]
    for name,replacements,message in cases:
        try:parse(changed_row(raw,1,replacements))
        except ValueError as error:assert str(error)==message,(name,type(error).__name__,str(error))
        else:raise AssertionError((name,'unexpected acceptance'))
        observations.append({'id':name,'result':'REFUSED','message':message})
    expected=json.loads((HERE/'EXPECTED-NEW-CONTROLS.DATA.json').read_bytes())
    assert observations==expected['observations']
    assert digest(GRAPH.read_bytes())==GRAPH_SHA and digest(EVIDENCE.read_bytes())==EVIDENCE_SHA
    print(json.dumps({'scope':'NEW_CURRENT_NET_TAG_PURE_CONTROLS_ONLY','source_sha256':GRAPH_SHA,'evidence_sha256':EVIDENCE_SHA,'observations':observations,'fixture_is_actual_operands_with_synthetic_framing_not_actual_rawrow':True,'old21_or_other_green_suites_rerun':False,'failedinstant_cause_or_native_ownership_or_acceptance_proved':False},sort_keys=True))

if __name__=='__main__':main()
