from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).parent;S=P/'source/host-kernel/native-rust';B=P/'base/host-kernel/native-rust'
p=S/'os_runtime.rs';s=p.read_text();needle='    fn begin_link_attempt(&mut self) -> Result {';assert s.count(needle)==1
method='''    // Only for the strict park-only claim. A failed table identity check
    // cannot hand its original ownership to an unrelated/reused pending cell.
    // Keep every original owner/capsule/module pin on that uncertainty.
    fn restore_control(mut self) -> Result {
        let result = {
            let object = unsafe { &*self.object };
            let mut table = object.forks.lock();
            match table.entries[self.index].as_mut() {
                Some(entry) if entry.epoch == self.epoch && entry.identity == Some(self.identity)
                    && Arc::ptr_eq(&entry.owner, &self.owner) => {
                    if entry.phase == FORK_PROVIDER_BUSY && self.previous_phase == FORK_PROVIDER_PENDING {
                        entry.phase = FORK_PROVIDER_PENDING;
                        self.active = false;
                        Ok(())
                    } else {
                        entry.phase = FORK_PROVIDER_QUARANTINED;
                        Err(EIO)
                    }
                },
                _ => Err(EIO),
            }
        };
        // No table/Remote/MM guard is held. Forgetting this original claim
        // retains its OS/admission/capsule/module owners; no foreign Drop or
        // arbitrary decrement may run on a mismatched/reused pending entry.
        if result.is_err() { core::mem::forget(self); }
        result
    }
'''
s=s.replace(needle,method+needle)
a=s.index('unsafe extern "C" fn resolve_fork_control_scope(');z=s.index('\n/// # Safety',a);part=s[a:z];assert part.count('claim.restore()')==2;part=part.replace('claim.restore()', 'claim.restore_control()').replace('Restore failure quarantines IHK via Drop','Restore failure retains the original IHK claim')
s=s[:a]+part+s[z:];p.write_text(s)
patch=[];pins=[]
for f in sorted(S.rglob('*.rs')):
 n=str(f.relative_to(S));a=(B/n).read_text();b=f.read_text()
 if a!=b:patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/host-kernel/native-rust/'+n,tofile='b/host-kernel/native-rust/'+n))
 pins.append(dict(path=str(f),relative=n,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,changed=a!=b))
(P/'positive-control-park.patch').write_text(''.join(patch));(P/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n');print('patch_bytes',(P/'positive-control-park.patch').stat().st_size)
