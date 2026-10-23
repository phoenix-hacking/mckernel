// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use std::sync::atomic::{AtomicU64, Ordering};
const CONTROL_PACKET_BYTES:usize=128;
mod abi { pub const SCD_MSG_EVENTFD:i32=0x46; }
type Result=core::result::Result<(),i32>;
const EINVAL:i32=-22;
fn errno(x:i32)->i32{x}
macro_rules! pr_info { ($fmt:expr, $($x:expr),* $(,)?) => {{let _=format_args!($fmt,$($x),*);}}; }
struct Owner;impl Owner{fn slot(&self)->u32{0}fn generation(&self)->u64{1}}
// EVENTFD is a one-way guest notification, not a sysfs/RPC request. The
// native IHK ioctl surface does not admit eventfd subscribers yet; as with
// legacy ihk_os_eventfd's empty subscriber list, receiving a valid notification
// must not poison the shared application transport. Retain typed observations;
// do not invent a subscriber delivery, guest ACK, cleanup or terminal success.
fn eventfd_notification(
    packet: &[u8; CONTROL_PACKET_BYTES],
) -> core::result::Result<Option<(usize, i32)>, i32> {
    if i32::from_le_bytes(packet[8..12].try_into().unwrap()) != abi::SCD_MSG_EVENTFD {
        return Ok(None);
    }
    let kind = i32::from_le_bytes(packet[24..28].try_into().unwrap());
    let index = match kind {
        0 => 0,   // IHK_OS_EVENTFD_TYPE_OOM
        2 => 1,   // IHK_OS_EVENTFD_TYPE_STATUS
        101 => 2, // IHK_OS_EVENTFD_TYPE_KMSG
        _ => return Err(-22),
    };
    Ok(Some((index, kind)))
}


struct Runtime{owner:Owner, eventfd_notifications:[AtomicU64;3] }
impl Runtime {
    fn dispatch(&self, port: i32, packet: &[u8; CONTROL_PACKET_BYTES]) -> Result {
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        if port != 503 {
            return Err(EINVAL);
        }
        if let Some((index, kind)) = eventfd_notification(packet).map_err(errno)? {
            let sequence = self.eventfd_notifications[index].fetch_add(1, Ordering::Relaxed);
            if sequence < 16 {
                pr_info!("IHK-SMP: guest notification os={} generation={} eventfd_type={} count={} subscribers=0\n",
                    self.owner.slot(), self.owner.generation(), kind, sequence + 1);
            }
            return Ok(());
        }
        let _=message;
        Err(-38) // Existing unknown-message ENOSYS continuation, exercised separately.
    }

fn new()->Self{Self{owner:Owner,eventfd_notifications:[AtomicU64::new(0),AtomicU64::new(0),AtomicU64::new(0)]}}
fn counts(&self)->[u64;3]{std::array::from_fn(|i|self.eventfd_notifications[i].load(Ordering::Relaxed))}
}
fn packet(message:i32,kind:i32)->[u8;128]{let mut p=[0;128];p[8..12].copy_from_slice(&message.to_le_bytes());p[24..28].copy_from_slice(&kind.to_le_bytes());p}
#[test]fn actual_wire_types(){for (i,k) in [0,2,101].into_iter().enumerate(){assert_eq!(eventfd_notification(&packet(0x46,k)),Ok(Some((i,k))));}}
#[test]fn actual_valid_dispatch_does_not_fail_transport(){let r=Runtime::new();for k in [0,2,101]{assert_eq!(r.dispatch(503,&packet(0x46,k)),Ok(()));}assert_eq!(r.counts(),[1,1,1]);}
#[test]fn kmsg_burst_retains_all_counts(){let r=Runtime::new();for _ in 0..100{assert_eq!(r.dispatch(503,&packet(0x46,101)),Ok(()));}assert_eq!(r.counts(),[0,0,100]);}
#[test]fn invalid_type_refuses_no_effect(){let r=Runtime::new();for k in [-1,1,3,100,102,i32::MIN,i32::MAX]{assert_eq!(r.dispatch(503,&packet(0x46,k)),Err(-22));}assert_eq!(r.counts(),[0,0,0]);}
#[test]fn foreign_ports_refuse_before_effect(){let r=Runtime::new();for port in [-1,0,501,502,504]{for k in [0,2,101]{assert_eq!(r.dispatch(port,&packet(0x46,k)),Err(-22));}}assert_eq!(r.counts(),[0,0,0]);}
#[test]fn wrong_message_not_classified(){let r=Runtime::new();for msg in [0,0x13,0x44,0x45,0x47,0x60,-1]{assert_eq!(eventfd_notification(&packet(msg,101)),Ok(None));assert_eq!(r.dispatch(503,&packet(msg,101)),Err(-38));}assert_eq!(r.counts(),[0,0,0]);}
#[test]fn wire_offset_exact_not_adjacent(){let mut p=packet(0x46,101);p[28..32].copy_from_slice(&(-1i32).to_le_bytes());assert_eq!(eventfd_notification(&p),Ok(Some((2,101))));p[24..28].copy_from_slice(&(-1i32).to_le_bytes());p[28..32].copy_from_slice(&101i32.to_le_bytes());assert_eq!(eventfd_notification(&p),Err(-22));}
#[test]fn original_eventfd_fallthrough_reproducer(){let p=packet(0x46,101);let message=i32::from_le_bytes(p[8..12].try_into().unwrap());assert!(!matches!(message,0x30|0x32|0x34|0x36|0x38|0x40));assert_eq!(Runtime::new().dispatch(503,&p),Ok(()));}

mod wire {
#[derive(Clone,Copy)]
pub(crate) enum Kind {
    Create,
    Mkdir,
    Symlink,
    Lookup,
    Unlink,
}
impl Kind{
    pub(crate) const fn from_message(message: i32) -> Option<Self> {
        match message {
            0x30 => Some(Self::Create),
            0x32 => Some(Self::Mkdir),
            0x34 => Some(Self::Symlink),
            0x36 => Some(Self::Lookup),
            0x38 => Some(Self::Unlink),
            _ => None,
        }
    }

}
}
impl Runtime {fn original_unserviced(&self,port:i32,message:i32)->Result {
        let Some(kind) = wire::Kind::from_message(message) else {
            pr_info!(
                "IHK-SMP: unserviced continuing request os={} generation={} port={} message={:x}\n",
                self.owner.slot(),
                self.owner.generation(),
                port,
                message
            );
            return Err(errno(-38));
        };
let _=kind;Ok(())}}
#[test]fn original_actual_sysfs_fallthrough_fails_eventfd(){let r=Runtime::new();assert_eq!(r.original_unserviced(503,0x46),Err(-38));assert_eq!(r.dispatch(503,&packet(0x46,101)),Ok(()));}
