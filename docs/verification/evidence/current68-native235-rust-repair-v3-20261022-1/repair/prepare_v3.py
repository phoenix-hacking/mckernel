from pathlib import Path
import hashlib,json,difflib,shutil
D=Path(__file__).resolve().parent;V=D/'candidate-v3';V.mkdir()
for p in (D/'candidate').iterdir():shutil.copy2(p,V/p.name)
s=(V/'smp_application.rs').read_text();old=s
at='''        if published {
            for index in 0..slots.len() {
                let route=slots[index].as_ref().and_then(|entry|entry.fork_ingress.as_ref())
                    .filter(|owner|owner.parent==token).and_then(|owner|owner.host_start_return);'''
replacement='''        if published {
            // Record the original positive response at its real publication
            // boundary, under the same slots guard as every later selector1
            // admission. The sleeping RET waiter need not run first.
            for index in 0..slots.len() {
                let route=slots[index].as_ref().and_then(|entry|entry.fork_ingress.as_ref())
                    .filter(|owner|owner.parent==token&&owner.first_return_committed
                        &&!owner.first_return_published).map(|owner|owner.response.route());
                let Some((worker,serial))=route else{continue;};
                let parent=slots.iter().flatten().find(|entry|entry.key()==token).ok_or(ENOENT)?;
                if parent.syscalls.returned(worker,serial).map_err(errno)? {
                    slots[index].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_published=true;
                }
            }
            for index in 0..slots.len() {
                let route=slots[index].as_ref().and_then(|entry|entry.fork_ingress.as_ref())
                    .filter(|owner|owner.parent==token).and_then(|owner|owner.host_start_return);'''
assert s.count(at)==1;s=s.replace(at,replacement)
at='''                if let Some(child)=owned_child {
                    slots[child].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_published=true;
                }'''
replacement='''                if let Some(child)=owned_child {
                    // Only the continuing publisher records this observation.
                    // The waiter validates it; it cannot publish it late.
                    if !slots[child].as_ref().unwrap().fork_ingress.as_ref().unwrap().first_return_published {
                        return Err(errno(-71));
                    }
                }'''
assert s.count(at)==1;s=s.replace(at,replacement);(V/'smp_application.rs').write_text(s)
(D/'smp_application.v2-to-v3.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='candidate/smp_application.rs',tofile='candidate-v3/smp_application.rs')))
S=Path('/home/holden/mckernel-work/host-preparation/m05-sdk68-current-source-bundle-20261022-1/source-modules/smp_application.rs');pre=S.read_text();(D/'smp_application.production-to-v3.patch').write_text(''.join(difflib.unified_diff(pre.splitlines(True),s.splitlines(True),fromfile='a/smp_application.rs',tofile='b/smp_application.rs')))
pins=json.loads((D/'SOURCE-PINS.json').read_text())
for name,v in pins.items():v['v2_candidate_sha256']=v['candidate_sha256'];v['candidate_sha256']=hashlib.sha256((V/name).read_bytes()).hexdigest()
(D/'SOURCE-PINS-V3.json').write_text(json.dumps(pins,indent=2)+'\n')
