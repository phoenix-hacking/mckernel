from pathlib import Path
import difflib,hashlib,json
Q=Path(__file__).resolve().parent
R=Path('/home/holden/mckernel')
P=Q/'postimages';P.mkdir(mode=0o700)
pins={}
def put(name,old,new):
 assert old!=new
 (P/name).write_text(new)
 (Q/(name+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/host-kernel/native-rust/'+name,tofile='b/host-kernel/native-rust/'+name)))
 p=R/'host-kernel/native-rust'/name;b=p.read_bytes();pins[name]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'postimage_sha256':hashlib.sha256(new.encode()).hexdigest()}
name='smp_cpu.rs';old=(R/'host-kernel/native-rust'/name).read_text();new=old
helper='''    /// Bounded observation under the existing CPU policy/hotplug locks.
    /// This reports policy and retained topology identity, not device-ref drop
    /// or physical restoration. Incomplete records never establish zero use.
    fn observe_shutdown_cpus(&self, boot: &super::smp_memory::ShutdownBoot, phase: &str, count: usize) {
        let owner = boot.owner();
        let emitted = count.min(64);
        pr_info!("IHK-SMP: resource-cpu-v1 os={} generation={} epoch={} phase={} rows={} emitted={} complete={}\\n",
            owner.slot(), owner.generation(), boot.epoch_id(), phase, count, emitted, (count <= 64) as u8);
        for index in 0..emitted {
            let cpu = self.requests[index];
            if let Ok(slot) = self.table.slot(cpu) {
                let token = slot.owner();
                pr_info!("IHK-SMP: resource-cpu-row-v1 os={} generation={} epoch={} phase={} index={} cpu={} hardware={} numa={} state={:?} owner_none={} owner_slot={} owner_generation={}\\n",
                    owner.slot(), owner.generation(), boot.epoch_id(), phase, index, cpu,
                    slot.hardware_id(), slot.numa_node(), slot.state(), token.is_none() as u8,
                    token.map_or(0, |token| token.slot()), token.map_or(0, |token| token.generation()));
            }
        }
    }

'''
anchor='    fn query_os(&mut self, owner: OsToken, request: Option<&CpuRequest>) -> Result<isize> {'
assert new.count(anchor)==1;new=new.replace(anchor,helper+anchor)
anchor='    let transaction = context.table.prepare_shutdown_online(owner, &context.requests[..count]).map_err(|_| EIO)?;\n    super::smp_memory::finish_shutdown_claim(&boot, || { transaction.commit(); })?;'
assert new.count(anchor)==1;new=new.replace(anchor,'    context.observe_shutdown_cpus(&boot, "prepared", count);\n'+anchor+'\n    context.observe_shutdown_cpus(&boot, "committed", count);')
put(name,old,new)
name='smp_memory.rs';old=(R/'host-kernel/native-rust'/name).read_text();new=old
helper='''    /// The CPU -> memory lock order and live claim already serialize this
    /// exact generation. Physical extents remain reserved Linux page owners;
    /// these rows do not establish Linux page release or callback/ref cleanup.
    fn observe_shutdown_memory(&self, claim: &ShutdownBoot, phase: &str) {
        let owner = claim.owner;
        let count = self.map.len();
        let emitted = count.min(64);
        pr_info!("IHK-SMP: resource-memory-v1 os={} generation={} epoch={} phase={} rows={} emitted={} complete={}\\n",
            owner.slot(), owner.generation(), claim.epoch_id(), phase, count, emitted, (count <= 64) as u8);
        for index in 0..emitted {
            if let Some(range) = self.map.extent(index) {
                let token = range.owner();
                pr_info!("IHK-SMP: resource-memory-row-v1 os={} generation={} epoch={} phase={} index={} start={} bytes={} numa={} owner_none={} owner_slot={} owner_generation={}\\n",
                    owner.slot(), owner.generation(), claim.epoch_id(), phase, index,
                    range.start(), range.length(), range.numa_node(), token.is_none() as u8,
                    token.map_or(0, |token| token.slot()), token.map_or(0, |token| token.generation()));
            }
        }
    }

'''
anchor='    fn finish_shutdown_claim(&mut self, claim: &ShutdownBoot, commit_cpu: impl FnOnce()) -> Result {'
assert new.count(anchor)==1;new=new.replace(anchor,helper+anchor)
anchor='''        if claim.epoch.shutdown.load(Ordering::Acquire) != SHUTDOWN_SERVICES_RETIRED {
            return Err(EBUSY);
        }
        let owner = claim.owner;'''
assert new.count(anchor)==1;new=new.replace(anchor,anchor.replace('        let owner = claim.owner;','        self.observe_shutdown_memory(claim, "prepared");\n        let owner = claim.owner;'))
anchor='''        claim.epoch.shutdown.store(SHUTDOWN_COMMITTED, Ordering::Release);
        boot.started = false;
        self.images[owner.slot() as usize] = None;
        self.arguments[owner.slot() as usize] = None;
        Ok(())'''
assert new.count(anchor)==1;new=new.replace(anchor,anchor.replace('        Ok(())','        self.observe_shutdown_memory(claim, "committed");\n        Ok(())'))
put(name,old,new)
(Q/'SOURCE-PINS.json').write_text(json.dumps(pins,indent=2)+'\n')
