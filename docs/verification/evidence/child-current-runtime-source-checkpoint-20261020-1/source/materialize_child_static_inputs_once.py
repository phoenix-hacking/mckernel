"""Finite child amendment of accepted tuple-bound metadata materialization.
Three O_EXCL metadata outputs only; nineteen-output binder is a later reviewed
ordinary command. No source inspection resolver or runtime effect is added.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys
SOURCE=Path(__file__).resolve().parent
BASE=SOURCE.parent
SELECTOR = {'path': '/home/holden/mckernel-work/host-preparation/phase5-child-actual-stage-normalization-20261020-1/runtime-data-preparation-1/source/select_child_tuple_once.py', 'sha256': 'b70c7d1b1f5e49c624574351c23943067fcff2effb59556e987144c714517f9d', 'size': 6160, 'mode': 33152}

def ref(path):
    path=Path(path);raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),mode=path.lstat().st_mode)
def write(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w')as stream:
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    return ref(path)
def main():
    assert len(sys.argv)==5,'ACTUAL_CHILD_NORMALIZATION_REVIEW SHA256 COMPLETE_CURRENT_FETCHED_PROOF SHA256'
    assert ref(SELECTOR['path'])==SELECTOR
    spec=importlib.util.spec_from_file_location('exact_child_whole_tuple_selector',SELECTOR['path']);selector=importlib.util.module_from_spec(spec);spec.loader.exec_module(selector)
    selected=selector.select();t=selected['tuple'];packet=selected['packet']
    assert sys.argv[1:3]==[t['actual_normalization_acceptance']['path'],t['actual_normalization_acceptance']['sha256']]
    proof=ref(sys.argv[3]);assert proof['sha256']==sys.argv[4]
    document=json.loads(Path(proof['path']).read_bytes())
    assert document['schema']=='mckernel.root.exact-fetched-source-publication.v1'and document['verified']is True
    assert type(document['commit'])is str and len(document['commit'])==40 and document['count']==len(document['rows'])
    # The current root proof shape records verified fetched blobs directly;
    # do not invent a missing fetched_commit field or reuse the partial147 set.
    allow=json.loads((BASE/'PUBLICATION-ALLOWLIST.json').read_bytes())
    for path in allow['required_current_runtime_source_paths']:
        current=ref(path)
        assert any(row['sha256']==current['sha256']and row['bytes']==current['size']and row['mode']==current['mode']for row in document['rows']),'missing current published source '+path
    c=json.loads((packet/'STATIC-CHILD-NONTEMPORAL-INPUTS.PENDING.json').read_bytes())
    role=selected['original_role'];assert c['actual_preparation_acceptance']==t['actual_normalization_acceptance']and c['binding']==role['binding']and c['whole_manifest']==role['manifest']
    c.update(whole_manifest=t['binding']['manifest'],fetched_runtime_proof=dict(path=proof['path'],sha256=proof['sha256'],bytes=proof['size']),status='GENUINE_CHILD_NONTEMPORAL_INPUTS_CURRENT_SOURCE_PROOF_BOUND_PENDING_MAPPING_REVIEW')
    c['runtime_source_refs']=[dict(path=row['path'],sha256=row['sha256'],bytes=row['size'])for row in [ref(p)for p in sorted(SOURCE.glob('*.py'))]]+[dict(path=row['path'],sha256=row['sha256'],bytes=row['size'])for row in t['runtime_source_files']]
    command=json.loads((SOURCE/'FINAL19-CHILD-COMMAND.PENDING.json').read_bytes())
    assert command['argv'][4:8]==[t['actual_normalization_acceptance']['path'],t['actual_normalization_acceptance']['sha256'],t['known_latest_physical_context']['path'],t['known_latest_physical_context']['sha256']]and command['argv'][-2:]==[None,None]
    outputs=[packet/'STATIC-CHILD-NONTEMPORAL-INPUTS.json',SOURCE/'FINAL19-CHILD-COMMAND.REVIEW-PENDING.json',BASE/'FINAL19-MATERIALIZED-PROPOSAL.json']
    assert len(set(outputs))==3 and set(map(str,outputs)).isdisjoint(selected['source_paths']|set(selected['outputs']+selected['captures']))
    for path in outputs:assert not os.path.lexists(path)
    c_ref=write(outputs[0],c);command_ref=write(outputs[1],command)
    proposal=json.loads((BASE/'STATIC-SCAFFOLD-PROPOSAL.json').read_bytes())
    proposal.update(status='SOURCE_PROOF_BOUND_PENDING_EXACT_FINAL19_MAPPING_REVIEW_AND_ROOT_GRANT',fetched_source_proof=proof,static_inputs=c_ref,child_command_template=command_ref,root_ordinary_grant=None,independent_static_review=None)
    p_ref=write(outputs[2],proposal)
    print(json.dumps(dict(status='CHILD_METADATA_MATERIALIZED_ONLY',proposal=p_ref,static_inputs=c_ref,metadata_outputs=3,final_outputs=19,root_operations=0,guest_runs=0)))
if __name__=='__main__':main()
