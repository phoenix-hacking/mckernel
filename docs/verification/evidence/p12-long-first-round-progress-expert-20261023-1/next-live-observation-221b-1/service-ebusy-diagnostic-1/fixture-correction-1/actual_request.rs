const REQUEST_BYTES:usize=72;const RESPONSE_BYTES:usize=40;pub(crate) const REQUEST_MESSAGE:i32=4;
#[derive(Clone,Debug,Eq,PartialEq)]
pub(crate) struct Request {
    cpu: i32,
    pid: i32,
    requester: i32,
    target: i32,
    response: u64,
    bytes: [u8; REQUEST_BYTES],
}
impl Request {
    pub(crate) fn decode(packet: &[u8], cpus: usize) -> Result<Self, i32> {
        if packet.len() != 128 {
            return Err(-22);
        }
        let integer = |offset| i32::from_le_bytes(packet[offset..offset + 4].try_into().unwrap());
        let word = |offset| u64::from_le_bytes(packet[offset..offset + 8].try_into().unwrap());
        let cpu = integer(24);
        let pid = integer(32);
        let requester = integer(48);
        let target = integer(52);
        let response = word(120);
        if integer(8) != REQUEST_MESSAGE
            || cpu < 0
            || cpu as usize >= cpus
            || pid <= 0
            || requester <= 0
            || target < 0
            || word(56) != 1
            || response == 0
            || response % 8 != 0
            || response.checked_add(RESPONSE_BYTES as u64).is_none()
        {
            return Err(-22);
        }
        Ok(Self {
            cpu,
            pid,
            requester,
            target,
            response,
            bytes: packet[48..120].try_into().unwrap(),
        })
    }
    pub(crate) fn cpu(&self) -> i32 {
        self.cpu
    }
    pub(crate) fn pid(&self) -> i32 {
        self.pid
    }
    pub(crate) fn requester(&self) -> i32 {
        self.requester
    }
    pub(crate) fn target(&self) -> i32 {
        self.target
    }
    pub(crate) fn response(&self) -> u64 {
        self.response
    }
    pub(crate) fn number(&self) -> u64 {
        u64::from_le_bytes(self.bytes[16..24].try_into().unwrap())
    }
}
