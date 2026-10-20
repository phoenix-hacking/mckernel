"""One child tuple join using the accepted c807 namespace-selection pattern.
No writer, root caller, owner, backend, snapshot or materializer is invoked.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,stat
TUPLE = {'path': '/home/holden/mckernel-work/host-preparation/phase5-child-actual-stage-normalization-20261020-1/runtime-data-preparation-1/CHILD-WHOLE-TUPLE.json', 'sha256': '94e312658ec1b5528a4a9b90104c586b1b5cb9849ebf2dc85a9196b82147db26', 'size': 100691, 'mode': 33152}
CONTRACT = {'path': '/home/holden/mckernel-work/host-preparation/phase5-child-actual-stage-normalization-20261020-1/runtime-data-preparation-1/source/child_normalization_contract.py', 'sha256': '88fc53c733ede1645c5786eba6e5cd3bcafbff8804b07b5aca5bffe9bc017bbd', 'size': 4057, 'mode': 33152}
STABLE=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

def exact(row):
    assert type(row)is dict and set(row)=={'path','sha256','size','mode'}
    p=Path(row['path']);assert p.is_absolute()and p.resolve()==p
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,'rb')as f:
        a=os.fstat(f.fileno());assert stat.S_ISREG(a.st_mode)and a.st_mode==row['mode']and a.st_size==row['size']and a.st_size<=4<<20
        raw=f.read((4<<20)+1);b=os.fstat(f.fileno());c=p.lstat();assert all(getattr(a,k)==getattr(b,k)==getattr(c,k)for k in STABLE)
    assert len(raw)==row['size']and hashlib.sha256(raw).hexdigest()==row['sha256'];return raw

def select():
    t=json.loads(exact(TUPLE));exact(CONTRACT)
    spec=importlib.util.spec_from_file_location('genuine_child_normalization_contract',CONTRACT['path']);contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    role=contract.validate(t['actual_normalization_acceptance'],t['raw_artifact_authority']);pre=role['preflight'];binding=role['binding']
    assert t['binding']==binding==pre['binding']and t['whole_manifest']==role['manifest']
    assert t['normalized_manifest']==dict(path=binding['manifest']['path'],sha256=binding['manifest']['sha256'],size=binding['manifest']['size'],mode=binding['manifest']['mode'])
    parent=Path(binding['attempt_parent']);state=parent.lstat();assert not list(parent.iterdir())and all(getattr(state,k)==v for k,v in t['parent']['nine_field_identity'].items())
    assert t['parent']['nine_field_identity']==pre['parent_nine_field_identity']==role['report']['parent']['nine_field_identity']
    assert t['nonce']==binding['nonce']and len(binding['nonce'])==32 and all(c in '0123456789abcdef'for c in binding['nonce'])
    assert t['accepted_owner_argv']==pre['owner_argv']and t['inside_owner_argv']==pre['inside_owner_argv']and t['container_create_argv']==pre['container_create_argv']and t['qemu_argv']==pre['qemu_argv']
    root_argv=['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3']+pre['owner_argv'][1:]
    assert t['root_owner_argv']==root_argv==t['seven_steps'][3]['argv_template']
    assert root_argv[root_argv.index('--owner-sha256')+1]==t['runtime_owner']['sha256']and root_argv[root_argv.index('--manifest')+1]==binding['manifest']['path']and root_argv[root_argv.index('--manifest-sha256')+1]==binding['manifest']['sha256']
    owner=Path(t['runtime_owner']['path']);tree=ast.parse(exact(t['runtime_owner']));hashes=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='SOURCE_HASHES'for x in n.targets)))
    assert hashes==t['runtime_source_hashes']
    qmp=pre['paths']['qmp_socket'];assert qmp==str(parent/('attempt-'+binding['nonce'])/'qmp.sock')and len(os.fsencode(qmp))==97
    assert t['AF_UNIX']==[dict(option='-qmp',path=qmp,encoded_bytes=97)]and t['qemu_argv'][t['qemu_argv'].index('-qmp')+1]=='unix:'+qmp+',server=on,wait=off'
    assert not os.path.lexists(pre['paths']['attempt'])and not os.path.lexists(t['fresh_namespaces']['owner_evidence'])
    packet=Path(t['packet_output_locator']['selected_static_inputs_template']).parent
    assert str(packet)==t['packet_output_locator']['packet']==t['fresh_namespaces']['packet']and packet.parent==Path(TUPLE['path']).parent
    outputs=t['final19_outputs'];captures=t['fresh_capture_and_actual_command_paths'];sources=set(t['source_input_paths'])|{TUPLE['path'],CONTRACT['path'],str(Path(__file__).resolve())}
    assert len(outputs)==len(set(outputs))==19 and len(captures)==len(set(captures))==49 and len(t['seven_steps'])==7
    assert set(outputs+captures).isdisjoint(sources)
    for path in outputs+captures:
        assert packet in Path(path).parents and not os.path.lexists(path)
    physical=t['accepted_physical_reader'];accept=json.loads(exact(physical['independent_whole_acceptance']))
    assert accept['schema']=='mckernel.independent-native-positive-physical-actual-two-witness-review.v1'and accept['status']=='PASS_SOURCE_AND_ACTUAL_WHOLE_CONSUMER_CHECKS_ONLY'and accept['decision']=='PASS_EXACT_CURRENT_POSITIVE_NATIVE_OWNER_PHYSICAL_CONSUMER_AND_TWO_WITNESS_CHECKS'
    assert accept['source']==dict(path=physical['source']['path'],sha256=physical['source']['sha256'],bytes=physical['source']['size'])
    proposal=json.loads(exact(t['physical_reader_candidate']['proposal']))
    assert proposal['candidate_projection']==physical['source']and accept['actual_projection']==physical['recorded_projection']
    current=t['known_latest_physical_context'];assert accept['genuine_current_physical']==dict(path=current['path'],sha256=current['sha256'],bytes=current['size'])
    exact(physical['source']);exact(current);exact(physical['consumable_descriptor'])
    assert all(v is None for v in t['future'].values())
    assert t['packet_output_locator']['exact_M03_contract_matches']is False and t['packet_output_locator']['do_not_invoke_M03_materializer']is True
    return dict(tuple=t,original_role=role,packet=packet,outputs=outputs,captures=captures,source_paths=sources)

if __name__=='__main__':
    result=select();print(json.dumps(dict(status='CHILD_WHOLE_TUPLE_JOIN_ONLY',outputs=len(result['outputs']),capture_paths=len(result['captures']),steps=7,QMP_bytes=97,root_operations=0,guest_runs=0,writer_calls=0)))
