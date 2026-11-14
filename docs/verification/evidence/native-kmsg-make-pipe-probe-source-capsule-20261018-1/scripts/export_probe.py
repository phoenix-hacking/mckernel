#!/usr/bin/env python3
"""Export driver proof only after independent actual owner/probe/retirement review."""
import argparse,json,os,stat
from pathlib import Path
import probe_contract as c
ROLES={'request','preparation','owner_receipt','inner_result','inspect_before','inspect_terminal','postflight','ownership_archive','release_authorized','release_complete','dispatch_status','execution_release'}

def validate(b):
    c.need(b['schema']=='mckernel.pinned-make-proof-export.v1' and set(b['inputs'])==ROLES,'exact export roles')
    refs=b['inputs'];v={k:c.bound(r) for k,r in refs.items()};review=c.bound(b['independent_review'])
    c.need(review['decision']=='PASS_ACTUAL_PINNED_MAKE_PIPE_PROBE_AND_RETIREMENT' and review['implementation_ownership'] is False and review['reviewer'] and review['author'] and review['reviewer']!=review['author'],'independent actual acceptance required')
    c.need(review['inputs']==refs,'exact actual review bindings')
    req,prep,owner,inner=v['request'],v['preparation'],v['owner_receipt'],v['inner_result']
    c.need(req['image_id']==c.IMAGE and req['preparation']==refs['preparation'],'request/preparation binding')
    c.need(owner['schema']=='mckernel.native-running-external-modules-owner-receipt.v1' and owner['request']==req and owner['authority']['request']==refs['request'],'actual owner schema/request')
    c.need(owner['status']=='PASS' and owner['build_status']=='PASS' and owner['wait_exit_code']==0 and owner['retired'] is True and owner['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and owner['cleanup_separately_required'] is False and owner['terminal_container_retained'] is False and owner['terminal_container_info_current'] is True and owner['target_build'] is False,'positive owner/physical retirement')
    c.need(owner['probe_result_sha256']==refs['inner_result']['sha256'] and str(Path(req['candidate_root'])/'evidence/probe-result.json')==refs['inner_result']['path'],'actual inner path/hash')
    release=v['execution_release'];c.need(release['schema']=='mckernel.native-running-external-modules-release.v1' and release['status']=='PASS_EXECUTION_RELEASE' and release['request']==refs['request'] and release['nonce']==req['nonce'] and release['boot_id']==req['boot_id'] and release['source_sha256']==owner['authority']['source_sha256'],'actual source/execution release join')
    joined=c.validate_inner(inner,Path(req['candidate_root']),prep['source_rows']);c.need(joined==owner['probe_evidence'],'owner/actual raw probe evidence join')
    c.need(owner['image_inspect']['Id']==c.IMAGE and owner['image_inspect']['Architecture']=='amd64','actual image-inspect join')
    cid=owner['container_id'];before,terminal=v['inspect_before'],v['inspect_terminal']
    expected_mounts=sorted([(req['input_root'],'/probe',False),(req['candidate_root'],'/work',True)])
    for x in (before,terminal):
        c.need(x['Id']==cid and x['Name']=='/'+owner['container_name'] and x['Image']==c.IMAGE and x['Config']['Image']==c.IMAGE and x['Config']['Labels']['mckernel.owner']==req['nonce'],'actual immutable container image/ID/label')
        cfg,host=x['Config'],x['HostConfig'];c.need(cfg['User']=='1000:1000' and cfg['Entrypoint']==['/usr/bin/timeout'],'actual entry/user')
        expected_cmd=['--signal=TERM','--kill-after=2s','35s','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=30:30','--fsize=1048576:1048576','--core=0:0','--','/usr/bin/python3','/probe/probe.py','--execute']
        c.need(cfg['Cmd']==expected_cmd and x['Path']=='/usr/bin/timeout' and x['Args']==expected_cmd,'actual one-probe command')
        c.need(host['Memory']==host['MemorySwap']==12884901888 and host['NanoCpus']==4000000000 and host['CpusetCpus']=='2-5' and host['PidsLimit']==512,'actual resource profile')
        c.need(host['NetworkMode']=='none' and host['IpcMode']=='private' and host['ReadonlyRootfs'] is True and host['CapDrop']==['ALL'] and host['Init'] is True and 'no-new-privileges' in host['SecurityOpt'] and host['AutoRemove'] is False and host['RestartPolicy']=={'Name':'no','MaximumRetryCount':0} and host['Tmpfs']=={'/tmp':'rw,nodev,nosuid,size=256m'},'actual isolation/retention profile')
        mounts=sorted((r['Source'],r['Destination'],r['RW']) for r in x['Mounts'] if r['Type']=='bind');c.need(mounts==expected_mounts,'actual exact two bindings')
    c.need(before['Config']==terminal['Config'] and before['HostConfig']==terminal['HostConfig'] and sorted(json.dumps(r,sort_keys=True) for r in before['Mounts'])==sorted(json.dumps(r,sort_keys=True) for r in terminal['Mounts']),'profile stable')
    state=terminal['State'];c.need(state['Status']=='exited' and state['Pid']==0 and state['Running'] is False and state['OOMKilled'] is False and state['ExitCode']==0,'actual terminal state')
    post=v['postflight'];c.need(post==owner['postflight'] and post['container_absent'] is True and post['all_clients_reaped'] is True and post['compiler_status']=='PASS','postflight owner join')
    absence=post['absence'];c.need(absence['absent'] is True and absence['container_id']==cid and absence['name']==owner['container_name'] and absence['nonce']==req['nonce'] and absence['queries']==['name','label','id'],'exact positive absence')
    for name in ('client_group_checks','admission_client_group_checks'):
        rows=post[name];c.need(rows and all(r['empty'] is True and r['surviving_members']==[] for r in rows),'all positive client groups')
        for path in {r['status_path'] for r in rows}:
            status=json.loads(c.read(path));c.need(status['state']=='exited' and type(status['exit_code']) is int and status['exit_code']>=0 and not status.get('client_retirement_unproven'),'actual positive client wait ledger')
    arc,authorized,complete=v['ownership_archive'],v['release_authorized'],v['release_complete']
    c.need(arc['source_sha256']==owner['authority']['source_sha256'] and arc['request']==refs['request'] and arc['nonce']==req['nonce'] and arc['postflight']==post and len(arc['records'])==3,'owned archive join')
    expected_records={req['lease_path']:('lease',owner['operation_lease']),req['common_exclusion_path']:('common',owner['common_record']),'/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock':('shared',owner['shared_record'])}
    c.need({r['path'] for r in arc['records']}==set(expected_records),'exact three owned records')
    for r in arc['records']:
        label,record=expected_records[r['path']];c.need(r['record']==record,'owned original record join')
        raw=c.read(Path(refs['owner_receipt']['path']).parent/(label+'.record.raw'));c.need(len(raw)==r['size'] and c.digest(raw)==r['sha256'],'actual archived original bytes')
    c.need(authorized['records']==arc['records'] and authorized['status']=='POSTFLIGHT_RELEASE_AUTHORIZED' and complete['status']=='OWNED_RECORDS_RELEASED' and authorized['nonce']==complete['nonce']==req['nonce'] and authorized['archive_sha256']==complete['archive_sha256']==refs['ownership_archive']['sha256'],'positive authorized record release')
    dispatch=v['dispatch_status'];c.need(dispatch['returncode']==0 and dispatch['direct_child_joined'] is True and dispatch['owned_group_absent'] is True and dispatch['request']==refs['request'],'actual outer direct join')
    c.need(dispatch['release']==refs['execution_release'] and dispatch['owner_sha256']==release['source_sha256']['scripts/native_running_external_modules_owner.py'],'outer source/release binding')
    owner_path=str(Path(refs['preparation']['path']).parent/'scripts/native_running_external_modules_owner.py')
    expected_argv=['/home/holden/anaconda3/bin/python3','-B',owner_path,'--request',refs['request']['path'],'--request-sha256',refs['request']['sha256'],'--release',refs['execution_release']['path'],'--release-sha256',refs['execution_release']['sha256']]
    c.need(dispatch['argv']==expected_argv,'actual ordinary owner argv')
    for role in ('stdout','stderr'):
        r=dispatch['captures'][role];data=c.read(r['path']);c.need(len(data)==r['bytes'] and c.digest(data)==r['sha256'],'actual outer stream')
        c.need((json.loads(data)==owner) if role=='stdout' else not data,'exact owner stdout/empty stderr')
    return dict(status='PASS_PINNED_MAKE_PIPE_RECIPE',image_id=c.IMAGE,make_path='/usr/bin/make',argv=c.ARGV,returncode=0,direct_child_joined=True,pipe_jobserver_observed=True,fifo_count=0,make_sha256=inner['make_sha256'],make_version=inner['make_version'],source_rows=prep['source_rows'],actual_observation=refs['inner_result'],actual_owner=refs['owner_receipt'],independent_review=b['independent_review'],actual_inputs=refs,driver_build_authority=False)

def export(binding,sha,output):
    b=c.bound(dict(path=str(binding),sha256=sha));proof=validate(b)
    p=Path(output);c.need(p.is_absolute() and p.parent.resolve()==p.parent and not p.exists(),'fresh canonical proof output')
    raw=(json.dumps(proof,indent=2)+'\n').encode();c.need(len(raw)<c.CAP,'proof cap');fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return c.reference(p)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binding',type=Path,required=True);p.add_argument('--binding-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(export(a.binding,a.binding_sha256,a.output)))
if __name__=='__main__':main()
