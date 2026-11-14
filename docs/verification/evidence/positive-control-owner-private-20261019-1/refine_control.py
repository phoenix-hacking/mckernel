from pathlib import Path
import sys,re,json,hashlib,difflib
sys.path.insert(0,'/home/holden/mckernel');from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;S=P/'source/host-kernel/native-rust';B=P/'base/host-kernel/native-rust'
p=S/'os_runtime.rs';s=p.read_text();link=balanced_item(s,'pub(crate) unsafe extern "C" fn prepare_fork_link_application(');a=link.index('        if callbacks.open');z=link.index('        { return Err(EACCES); }',a)+len('        { return Err(EACCES); }');full=link[a:z]
control=balanced_item(s,'pub(crate) unsafe extern "C" fn prepare_fork_control_application(');a=control.index('        if callbacks.open');z=control.index('        { return Err(EACCES); }',a)+len('        { return Err(EACCES); }');old=control[a:z];assert s.count(old)==1;s=s.replace(old,full,1)
# All five actual connection closure joins include the additive callback.
needle='        { return Err(EACCES); }';lines=s.splitlines(True);count=0;inside=False
for i,l in enumerate(lines):
 if 'if callbacks.open as usize != registered.open as usize' in l:inside=True
 if inside and needle in l:
  lines[i]='            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)\n'+l;count+=1;inside=False
assert count==5,count;s=''.join(lines);p.write_text(s)
p=S/'smp_fork_link.rs';s=p.read_text();needle='''    let proof = p.syscalls.unique_delivered(|r| r.number() == 56 && r.arguments()[0] == 2).map_err(errno)?;'''
new='''    // A parked call no longer appears in unique_delivered because the SAME
    // Response has moved. Reject its exact retry before legacy RETURN hooks.
    for f in slots.iter().flatten().filter_map(|e| e.fork.as_ref()) {
        let Some(control) = &f.control else { continue; };
        let d = control.descriptor;
        if d.identity.parent != parent.wire() || d.worker != worker || d.delivery != serial { continue; }
        if d.cpu as i64 != cpu || d.identity != host_key(f.reservation.identity)
            || f.ack.as_ref().is_none_or(|ack| ack.epoch != d.epoch)
            || control.request.number() != 56 || control.request.arguments()[0] != 2
            || control.request.arguments()[5] != CARRIER_MARKER
            || control.request.pid() != p.cleanup.pid() || control.request.cpu() != d.cpu
            || control.request.response() != d.response || control._response.request() != &control.request
        { return Err(EACCES); }
        return Err(EBUSY);
    }
'''+needle
assert s.count(needle)==1;s=s.replace(needle,new)
needle='''    let descriptor = super::super::application_abi::ForkControlV1 {'''
new='''    let pin = f.retained_parent.as_ref().ok_or(EBUSY)?;
    if pin.parent != parent || pin.identity != k || pin.reservation != f.reservation.token.wire()
        || !core::ptr::eq(&*pin.remote, remote) { return Err(EACCES); }
'''+needle
assert s.count(needle)==1;s=s.replace(needle,new);p.write_text(s)
patch=[];pins=[]
for f in sorted(S.rglob('*.rs')):
 n=str(f.relative_to(S));a=(B/n).read_text();b=f.read_text()
 if a!=b:patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/host-kernel/native-rust/'+n,tofile='b/host-kernel/native-rust/'+n))
 pins.append(dict(path=str(f),relative=n,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size,changed=a!=b))
(P/'positive-control-park.patch').write_text(''.join(patch));(P/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n');print('callback_closure_joins',count,'patch_bytes',(P/'positive-control-park.patch').stat().st_size)
