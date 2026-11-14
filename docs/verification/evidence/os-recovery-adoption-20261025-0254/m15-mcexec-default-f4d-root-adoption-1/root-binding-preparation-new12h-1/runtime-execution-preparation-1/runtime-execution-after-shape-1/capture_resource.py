"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only fresh read-only physical/resource capture, using accepted shared observer.
No compiler, Docker workload, clock allocation, release or native mutation.
"""
import argparse,json,subprocess
from pathlib import Path
import execution_contract as c
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('ledger','latest-postjoin','source-publication'):p.add_argument('--'+n,required=True);p.add_argument('--'+n+'-sha256',required=True)
    a=p.parse_args();o=c.owner();requestpath=c.HERE/'ADOPT-REQUEST.json';request=json.loads(requestpath.read_bytes());references={}
    for name in ('ledger','latest-postjoin','source-publication'):
        path=getattr(a,name.replace('-','_'));r=dict(path=str(Path(path).resolve()),sha256=getattr(a,name.replace('-','_')+'_sha256'));c.bound(r);references[name]=c.ref(r['path'])
    clocks=c.campaign();ledger=c.ledger(references['ledger'],request['nonce']);pin=c.pins()['pins']['observer'];c.need(c.ref(pin['path'])==pin,'reuse accepted outer resource observer')
    obs=c.load('accepted_outer_resource_observer',pin['path']);physical=obs.observe()
    memory={line.split(':')[0]:int(line.split(':')[1].split()[0])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemTotal:'))};c.need(memory['MemAvailable']>=24*2**30,'original24GiB aggregate memory floor')
    paths=['/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us','/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us','/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes','/sys/fs/cgroup/pids/mckernel-dev/pids.max','/sys/fs/cgroup/pids/mckernel-dev/pids.current'];cg={p:Path(p).read_text().strip() for p in paths};c.need(list(cg.values())==['100000','400000','12884901888','512','0'],'original empty fourCPU12GiB512tasks cgroup')
    running=subprocess.run(['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-q','--no-trunc'],capture_output=True,text=True,timeout=15);c.need(running.returncode==0 and not running.stdout.strip() and not running.stderr,'no running Docker workload')
    resources=dict(scope=c.pins()['scope'],observed_clocks=clocks,boot_id=o.BOOT,no_existing_heavy=True,physical_observer=pin,current_physical_observation=physical,memory=memory,cgroups=cg,no_running_containers=dict(returncode=running.returncode,stdout=running.stdout,stderr=running.stderr),planned_profile=o.LIBRARY_PREPARATION['profile'],nonce_ledger=references['ledger'],owner_resources=o.measure(request),runtime_authority=None)
    rp=c.HERE/'ROOT-FRESH-RESOURCE-PHYSICAL.json';c.write(rp,resources)
    admission=dict(schema='mckernel.mcexec-default-current-admission.v1',status='ROOT_RESERVED_MCEXEC_DEFAULT_SOLE_HEAVY',author='/root',nonce=request['nonce'],request=c.short(c.ref(requestpath)),boot_id=o.BOOT,profile=o.LIBRARY_PREPARATION['profile'],one_heavy=True,observed_clocks=clocks,expires_wall=min(clocks[0]+120,c.pins()['cutoffs'][0]),nonce_ledger_complete=True,consumed_nonces=ledger['consumed_nonces'],resource_physical=c.ref(rp),latest_postjoin_acceptance=references['latest-postjoin'],source_publication=references['source-publication'])
    c.campaign();c.validate_admission(admission,request,c.ref(requestpath),c.campaign());ap=c.HERE/'CURRENT-ADMISSION.ACTUAL.json';c.write(ap,admission);print(json.dumps(dict(admission=c.ref(ap),entry=False)))
if __name__=='__main__':main()
