// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact entire candidate and actual ABI; only output provider is a HOST mock.
#![allow(dead_code, unexpected_cfgs)]
#[path = "abi.snapshot.rs"] mod abi;
#[path = "f06_vdso_setup_log.rs"] mod candidate;

#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Record {
    format: [u8;128], rendered: [u8;128], has_argument: i32,
    argument: i32, printer_return: i32, rendered_length: i32,
}
impl Default for Record {
    fn default() -> Self {
        Self { format:[0;128], rendered:[0;128], has_argument:0,
               argument:0, printer_return:0, rendered_length:0 }
    }
}
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Trace { calls: u64, records: [Record;8] }
impl Default for Trace {
    fn default() -> Self { Self { calls:0, records:[Record::default();8] } }
}
unsafe extern "C" {
    fn original_arch_vdso_setup_log_bridge(event:i32,error:i32);
    fn fixture_reset(result:i32);
    fn fixture_read_trace(out:*mut Trace);
}
fn fixed(text:&str) -> [u8;128] {
    assert!(text.len()<128);
    let mut bytes=[0u8;128]; bytes[..text.len()].copy_from_slice(text.as_bytes()); bytes
}
fn expected(event:i32,error:i32,result:i32) -> Option<Record> {
    let (format,rendered,has_argument)=match event {
        1 => ("arch_setup_vdso: vdso_get_vdso_info failed. %d\n",
              format!("arch_setup_vdso: vdso_get_vdso_info failed. {error}\n"),true),
        2 => ("x86 local gettime disabled: host vgtod data unavailable\n",
              "x86 local gettime disabled: host vgtod data unavailable\n".to_owned(),false),
        3 => ("vdso disabled: host vgtod data unavailable\n",
              "vdso disabled: host vgtod data unavailable\n".to_owned(),false),
        4 => ("arch_setup_vdso: vdso_map_global_pages failed. %d\n",
              format!("arch_setup_vdso: vdso_map_global_pages failed. {error}\n"),true),
        _ => return None,
    };
    Some(Record { format:fixed(format),rendered:fixed(&rendered),
         has_argument:has_argument as i32,argument:if has_argument {error} else {0},
         printer_return:result,rendered_length:rendered.len() as i32 })
}
#[test]
fn exact_original_c_and_rust_vdso_setup_log() {
    assert_eq!(core::mem::size_of::<Record>(),272);
    assert_eq!(core::mem::size_of::<Trace>(),2184);
    let events=[i32::MIN,-65536,-1,0,1,2,3,4,5,6,255,65536,i32::MAX];
    let errors=[i32::MIN,-513,-14,-1,0,1,14,513,i32::MAX];
    let printer_results=[i32::MIN,-1,0,1,i32::MAX];
    let mut pairs=0;
    for event in events { for error in errors { for result in printer_results {
        unsafe { fixture_reset(result); original_arch_vdso_setup_log_bridge(event,error); }
        let mut original=Trace::default(); unsafe { fixture_read_trace(&mut original); }
        unsafe { fixture_reset(result); }
        candidate::arch_vdso_setup_log_bridge(event,error);
        let mut actual=Trace::default(); unsafe { fixture_read_trace(&mut actual); }
        assert_eq!(actual,original,"exact C/Rust trace event={event},error={error},result={result}");
        let mut independent=Trace::default();
        if let Some(record)=expected(event,error,result) { independent.calls=1; independent.records[0]=record; }
        assert_eq!(actual,independent,"independent message/argument/render/canary oracle");
        pairs+=1;
    }}}
    assert_eq!(pairs,585);
    // One retained mixed sequence additionally checks exact order and unknown-event silence.
    let sequence=[(1,-14),(0,99),(2,44),(4,i32::MIN),(3,22),(5,11),(1,i32::MAX)];
    unsafe { fixture_reset(-1); }
    for (event,error) in sequence { unsafe { original_arch_vdso_setup_log_bridge(event,error); } }
    let mut original=Trace::default(); unsafe { fixture_read_trace(&mut original); fixture_reset(-1); }
    for (event,error) in sequence { candidate::arch_vdso_setup_log_bridge(event,error); }
    let mut actual=Trace::default(); unsafe { fixture_read_trace(&mut actual); }
    assert_eq!(actual,original);
    let mut independent=Trace::default();
    for (event,error) in sequence { if let Some(record)=expected(event,error,-1) {
        independent.records[independent.calls as usize]=record; independent.calls+=1;
    }}
    assert_eq!(actual,independent);
    println!("functional vdso-setup-log original-C/Rust pairs={pairs}; mixed_sequence_calls={}; exact format/rendered bytes, int32 values, ordering and unknown-event silence checked",actual.calls);
}
