    fn read_current_fork_carrier(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let args=request.arguments();
        if request.number()!=56||args[5]!=0x313030434b46434d{return Err(EACCES);}
        if self.payload.is_none(){self.prepare_payload(args[4],128,true)?;}
        let(tag,address,writable)=self.payload.ok_or(EIO)?;
        if !writable||tag.span.physical!=args[4]
            ||tag.span.end.checked_sub(tag.span.physical)!=Some(128){return Err(EACCES);}
        // The same exclusive response-owned span permits both initial reads
        // and the eventual first receipt write; ordinary pager rights remain
        // unchanged. No peer byte is written before the original RET is bound.
        let mut bytes=[0;128];
        for(i,b)in bytes.iter_mut().enumerate(){*b=unsafe {ptr::read_volatile((address as *const u8).add(i))};}
        Ok(bytes)
    }
    pub(crate) fn current_fork_control_frame(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let a=request.arguments();
        if request.number()!=56||!matches!(a[0],2|3)||a[5]!=0x313030434b46434d{return Err(EACCES);}
        self.read_current_fork_carrier(request)
    }
    pub(crate) fn write_fork_control_frame(&mut self,bytes:&mut[u8;128])->Result {
        self.pager_copy(0,bytes,true)
    }