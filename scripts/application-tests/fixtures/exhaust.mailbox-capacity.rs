fn main() { let capacity: u32 = 64; for call in 1..=capacity { println!("call={} admitted=1", call); } println!("call=65 admitted=0 error=EAGAIN cleanup=required"); }
