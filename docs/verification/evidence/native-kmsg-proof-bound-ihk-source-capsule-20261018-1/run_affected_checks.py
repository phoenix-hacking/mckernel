from pathlib import Path
import hashlib,json,os,shutil
N=Path(__file__).resolve().parent
prior=Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-cutover-20261018-1/check-v2.py')
assert hashlib.sha256(prior.read_bytes()).hexdigest()=='921fbbe94518ef41f8f8d78e779eb5c0475cb19490d1975026e7d32b8ce7f02f'
exec(compile(prior.read_text().split("if __name__=='__main__':",1)[0],str(prior),'exec'))
N=Path(__file__).resolve().parent;C=N/'capsule';E=N/'checks-1'
assert not E.exists();E.mkdir(mode=0o700)
bound=json.loads((N/'SOURCE-BINDINGS.json').read_text())
for r in bound['files'].values():
 p=Path(r['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_nlink==1 and p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
assert {str(p.relative_to(C)) for p in C.rglob('*') if p.is_file()}==set(bound['files'])
assert shutil.disk_usage('/home/holden/mckernel-work/host-preparation').free>16*2**30+32*2**20+512*2**20
assert shutil.disk_usage('/home/holden/mckernel-work/scratch').free>12*2**30+512*2**20
available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert available>2*2**30
os.environ['MCKERNEL_KMSG_FIXTURE_DATA']=str(E/'fixture-data')
run('affected-driver-owner',['/home/holden/anaconda3/bin/python3','-B',str(C/'scripts/tests/test_native_running_external_modules_owner.py')],cap_bytes=1024**2)
assert sum(p.stat().st_size for p in N.rglob('*') if p.is_file())<32*2**20
print(json.dumps({'status':'PASS_PRIVATE_AFFECTED_CAPSULE_ORDINARY_ONLY','commands':len(records),'tests':8,'target_builds':0,'root':False,'Docker':False}))
