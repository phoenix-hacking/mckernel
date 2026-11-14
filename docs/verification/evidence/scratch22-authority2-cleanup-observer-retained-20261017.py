# Retained exact Python body of the completed read-only inline observation.
# Executed via sudo -A taskset -c 0 /usr/bin/python3 -B - with stdout captured
# in native-exact-scratch22-authority2-cleanup-observation-20261017.json.
# This source retention is not another execution or an execution release.
import fcntl,importlib.util,json,os,subprocess
from pathlib import Path
spec=importlib.util.spec_from_file_location('cleanup','scripts/native_exact_scratch22_authority2_terminal_cleanup.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
lock=os.open(str(m.ROOT_LOCK),os.O_RDONLY|os.O_NOFOLLOW)
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
    assert not m.LEASE.exists()
    assert not Path('/proc/244086').exists()
    assert not Path('/proc/243497').exists()
    request=m.parse(m.read_bounded(m.REQUEST))
    owner=m.parse(m.read_bounded(m.ATTEMPT))
    ident='63c2d2570315c693bc06befaa37d1408ded53896b35d13d80bc4d7b9ecdba9cb'
    item=json.loads(subprocess.check_output(['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect','--',ident],timeout=20))[0]
    paths={m.REQUEST,m.TERMINAL,m.ROOT_TERMINAL,m.EVIDENCE/'container.log',m.EVIDENCE/'receipt.json',m.EVIDENCE/'build/receipt.json',m.EVIDENCE/'build/driver.log',m.ROOT/'native-exact-scratch-22-authority2-heavy-build.stdout'}
    paths.update(Path(request[k]) for k in ('driver_path','owner_path','input_manifest','image_receipt'))
    obs={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'candidate_commit':request['candidate_sha'],'candidate_tree':subprocess.check_output(['/usr/bin/git','-C',str(m.CANDIDATE),'rev-parse','HEAD^{tree}'],timeout=10).decode().strip(),'candidate_root':m.observe_identity(m.CANDIDATE),'container_inspect':item,'inventories':{str(p):m.metadata_inventory(p) for p in (m.OUTPUT,m.EVIDENCE)},'mount':json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-T',str(m.ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],timeout=10))['filesystems'][0],'request':m.observe_identity(m.REQUEST),'request_lease_absent':True,'retained_exclusions':[m.observe_identity(p) for p in (m.ATTEMPT,m.SHARED)],'root':m.observe_identity(m.ROOT),'root_lock':m.observe_identity(m.ROOT_LOCK),'selected_files':[m.observe_identity(p) for p in sorted(paths)],'target':{'container_id':ident,'container_name':item['Name'].lstrip('/'),'owner_nonce':item['Config']['Labels']['mckernel.owner'],'image_id':item['Image'],'owner_pid':owner['pid'],'owner_starttime':owner['starttime'],'exit_code':item['State']['ExitCode']}}
    assert obs['mount']['uuid']==m.UUID
    print(json.dumps(obs,sort_keys=True))
finally:
    fcntl.flock(lock,fcntl.LOCK_UN);os.close(lock)
