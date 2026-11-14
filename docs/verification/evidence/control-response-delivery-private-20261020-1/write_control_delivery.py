from pathlib import Path
import json,hashlib,difflib,sys
sys.path.insert(0,'/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;B=P/'base/host-kernel/native-rust';S=P/'source/host-kernel/native-rust'
def once(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a))
 return s.replace(a,b,1)
def save(name,s):
 assert (S/name).read_bytes()==(B/name).read_bytes(),name
 (S/name).write_text(s)
s=(B/'application_syscall.rs').read_text()
s=once(s,'    /// Claim the guest\'s wake state exactly once.',(P/'retained_prepare.rs.in').read_text()+'\n    /// Claim the guest\'s wake state exactly once.')
save('application_syscall.rs',s)
s=(B/'smp_application_syscall.rs').read_text()
s=once(s,'    // END PRIVATE FORK INGRESS RESPONSE TICKET',(P/'queue_control.rs.in').read_text()+'\n    // END PRIVATE FORK INGRESS RESPONSE TICKET')
old=balanced_item(s,'pub(crate) fn publish_observed(')
start=old.index('        self.completion_cursor = ')
body=old[start:old.rfind('}')]
new=old[:start]+'        self.publish_index_observed(index, send, observed)\n    }'
new+='\n    fn publish_index_observed(&mut self,index:usize,\n        send:impl FnOnce(&[u8;128])->Result,\n        observed:impl FnOnce(&Request,Option<u64>,u64),\n    )->Result<bool>{\n'+body+'}'
s=once(s,old,new);save('smp_application_syscall.rs',s)
s=(B/'smp_fork_link.rs').read_text()
s=once(s,'    write_error: Option<i32>,','    write_error: Option<i32>,\n    queued: bool,\n    published: bool,')
s=once(s,'written: false, uncertain: false, write_error: None','written: false, uncertain: false, write_error: None, queued: false, published: false')
s+='\n'+(P/'control_publish.rs.in').read_text()+'''
pub(super) fn has_control_completion(slots:&[Option<Entry>],parent:Token,cpu:i32)->bool{
 slots.iter().flatten().filter_map(|e|e.fork.as_ref()).filter_map(|f|f.control.as_ref())
  .any(|c|c.descriptor.identity.parent==parent.wire()&&c.descriptor.cpu==cpu
   &&c.receipt.queued&&!c.receipt.published)
}
'''
save('smp_fork_link.rs',s)
s=(B/'smp_application.rs').read_text()
s=once(s,'        if fork_publication_frozen(&slots, token, cpu)','''        if fork_link::has_control_completion(&slots, token, cpu) {
            let result=fork_link::publish_control_receipt_in_slots(self,&mut slots,token,cpu,send);
            // The exact control publisher records real response release before
            // bookkeeping/notify errors. No generic completion is selected.
            return self.finish_publication(&mut slots,result,notify);
        }
        if fork_publication_frozen(&slots, token, cpu)''')
s=once(s,'        authorize_fork_return(&slots, token, worker, serial, cpu, value)?;','''        if fork_link::queue_control_receipt_in_slots(self,&mut slots,token,worker,serial,cpu,destination,length)?.is_some() {
            bytes[48..56].copy_from_slice(&1u64.to_le_bytes());
            loop {
                // Queueing alone is not ioctl success. This marker is set by
                // the actual Completion status-Release observer only.
                if fork_link::control_receipt_published(&slots,token,worker,serial,cpu)? { return Ok(()); }
                let entry=slots.iter().flatten().find(|e|e.key()==token).ok_or(ENOENT)?;
                if entry.quarantined { return Err(EIO); }
                self.changed.wait(&mut slots);
            }
        }
        authorize_fork_return(&slots, token, worker, serial, cpu, value)?;''')
save('smp_application.rs',s)
s=(B/'mcctrl_process.rs').read_text()
s=once(s,'''        // Resume ONLY an already owned control response; a receipt never
        // grants standard RET, legacy HOST_REVOKED or final ACK permission.
        match unsafe { ihk_os_application_prepare_fork_control_receipt_v1(''','''        // Success means a real receipt was written under its authenticated
        // claim. It may enter ONLY the backend's exact owned-control return;
        // the incoming launcher scalar is never transport/phase authority.
        let control_receipt_ready = match unsafe { ihk_os_application_prepare_fork_control_receipt_v1(''')
s=once(s,'''            0 => {}, 1 => return Err(EBUSY),
            error if (-4095..0).contains(&error) => return Err(errno(error)),
            _ => return Err(errno(-71)),
        }
        // Park''','''            0 => false, 1 => true,
            error if (-4095..0).contains(&error) => return Err(errno(error)),
            _ => return Err(errno(-71)),
        };
        // Park''')
# balanced_item handles an ordinary braced item, while this match has a call
# initializer. Capture its exact textual scope through the known following hook.
needle='''        match unsafe { ihk_os_application_prepare_fork_control_v1(
            self.context.as_ptr(), worker.handle, serial, cpu, value,
        ) } {
            0 => {}, 1 => return Err(EBUSY),
            e if (-4095..0).contains(&e) => return Err(errno(e)),
            _ => return Err(errno(-71)),
        }'''
s=once(s,needle,'        if !control_receipt_ready {\n'+needle+'\n        }')
save('mcctrl_process.rs',s)
rows=[];patch=[]
for f in sorted(S.rglob('*.rs')):
 rel=f.relative_to(S);b=B/rel;data=f.read_bytes();rows.append({'path':str(f),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'changed':data!=b.read_bytes()})
 if data!=b.read_bytes():patch.extend(difflib.unified_diff(b.read_text().splitlines(True),f.read_text().splitlines(True),fromfile='a/host-kernel/native-rust/'+str(rel),tofile='b/host-kernel/native-rust/'+str(rel)))
(P/'control-response-delivery.patch').write_text(''.join(patch))
(P/'source-pins.json').write_text(json.dumps({'rows':rows,'changed_files':sum(r['changed']for r in rows),'scope':'private held provider transport only; guestconsumer/currentactivation pending'},indent=2)+'\n')
print('changed_files',sum(r['changed']for r in rows),'patch_sha256',hashlib.sha256((P/'control-response-delivery.patch').read_bytes()).hexdigest())
