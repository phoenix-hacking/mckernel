"""Five actual saved-evidence witnesses; proposed only, no live execution."""
from pathlib import Path
import copy,hashlib,importlib.util,json
D=Path(__file__).resolve().parent

def load(name,path,expected):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def refuses(call):
    try:call()
    except (AssertionError,ValueError):return
    raise AssertionError('negative accepted')

def main():
    cfg=json.loads((D/'PHYSICAL-CHECK-INPUTS.json').read_bytes())
    p=load('current_native_physical',Path(cfg['projection']['path']),cfg['projection']['sha256'])
    caller=load('existing_physical_terminal_caller',Path(cfg['caller']['path']),cfg['caller']['sha256'])
    ctx=p.checked(p.CONTEXT_REF);t=p.checked(ctx['physical_FD'])
    # Complete current machine predecessor fields come from the actual full
    # report and its actual snapshot ancestry, never a passing approval fixture.
    predecessor=dict(ctx['persistent_predecessor'],container_id=t['container_id'],owner_nonce=t['case_nonce'])
    overlay=dict(physical_projection_source=cfg['projection'],physical_review=ctx['physical'],physical_predecessor=predecessor,root_lock_identity=dict(device=27,inode=4,uid=0,gid=0,mode='0o644'))
    caller.terminal_joins(t,overlay)
    wrong=copy.deepcopy(t);wrong['schema']='mckernel.independent-current-v6-sdk.actual-physical-retirement.v1'
    refuses(lambda:p.kind(wrong))
    wrong=copy.deepcopy(ctx['physical_FD']);wrong['inode']+=1
    refuses(lambda:p.R.read_bytes(wrong))
    wrong=copy.deepcopy(t['archived_record_FDs']['owner']);wrong['metadata']['inode']+=1
    refuses(lambda:p.captured_bytes(wrong))
    wrong=copy.deepcopy(ctx['physical_FD']);del wrong['ctime_ns']
    refuses(lambda:p.R.read_bytes(wrong))
    result=dict(status='PASS',cases=['actual62ba_failed_exit7_complete_report_through_existing_terminal_caller','changed_report_kind_refused','changed_report_full_FD_identity_refused','changed_archive_full_FD_identity_refused','stripped_authoritative_descriptor_refused'],physical=ctx['physical'],actual_projection=predecessor,actual_projection_calls=1,root_operations=0,guest_runs=0,application_acceptance=False,scope='Saved current native-owner physical retirement only; original owner FAIL retained; no live snapshot/release/application acceptance')
    output=D/'ordinary-check-1'/'RESULT.json'
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(status='PASS',witnesses=5,actual_projection_calls=1)))

if __name__=='__main__':main()
