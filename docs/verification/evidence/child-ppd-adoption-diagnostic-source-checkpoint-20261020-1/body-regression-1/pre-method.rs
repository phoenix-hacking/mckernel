    fn adopt_current_fork_v4(&self,descriptor:&[u8;24],compat:bool)->Result<isize> {
        let word=|at|u64::from_le_bytes(descriptor[at..at+8].try_into().unwrap());
        let (start,length,root)=if compat{let integer=|at|u32::from_le_bytes(descriptor[at..at+4].try_into().unwrap()) as u64;
            (integer(0),integer(4),integer(8))}else{(word(0),word(8),word(16))};
        let end=start.checked_add(length).ok_or(EINVAL)?;
        if root==0||root%4096!=0||start%4096!=0||length==0||length%4096!=0{return Err(EINVAL);}
        let process=self.process()?;let current=ProcessId::current()?;
        if !process.pid.same(&current){return Err(EACCES);}
        process.registration_pending.compare_exchange(false,true,Ordering::AcqRel,Ordering::Acquire).map_err(|_|EBUSY)?;
        let _reservation=RegistrationReservation(&process);
        if process.registration.lock().is_some(){return Err(EINVAL);}
        let (mirror,parent)=Mirror::inherited_registration(start,end)?;
        if parent.slot!=self.slot||parent.generation!=self.generation||self.generation==0||parent._pid.same(&current){return Err(EACCES);}
        let child=Registration::acquire(self.slot,self.generation,current)?;
        let geometry=super::application_abi::ForkGeometryV3{root,start,length};
        let mut attempt=CurrentForkAdoptAttempt{process:&process,parent:&parent,child:&child,mirror:&mirror,geometry,called:false,published:false};
        let status=unsafe {ihk_os_application_adopt_current_v4(parent.context.as_ptr(),child.context.as_ptr(),
            &geometry,Some(current_fork_adopted_v4),ptr::from_mut(&mut attempt).cast())};
        kernel::error::to_result(status)?;
        if !attempt.called||!attempt.published{return Err(errno(-71));}Ok(0)
    }
