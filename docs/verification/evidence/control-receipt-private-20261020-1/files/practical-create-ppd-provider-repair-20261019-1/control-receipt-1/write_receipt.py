from pathlib import Path
import json,hashlib,difflib,re,sys
sys.path.insert(0,'/home/holden/mckernel');from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;B=P/'base/host-kernel/native-rust';S=P/'source/host-kernel/native-rust'
def src(n):return(B/n).read_text()
def put(n,s):(S/n).write_text(s)
def once(s,a,b):assert s.count(a)==1,(a[:80],s.count(a));return s.replace(a,b,1)
abi='''
// Distinct park-resume receipt ABI. Real registered MM verifier is mandatory;
// neither a selector nor a scalar return constructs HostAliasesRevokedControl.
pub(crate) const FORK_CONTROL_RECEIPT_UNCERTAIN_V1: i32 = 2;
pub(crate) type ForkControlResumeV1 = unsafe extern "C" fn(
    *mut c_void, Option<ForkVerifyV1>, *mut c_void, *mut c_void,
) -> i32;
pub(crate) type ForkControlReceiptResolveV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkControlV1, Option<ForkControlResumeV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareControlReceiptV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkControlReceiptResolveV1>, *mut c_void,
) -> i32;
'''
put('abi/application.rs',src('abi/application.rs')+abi)
t=once(src('smp_fork_link.rs'),'    quarantined: bool,\n}\npub(crate) struct PreparedControlTicket','    quarantined: bool,\n    receipt: ControlReceiptRecord,\n}\npub(crate) struct PreparedControlTicket')
t=once(t,'            quarantined: false };','            quarantined: false, receipt: ControlReceiptRecord::new() };');put('smp_fork_link.rs',t+'\n'+(P/'control_writer.rs.in').read_text())
put('smp_application.rs',once(src('smp_application.rs'),'pub(crate) use fork_link::{PreparedLinkTicket, PreparedControlTicket};','pub(crate) use fork_link::{PreparedLinkTicket, PreparedControlTicket, PreparedControlReceiptTicket, ControlReceiptOutcome};'))
service='''
    /// The actual parent preRETURN receipt hook; success still parks RET.
    pub(in super::super) unsafe fn prepare_fork_control_receipt(
        &self, worker: u64, serial: u64, cpu: i64, value: i64,
        resolve: super::super::application_abi::ForkControlReceiptResolveV1, context: *mut core::ffi::c_void,
    ) -> Result<bool> {
        let Some(mut ticket) = self.started.runtime.application.begin_fork_control_receipt(
            self.token, worker, serial, cpu, value,
        )? else { return Ok(false); };
        let descriptor = ticket.descriptor();
        let status = unsafe { resolve(context, &descriptor, Some(Self::resume_fork_control_scope),
            core::ptr::from_mut(&mut ticket).cast()) };
        if status != 0 {
            ticket.quarantine();
            return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
        }
        Ok(true)
    }
    unsafe extern "C" fn resume_fork_control_scope(ticket: *mut core::ffi::c_void,
        verify: Option<super::super::application_abi::ForkVerifyV1>,
        context: *mut core::ffi::c_void, payload: *mut core::ffi::c_void,
    ) -> i32 {
        if ticket.is_null() || context.is_null() { return EINVAL.to_errno(); }
        let Some(verify) = verify else { return EINVAL.to_errno(); };
        let Some(payload) = core::ptr::NonNull::new(payload.cast::<memory::ForkPayload>()) else { return EINVAL.to_errno(); };
        let ticket = unsafe { &*ticket.cast::<super::super::smp_application::PreparedControlReceiptTicket>() };
        match unsafe { ticket.resume(verify, context, payload) } {
            Ok(super::super::smp_application::ControlReceiptOutcome::Written) => 0,
            Ok(super::super::smp_application::ControlReceiptOutcome::Uncertain) =>
                super::super::application_abi::FORK_CONTROL_RECEIPT_UNCERTAIN_V1,
            Err(error) => error.to_errno(),
        }
    }
'''
put('smp_service.rs',once(src('smp_service.rs'),'    // END PRIVATE FORK PROVIDER APPLICATION',service+'    // END PRIVATE FORK PROVIDER APPLICATION'))
callback='''
unsafe extern "C" fn application_prepare_fork_control_receipt(
    parent: *mut core::ffi::c_void, worker: u64, serial: u64, cpu: i64, value: i64,
    resolver: Option<application_abi::ForkControlReceiptResolveV1>, context: *mut core::ffi::c_void,
) -> i32 {
    if parent.is_null() { return EINVAL.to_errno(); }
    let Some(resolver) = resolver else { return EINVAL.to_errno(); };
    let parent = unsafe { &*parent.cast::<smp_memory::Application>() };
    unsafe { parent.prepare_fork_control_receipt(worker, serial, cpu, value, resolver, context) }
        .map_or_else(|error| error.to_errno(), |handled| i32::from(handled))
}
'''
t=src('ihk_smp_x86_64.rs').replace('ihk_os_create_unbooted_v11','ihk_os_create_unbooted_v12')
t=once(t,'                    Some(application_prepare_fork_control),','                    Some(application_prepare_fork_control),\n                    Some(application_prepare_fork_control_receipt),')
t=once(t,'        application_prepare_fork_control: Option<application_abi::ForkPrepareControlV1>,','        application_prepare_fork_control: Option<application_abi::ForkPrepareControlV1>,\n        application_prepare_fork_control_receipt: Option<application_abi::ForkPrepareControlReceiptV1>,')
put('ihk_smp_x86_64.rs',once(t,'unsafe extern "C" fn application_prepare_fork_control(',callback+'\nunsafe extern "C" fn application_prepare_fork_control('))
t=src('os_runtime.rs');t=once(t,'    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,\n}','    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,\n    prepare_fork_control_receipt: Option<super::application_abi::ForkPrepareControlReceiptV1>,\n}')
t=re.sub(r'(                prepare_fork_control(?:: None)?,\n)',r'\1                prepare_fork_control_receipt: None,\n',t)
# The entire registered callback closure includes this additive endpoint.
lines=t.splitlines(True);count=0;inside=False
for i,line in enumerate(lines):
 if'if callbacks.open as usize != registered.open as usize'in line:inside=True
 if inside and'        { return Err(EACCES); }'in line:
  lines[i]='            || callbacks.prepare_fork_control_receipt.map(|f|f as usize) != registered.prepare_fork_control_receipt.map(|f|f as usize)\n'+line;count+=1;inside=False
assert count==5,count;t=''.join(lines)
# Preserve v11; v12 is separately named with one typed additive callback.
a=t.index('pub(crate) unsafe extern "C" fn ihk_os_create_unbooted_v11(');a=t.rfind('/// # Safety',0,a);z=t.index('\n/// # Safety',a+15);v12=t[a:z].replace('ihk_os_create_unbooted_v11','ihk_os_create_unbooted_v12')
v12=once(v12,'    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,\n) -> i64','    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,\n    prepare_fork_control_receipt: Option<super::application_abi::ForkPrepareControlReceiptV1>,\n) -> i64');v12=once(v12,'                prepare_fork_control_receipt: None,','                prepare_fork_control_receipt,');t=t[:z]+'\n'+v12+t[z:]
retain='''
    // An uncertain control write retains the exact original claim irrespective
    // of a mismatched/reused table cell; never quarantine a foreign replacement.
    fn retain_control_uncertain(self) {
        {
            let object = unsafe { &*self.object };
            let mut table = object.forks.lock();
            if let Some(entry) = table.entries[self.index].as_mut() {
                if entry.epoch == self.epoch && entry.identity == Some(self.identity)
                    && Arc::ptr_eq(&entry.owner, &self.owner)
                { entry.phase = FORK_PROVIDER_QUARANTINED; }
            }
        }
        // No table/Remote/MM guard or foreign callback/destructor spans forget.
        core::mem::forget(self);
    }
'''
t=once(t,'    fn begin_link_attempt(&mut self) -> Result {',retain+'    fn begin_link_attempt(&mut self) -> Result {')
old_resolver=balanced_item(t,'unsafe extern "C" fn resolve_fork_control_scope(')
resolver=old_resolver.replace('resolve_fork_control_scope','resolve_fork_control_receipt_scope').replace('park: Option<super::application_abi::ForkControlParkV1>','resume: Option<super::application_abi::ForkControlResumeV1>').replace('let park = park.ok_or(EINVAL)?;','let resume = resume.ok_or(EINVAL)?;')
a=resolver.index('        let capsule = claim.capsule');resolver=resolver[:a]+'''        let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
        let payload = claim.payload.as_ref().ok_or(ENODEV)?;
        let consumer_context = capsule.context.load(Ordering::Acquire);
        let payload_context = payload.context.load(Ordering::Acquire);
        if consumer_context.is_null() || payload_context.is_null() { return Err(EIO); }
        // The SAME exact BUSY claim owns both contexts. Registered backend code
        // freezes its owner BEFORE invoking this actual module-pinned verifier;
        // only then may it materialize an exclusive short payload borrow.
        let status = unsafe { resume(ticket, Some(capsule.verify), consumer_context, payload_context) };
        if unsafe { *descriptor } != before {
            claim.retain_control_uncertain(); return Err(errno(-71));
        }
        match status {
            0 => claim.restore_control(),
            super::application_abi::FORK_CONTROL_RECEIPT_UNCERTAIN_V1 => {
                claim.retain_control_uncertain(); Err(EIO)
            },
            error if (-4095..0).contains(&error) => {
                claim.restore_control()?; Err(errno(error))
            },
            _ => { claim.retain_control_uncertain(); Err(errno(-71)) },
        }
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}'''
prepare=balanced_item(t,'pub(crate) unsafe extern "C" fn prepare_fork_control_application(');prepare=prepare.replace('prepare_fork_control_application','prepare_fork_control_receipt_application').replace('registered.prepare_fork_control else','registered.prepare_fork_control_receipt else').replace('Some(resolve_fork_control_scope)','Some(resolve_fork_control_receipt_scope)')
t=once(t,'unsafe extern "C" fn resolve_fork_control_scope(',resolver+'\n\n#[export_name = "ihk_os_application_prepare_fork_control_receipt_v1"]\n'+prepare+'\n\nunsafe extern "C" fn resolve_fork_control_scope(')
exports='''
#[export_name = "__export_symbol_ihk_os_application_prepare_fork_control_receipt_v1"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static APPLICATION_CONTROL_RECEIPT_V1_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0", namespace: *b"MCKERNEL_IHK_V1\\0", padding: [0; 4],
    symbol: prepare_fork_control_receipt_application as *const () as *const u8,
};
#[export_name = "__export_symbol_ihk_os_create_unbooted_v12"]
#[link_section = ".export_symbol"]
#[used(compiler)]
pub(crate) static IHK_OS_CREATE_V12_EXPORT: IhkExportSymbolRecord = IhkExportSymbolRecord {
    license: *b"GPL\\0", namespace: *b"MCKERNEL_IHK_V1\\0", padding: [0; 4],
    symbol: ihk_os_create_unbooted_v12 as *const () as *const u8,
};
'''
put('os_runtime.rs',t+exports)
t=src('mcctrl_process.rs');t=once(t,'    fn ihk_os_application_prepare_fork_control_v1(', '    fn ihk_os_application_prepare_fork_control_receipt_v1(parent: *mut core::ffi::c_void, worker: u64, serial: u64, cpu: i64, value: i64) -> i32;\n    fn ihk_os_application_prepare_fork_control_v1(')
hook='''        // Resume ONLY an already owned control response; a receipt never
        // grants standard RET, legacy HOST_REVOKED or final ACK permission.
        match unsafe { ihk_os_application_prepare_fork_control_receipt_v1(
            self.context.as_ptr(), worker.handle, serial, cpu, value,
        ) } {
            0 => {}, 1 => return Err(EBUSY),
            error if (-4095..0).contains(&error) => return Err(errno(error)),
            _ => return Err(errno(-71)),
        }
'''
t=once(t,'        // Park a genuine fresh selector2 delivery before any legacy return',hook+'        // Park a genuine fresh selector2 delivery before any legacy return');put('mcctrl_process.rs',t)
patch=[];pins=[]
for f in sorted(S.rglob('*.rs')):
 n=str(f.relative_to(S));a=(B/n).read_text();b=f.read_text()
 if a!=b:patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/host-kernel/native-rust/'+n,tofile='b/host-kernel/native-rust/'+n))
 pins.append({'relative':n,'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size,'changed':a!=b})
(P/'control-receipt.patch').write_text(''.join(patch));(P/'source-pins.json').write_text(json.dumps(pins,indent=2)+'\n');print('changed_rust_files',sum(r['changed']for r in pins),'patch_bytes',(P/'control-receipt.patch').stat().st_size)
