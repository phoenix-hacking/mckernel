from pathlib import Path
import hashlib,json,difflib
D=Path(__file__).resolve().parent
S=Path('/home/holden/mckernel-work/host-preparation/m05-sdk68-current-source-bundle-20261022-1/source-modules')
L=Path('/home/holden/mckernel-work/host-preparation/p-m06-01-pinned-launcher-process-inputs-20261022-1/source-packet/executer/user/rust/mcexec_helpers.rs')
C=D/'candidate';C.mkdir(exist_ok=True)
pins={}
def emit(name,old,new):
 assert old!=new
 (C/name).write_text(new)
 pins[name]={'preimage_sha256':hashlib.sha256(old.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(new.encode()).hexdigest()}
 (D/(name+'.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
s=(S/'mcctrl.rs').read_text();s2=s.replace('abi::MCEXEC_UP_GET_CREDV =>','abi::MCEXEC_UP_GET_NUM_POOL_THREADS => Some(context.pool_thread_limit()),\n        abi::MCEXEC_UP_GET_CREDV =>',1);emit('mcctrl.rs',s,s2)
s=(S/'mcctrl_process.rs').read_text()
at='    fn registered(&self) -> Result<Arc<Registration>> {'
method='''    // Same advisory predicate as legacy mcctrl_get_num_pool_threads: count
    // Linux threads in this OS's registered launcher groups, limit above 128
    // per online Linux CPU. PID references exclude numeric identity reuse.
    pub(super) fn pool_thread_limit(&self) -> Result<isize> {
        let _registration=self.registered()?;
        let mut threads=0usize;
        {
            let entries=table().lock();
            for entry in entries.iter() {
                let process=&entry.process;
                if process.slot!=self.slot||process.generation!=self.generation
                    ||process.registration.lock().is_none(){continue;}
                // SAFETY: the owned PID yields an owned task. Its signal is
                // live until put_task_struct; match get_nr_threads READ_ONCE.
                unsafe {
                    let task=bindings::get_pid_task(process.pid.0.as_ptr(),bindings::pid_type_PIDTYPE_TGID);
                    if task.is_null(){continue;}
                    let signal=(*task).signal;
                    let count=ptr::read_volatile(ptr::addr_of!((*signal).nr_threads));
                    bindings::put_task_struct(task);
                    threads=threads.saturating_add(count.max(0) as usize);
                }
            }
        }
        // SAFETY: CPU hotplug read exclusion keeps the online bitmap stable.
        // Bounds use its actual generated array and Linux's CPU-ID limit.
        let online=unsafe {
            bindings::cpus_read_lock();
            let words=ptr::addr_of!(bindings::__cpu_online_mask.bits);
            let limit=(bindings::nr_cpu_ids as usize).min((&*words).len()*64);
            let mut count=0usize;
            for cpu in 0..limit {
                let mask=ptr::read_volatile(words.cast::<u64>().add(cpu/64));
                count+=usize::from(mask&(1u64<<(cpu%64))!=0);
            }
            bindings::cpus_read_unlock();
            count
        };
        if online==0{return Err(EIO);}
        Ok(isize::from(threads>online.saturating_mul(128)))
    }

'''
assert s.count(at)==1;emit('mcctrl_process.rs',s,s.replace(at,method+at))
s=(S/'smp_application.rs').read_text();s2=s
# A unique retained route tracks only the exact successful parent selector1 RET.
s2=s2.replace('    first_return_published:bool,','    first_return_published:bool,\n    host_start_return:Option<(u64,u64)>,',1)
s2=s2.replace('first_return_published:false,lease:', 'first_return_published:false,host_start_return:None,lease:',1)
at='    pub(crate) fn return_syscall(\n'
method='''    fn current_host_start_child(&self,slots:&[Option<Entry>],parent:Token,
        worker:u64,serial:u64,cpu:i64,value:i64,length:u64)->Result<Option<usize>> {
        let pe=slots.iter().flatten().find(|entry|entry.key()==parent).ok_or(ENOENT)?;
        let found=pe.syscalls.unique_delivered_fork(|request| {
            let a=request.arguments();a[0]==1&&a[5]==0x313030434b46434d
        }).map_err(errno)?;
        let Some((actual_worker,actual_serial,request))=found else{return Ok(None);};
        if (actual_worker,actual_serial)!=(worker,serial){return Ok(None);}
        if value!=0{return Ok(None);}
        let a=request.arguments();
        if cpu!=request.cpu() as i64||length!=0||request.pid()!=pe.cleanup.pid()
            ||request.target()!=0{return Err(EACCES);}
        let mut matched=None;
        for (index,entry) in slots.iter().enumerate() {
            let Some(ce)=entry else{continue;};
            let Some(owner)=ce.fork_ingress.as_ref() else{continue;};
            if owner.parent!=parent||owner.child_task.tgid() as u64!=a[1]{continue;}
            let image=ce.inherited_root.as_ref().ok_or(EACCES)?;
            let original=owner.response.request();
            if matched.is_some()||ce.closed||ce.needs_cleanup||ce.quarantined||ce.scheduled
                ||owner.host_start_return.is_some()||owner.host_revoke.is_some()
                ||!owner.sealed.load(Ordering::Acquire)||!owner.first_return_published
                ||owner.child!=ce.key()||!ce.syscalls.has_open_worker()
                ||image.end-image.start!=a[2]||image.root!=a[3]
                ||original.arguments()[4]!=a[4]||original.arguments()[5]!=a[5]
                ||original.requester()!=request.requester()||original.cpu()!=request.cpu()
                {return Err(EACCES);}
            ce.backend_ready()?;matched=Some(index);
        }
        matched.map(Some).ok_or(EACCES)
    }

'''
assert s2.count(at)==1;s2=s2.replace(at,method+at)
at='        let owned_child=loop {'
s2=s2.replace(at,'        let started_child=self.current_host_start_child(&slots,token,worker,serial,cpu,value,length)?;\n'+at,1)
at='        if let Some(child)=owned_child {\n            slots[child].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_committed=true;'
s2=s2.replace(at,'''        if let Some(child)=started_child {
            slots[child].as_mut().unwrap().fork_ingress.as_mut().unwrap().host_start_return=Some((worker,serial));
        }
'''+at,1)
# Atomically under slots, mark started only after actual parent response publication.
at='        let entry = slots\n            .iter_mut()\n            .flatten()\n            .find(|entry| entry.key() == token)\n            .ok_or(ENOENT)?;\n        if entry.needs_cleanup'
replacement='''        if published {
            for index in 0..slots.len() {
                let route=slots[index].as_ref().and_then(|entry|entry.fork_ingress.as_ref())
                    .filter(|owner|owner.parent==token).and_then(|owner|owner.host_start_return);
                let Some((worker,serial))=route else{continue;};
                let parent=slots.iter().flatten().find(|entry|entry.key()==token).ok_or(ENOENT)?;
                if parent.syscalls.returned(worker,serial).map_err(errno)? {
                    // Exact successful selector1 RET has been published. This
                    // is child admission, never destruction/final-ACK proof.
                    let child=slots[index].as_mut().unwrap();
                    child.scheduled=true;
                    child.fork_ingress.as_mut().unwrap().host_start_return=None;
                }
            }
        }
'''+at
assert s2.count(at)==1;s2=s2.replace(at,replacement)
emit('smp_application.rs',s,s2)
s=L.read_text();at='    unsafe { mcexec_main_loop_timeout_bridge() };\n    1\n}'
replacement='''    unsafe {
        mcexec_main_loop_timeout_bridge();
        // A terminal WAIT failure otherwise disappears when the joining main
        // discards this worker return and exits zero. Preserve the existing
        // fatal launcher exit path; retained kernel ownership stays retained.
        mcexec_exit_cmd_servers_bridge();
        mcexec_exit_process_bridge(1);
    }
    1
}'''
assert s.count(at)==1;emit('mcexec_helpers.rs',s,s.replace(at,replacement))
(D/'SOURCE-PINS.json').write_text(json.dumps(pins,indent=2)+'\n')
