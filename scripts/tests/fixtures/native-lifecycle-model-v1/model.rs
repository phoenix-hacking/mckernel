// MODEL_ONLY: safe standalone lifecycle publication state model.
#![forbid(unsafe_code)]
use std::io::{self, BufRead};

const MAX_OBJECTS: usize = 8;
const MAX_OPS: u64 = 128;
const MAX_EVENTS: u64 = 256;

#[derive(Clone, Copy, PartialEq)]
enum Phase { Empty, Allocated, Born, Runnable, Aborted, ThreadTerminal, RetireBegun, ThreadRetired }

#[derive(Clone, Copy)]
struct Object {
    phase: Phase,
    capture: u64, slot: u32, generation: u64, application: u64,
    process: u64, thread: u64, exec: u64, pid: i32, tid: i32,
    refs: u32, process_terminal: bool, process_retired: bool,
    main_storage: bool, zombie: bool, vm_owned: bool,
}
impl Object {
    const fn empty() -> Self { Self { phase: Phase::Empty, capture: 0, slot: 0, generation: 0,
        application: 0, process: 0, thread: 0, exec: 0, pid: 0, tid: 0, refs: 0,
        process_terminal: false, process_retired: false, main_storage: false,
        zombie: false, vm_owned: false } }
}

struct Model {
    objects: [Object; MAX_OBJECTS], event_capacity: u64, attempts: u64, lost: u64,
    incomplete: bool, ended: bool, operations: u64,
}
impl Model {
    fn new(capacity: u64) -> Option<Self> {
        if capacity > MAX_EVENTS { return None; }
        Some(Self { objects: [Object::empty(); MAX_OBJECTS], event_capacity: capacity,
            attempts: 0, lost: 0, incomplete: false, ended: false, operations: 0 })
    }
    fn index(&self, process: u64, thread: u64) -> Option<usize> {
        self.objects.iter().position(|x| x.phase != Phase::Empty && x.process == process && x.thread == thread)
    }
    fn process_index(&self, process: u64) -> Option<usize> {
        self.objects.iter().position(|x| x.phase != Phase::Empty && x.process == process)
    }
    fn emit(&mut self, kind: &str, process: u64, thread: u64, raw: u64, branch: u64) {
        match self.attempts.checked_add(1) {
            Some(next) => self.attempts = next,
            None => { self.incomplete = true; self.lost = u64::MAX; return; }
        }
        if self.attempts <= self.event_capacity {
            println!("E {} {} {} {} {} {}", self.attempts, kind, process, thread, raw, branch);
        } else {
            self.incomplete = true;
            self.lost = self.lost.checked_add(1).unwrap_or_else(|| { self.incomplete = true; u64::MAX });
        }
    }
    fn apply(&mut self, fields: &[&str]) -> u32 {
        self.operations = match self.operations.checked_add(1) { Some(x) if x <= MAX_OPS => x, _ => { self.incomplete=true; return 15 } };
        if self.ended { self.incomplete = true; return 14; }
        let op = fields[0];
        let nums: Result<Vec<u64>, _> = fields[1..].iter().map(|x| x.parse::<u64>()).collect();
        let n = match nums { Ok(x) if x.len() == 9 => x, _ => { self.incomplete=true; return 1 } };
        let process=n[1]; let thread=n[2];
        match op {
            "alloc" => {
                let (capture,slot,generation,application,proc_id,thread_id,pid,tid)=(n[1],n[2],n[3],n[4],n[5],n[6],n[7],n[8]);
                // Line fields are op, operation-id, capture, slot, generation, application,
                // process-instance, thread-instance, pid, tid. Exec equals application here.
                if capture==0 || slot>=64 || generation==0 || application==0 || proc_id==0 || thread_id==0 || pid==0 { self.incomplete=true; return 1; }
                if self.index(proc_id,thread_id).is_some() || self.objects.iter().any(|x| x.phase!=Phase::Empty && x.phase!=Phase::ThreadRetired && x.tid==tid as i32 && tid!=0) { self.incomplete=true; return 2; }
                let idx=match self.objects.iter().position(|x| x.phase==Phase::Empty) { Some(i)=>i, None=>{self.incomplete=true;return 9} };
                self.objects[idx]=Object { phase:Phase::Allocated,capture,slot:slot as u32,generation,application,
                    process:proc_id,thread:thread_id,exec:application,pid:pid as i32,tid:tid as i32,refs:1,
                    process_terminal:false,process_retired:false,main_storage:true,zombie:false,vm_owned:true };
                self.emit("ALLOC",proc_id,thread_id,0,0); 0
            },
            "capture_end" => {
                self.ended=true; self.emit("CAPTURE_END",0,0,0,0);
                if self.objects.iter().any(|x| x.phase!=Phase::Empty && (!x.process_retired || x.phase!=Phase::ThreadRetired)) { self.incomplete=true; }
                0
            },
            "launcher_loss" => { self.emit("LAUNCHER_LOSS",0,0,0,0); 0 },
            _ => {
                let idx=match if thread==0 { self.process_index(process) } else { self.index(process,thread) } { Some(i)=>i,None=>{self.incomplete=true;return 1} };
                let mut event: Option<(&str,u64,u64)>=None;
                let result = {
                    let x=&mut self.objects[idx];
                    match op {
                        "birth" if x.phase==Phase::Allocated => { x.phase=Phase::Born; event=Some(("BIRTH",0,0)); 0 },
                        "birth" => 2,
                        "runnable" if x.phase==Phase::Born => { x.phase=Phase::Runnable; event=Some(("RUNNABLE",0,0)); 0 },
                        "runnable" => 3,
                        "abort" if x.phase==Phase::Allocated => { x.phase=Phase::Aborted; event=Some(("ABORT",n[3],0)); 0 },
                        "abort" => 3,
                        "add_ref" if x.phase!=Phase::ThreadRetired => match x.refs.checked_add(1) { Some(v)=>{x.refs=v;0},None=>7 },
                        "drop_ref" if x.refs>0 => { x.refs-=1; 0 },
                        "drop_ref" => 4,
                        "thread_terminal" if matches!(x.phase,Phase::Born|Phase::Runnable) => { x.phase=Phase::ThreadTerminal; event=Some(("THREAD_TERMINAL",n[3],n[6])); 0 },
                        "thread_terminal" => 2,
                        "process_terminal" if !x.process_terminal && !matches!(x.phase,Phase::Allocated|Phase::Aborted) => { x.process_terminal=true; event=Some(("PROCESS_TERMINAL",n[3],n[6])); 0 },
                        "process_terminal" => 2,
                        "retire_begin" if x.refs==0 && matches!(x.phase,Phase::ThreadTerminal|Phase::Aborted) => { x.phase=Phase::RetireBegun; event=Some(("RETIRE_BEGIN",0,0)); 0 },
                        "retire_begin" if n[3]==1 && x.phase==Phase::Aborted => { x.phase=Phase::RetireBegun; event=Some(("RETIRE_BEGIN",0,1)); 0 },
                        "retire_begin" => 4,
                        "thread_retire" if x.phase==Phase::RetireBegun => { x.phase=Phase::ThreadRetired; event=Some(("THREAD_RETIRE",0,0)); 0 },
                        "thread_retire" => 5,
                        "release_main" => { x.main_storage=false; x.vm_owned=false; 0 },
                        "set_zombie" => { x.zombie=true; 0 },
                        "clear_zombie" => { x.zombie=false; 0 },
                        "process_retire" if x.process_terminal && x.phase==Phase::ThreadRetired && !x.main_storage && !x.zombie && !x.vm_owned => { x.process_retired=true; event=Some(("PROCESS_RETIRE",0,0)); 0 },
                        "process_retire" if x.phase==Phase::ThreadRetired && !x.main_storage && !x.zombie && !x.vm_owned && matches!(x.phase,Phase::ThreadRetired) => { x.process_retired=true; event=Some(("PROCESS_RETIRE",0,1)); 0 },
                        "process_retire" => 8,
                        _ => 1,
                    }
                };
                if let Some((kind,raw,branch))=event { self.emit(kind,process,thread,raw,branch); }
                result
            }
        }
    }
    fn snapshot(&self, opid: u64, result: u32) {
        println!("R {} {} {}",self.operations,opid,result);
        for x in self.objects.iter().filter(|x| x.phase!=Phase::Empty) {
            println!("S {} {} {} {} {} {} {} {} {} {} {}",x.capture,x.slot,x.generation,x.application,x.process,x.thread,x.exec,x.pid,x.tid,x.refs,x.phase as u8);
        }
    }
}

fn main() {
    let stdin=io::stdin(); let mut lines=stdin.lock().lines();
    let header=match lines.next() { Some(Ok(x))=>x,_=>std::process::exit(2) };
    let h:Vec<_>=header.split_whitespace().collect();
    if h.len()!=2 || h[0]!="MODEL1" { std::process::exit(2); }
    let capacity=match h[1].parse::<u64>() { Ok(x)=>x,_=>std::process::exit(2) };
    let mut model=match Model::new(capacity) { Some(x)=>x,None=>std::process::exit(2) };
    for line in lines { let line=match line { Ok(x)=>x,Err(_)=>std::process::exit(2) }; let f:Vec<_>=line.split_whitespace().collect();
        if f.len()!=10 { std::process::exit(2); } let opid=match f[1].parse::<u64>() { Ok(x) if x>0=>x,_=>std::process::exit(2) };
        let result=model.apply(&f); model.snapshot(opid,result);
    }
    println!("Z {} {} {}",u8::from(model.ended && !model.incomplete),model.lost,model.attempts);
}
