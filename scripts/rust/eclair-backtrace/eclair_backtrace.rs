// Based on scripts/eclair-dump-backtrace.exp.in, original retained as reference.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use std::io;
#[derive(Clone,Copy,Debug,PartialEq,Eq)]pub enum State {Init,ThreadsList,ThreadChosen,ThreadBt,ThreadSkip,UnknownPrompt,UnknownQuit,Finished}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]enum Event{Quit,Unknown,UnknownFrame,Prompt,More,Continue,NotKnown}
const PATTERNS:[(&[u8],Event);7]=[(b"Quit anyway? (y or n) ",Event::Quit),(b"Unknown thread",Event::Unknown),(b"in ?? ()",Event::UnknownFrame),(b"(eclair) ",Event::Prompt),(b"Type <RET> for more, q to quit, c to continue without paging--",Event::More),(b"Type <return> to continue, or q <return> to quit",Event::Continue),(b" not known.",Event::NotKnown)];
pub struct Session {pub state:State,pub thread_id:u64,pending:Vec<u8>}
impl Default for Session {fn default()->Self{Self{state:State::Init,thread_id:0,pending:Vec::new()}}}
impl Session{
 pub fn feed(&mut self,bytes:&[u8])->Result<Vec<String>,String>{self.pending.extend_from_slice(bytes);let mut sends=Vec::new();loop{
  let mut found=None;for (order,(pattern,event)) in PATTERNS.iter().enumerate(){if let Some(at)=self.pending.windows(pattern.len()).position(|v|v==*pattern){if found.map_or(true,|(best,best_order,_,_)|at<best||(at==best&&order<best_order)){found=Some((at,order,pattern.len(),*event));}}}
  let Some((at,_,len,event))=found else{let keep=PATTERNS.iter().map(|(s,_)|s.len()).max().unwrap()-1;if self.pending.len()>keep{self.pending.drain(..self.pending.len()-keep);}break};
  self.pending.drain(..at+len);
  if self.state==State::Finished{break}
  // The reference's nested expects after "not known." wait for only these two
  // prompts; ordinary pagination/state handlers must not consume that transition.
  if self.state==State::UnknownPrompt{if event==Event::Prompt{sends.push("quit\r".into());self.state=State::UnknownQuit;}continue}
  if self.state==State::UnknownQuit{if event==Event::Quit{sends.push("y\r".into());self.state=State::Finished;}continue}
  match event{
   Event::Quit=>{sends.push("y\r".into());self.state=State::Finished;},
   Event::Unknown=>sends.push("quit\r".into()),
   Event::UnknownFrame=>if matches!(self.state,State::ThreadChosen|State::ThreadBt){self.state=State::ThreadSkip},
   Event::Prompt=>match self.state{State::Init=>{self.state=State::ThreadsList;sends.push("info threads\r".into());},State::ThreadsList|State::ThreadBt|State::ThreadSkip=>{self.thread_id=self.thread_id.checked_add(1).ok_or("thread index overflow")?;self.state=State::ThreadChosen;sends.push(format!("thread {}\r",self.thread_id));},State::ThreadChosen=>{self.state=State::ThreadBt;sends.push("bt\r".into());},_=>{}},
   Event::More=>match self.state{State::ThreadsList=>sends.push("\r".into()),State::ThreadBt|State::ThreadSkip=>sends.push("q\r".into()),_=>{}},
   Event::Continue=>match self.state{State::ThreadsList|State::ThreadBt=>sends.push("\r".into()),State::ThreadSkip=>sends.push("q\r".into()),_=>{}},
   Event::NotKnown=>self.state=State::UnknownPrompt,
  }
 }Ok(sends)}
}
pub trait Terminal{fn read(&mut self)->io::Result<Vec<u8>>;fn send(&mut self,text:&str)->io::Result<()>;fn transcript(&mut self,bytes:&[u8])->io::Result<()>;fn wait(&mut self)->io::Result<()>;}
pub fn drive(t:&mut dyn Terminal)->Result<(),String>{let mut session=Session::default();loop{let bytes=t.read().map_err(|e|e.to_string())?;if bytes.is_empty(){t.wait().map_err(|e|e.to_string())?;return Ok(())}t.transcript(&bytes).map_err(|e|e.to_string())?;for text in session.feed(&bytes)?{t.send(&text).map_err(|e|e.to_string())?;}if session.state==State::Finished{t.wait().map_err(|e|e.to_string())?;return Ok(())}}}
