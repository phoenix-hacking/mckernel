// SPDX-License-Identifier: GPL-2.0

#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/abi/x86_64.rs"]
mod abi;

#[path = "../../../host-kernel/native-rust/ikc_queue.rs"]
mod ikc_queue;

#[cfg(test)]
mod tests {
    use super::abi::IhkIkcQueueHead;
    use super::ikc_queue::{QueueError, SharedQueue};
    use std::collections::BTreeSet;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Mutex;

    #[repr(C, align(64))]
    struct Storage<const N: usize>([u8; N]);

    #[test]
    fn sequential_capacity_fifo_and_legacy_results() {
        let mut storage = Storage([0; 576]);
        let queue = SharedQueue::initialize(&mut storage.0, 7, 3, 64).unwrap();
        assert_eq!(queue.snapshot().unwrap().packet_count, 8);
        assert!(queue.is_empty().unwrap());
        assert_eq!(QueueError::Empty.legacy_status(), -1);
        assert_eq!(QueueError::Full.legacy_status(), -16);

        for value in 0_u64..7 {
            let mut packet = [0_u8; 64];
            packet[..8].copy_from_slice(&value.to_le_bytes());
            queue.try_enqueue(&packet).unwrap();
        }
        assert!(queue.is_full().unwrap());
        assert_eq!(queue.try_enqueue(&[0; 64]), Err(QueueError::Full));

        for expected in 0_u64..7 {
            let mut packet = [0_u8; 64];
            queue.try_dequeue(&mut packet).unwrap();
            assert_eq!(u64::from_le_bytes(packet[..8].try_into().unwrap()), expected);
        }
        assert_eq!(queue.try_dequeue(&mut [0; 64]), Err(QueueError::Empty));
        assert!(queue.is_empty().unwrap());
    }

    #[test]
    fn counters_wrap_without_changing_slot_order() {
        let mut storage = Storage([0; 320]);
        let head = storage.0.as_mut_ptr().cast::<IhkIkcQueueHead>();
        let queue = SharedQueue::initialize(&mut storage.0, 1, 2, 64).unwrap();
        drop(queue);
        unsafe {
            (*head).read_offset = u64::MAX;
            (*head).max_read_offset = u64::MAX;
            (*head).write_offset = u64::MAX;
        }
        let queue = unsafe { SharedQueue::attach(head, 320) }.unwrap();
        let mut sent = [0_u8; 64];
        sent[..8].copy_from_slice(&0xfeed_face_cafe_beef_u64.to_le_bytes());
        queue.try_enqueue(&sent).unwrap();
        let mut received = [0_u8; 64];
        queue.try_dequeue(&mut received).unwrap();
        assert_eq!(sent, received);
        let state = queue.snapshot().unwrap();
        assert_eq!(state.read, 0);
        assert_eq!(state.published, 0);
        assert_eq!(state.reserved, 0);
    }

    #[test]
    fn malformed_metadata_and_short_packets_fail_closed() {
        let mut storage = Storage([0; 320]);
        let head = storage.0.as_mut_ptr().cast::<IhkIkcQueueHead>();
        let queue = SharedQueue::initialize(&mut storage.0, 1, 2, 64).unwrap();
        assert_eq!(queue.try_enqueue(&[0; 63]), Err(QueueError::Invalid));
        drop(queue);
        unsafe {
            (*head).queue_size += 1;
        }
        assert_eq!(
            unsafe { SharedQueue::attach(head, 320) }.err(),
            Some(QueueError::Corrupt)
        );
        assert_eq!(QueueError::Corrupt.legacy_status(), -117);
    }

    #[test]
    fn concurrent_producers_and_consumers_transfer_each_packet_once() {
        const PRODUCERS: usize = 4;
        const CONSUMERS: usize = 4;
        const PER_PRODUCER: usize = 1_000;
        const TOTAL: usize = PRODUCERS * PER_PRODUCER;
        let storage = Box::leak(Box::new(Storage([0; 8192])));
        let queue = SharedQueue::initialize(&mut storage.0, 9, 4, 16).unwrap();
        let consumed = AtomicUsize::new(0);
        let values = Mutex::new(BTreeSet::new());

        std::thread::scope(|scope| {
            for _ in 0..CONSUMERS {
                let consumer = &queue;
                let consumed_ref = &consumed;
                let values_ref = &values;
                scope.spawn(move || {
                    while consumed_ref.load(Ordering::Acquire) < TOTAL {
                        let mut packet = [0_u8; 16];
                        match consumer.try_dequeue(&mut packet) {
                            Ok(()) => {
                                let producer =
                                    u64::from_le_bytes(packet[..8].try_into().unwrap());
                                let sequence =
                                    u64::from_le_bytes(packet[8..].try_into().unwrap());
                                assert!(values_ref.lock().unwrap().insert((producer, sequence)));
                                consumed_ref.fetch_add(1, Ordering::Release);
                            }
                            Err(QueueError::Empty | QueueError::Busy) => {
                                std::thread::yield_now()
                            }
                            result => panic!("unexpected dequeue result: {result:?}"),
                        }
                    }
                });
            }

            for producer in 0..PRODUCERS {
                let shared = &queue;
                scope.spawn(move || {
                    for sequence in 0..PER_PRODUCER {
                        let mut packet = [0_u8; 16];
                        packet[..8].copy_from_slice(&(producer as u64).to_le_bytes());
                        packet[8..].copy_from_slice(&(sequence as u64).to_le_bytes());
                        loop {
                            match shared.try_enqueue(&packet) {
                                Ok(()) => break,
                                Err(QueueError::Full) => std::thread::yield_now(),
                                result => panic!("unexpected enqueue result: {result:?}"),
                            }
                        }
                    }
                });
            }

        });
        assert_eq!(consumed.load(Ordering::Relaxed), TOTAL);
        assert_eq!(values.into_inner().unwrap().len(), TOTAL);
        assert!(queue.is_empty().unwrap());
    }
}
