// SPDX-License-Identifier: GPL-2.0
#![allow(dead_code)]

#[path = "../../../host-kernel/native-rust/abi/x86_64.rs"]
mod abi;
#[path = "../../../host-kernel/native-rust/ikc_master.rs"]
mod ikc_master;

use std::sync::{Arc, Barrier};
use std::thread;

use abi::{
    IHK_IKC_MASTER_MSG_CONNECT, IHK_IKC_MASTER_MSG_CONNECT_REPLY,
    IHK_IKC_MASTER_MSG_DISCONNECT, IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL,
    IKC_FLAG_DESTROY_ACKED, IKC_FLAG_DESTROYING, IKC_FLAG_ENABLED, IKC_FLAG_NO_COPY,
    IhkIkcMasterPacket, IhkIkcPacketHeader,
};
use ikc_master::*;

fn listener(port: i32, direction: ListenerDirection) -> ListenerSpec {
    ListenerSpec::try_new(port, 64, 4096, 0x1234, direction, 0xcafe).unwrap()
}

fn packet(message: u32, reference: u32, parameters: [u64; 5]) -> IhkIkcMasterPacket {
    IhkIkcMasterPacket {
        header: IhkIkcPacketHeader {
            channel: std::ptr::null_mut(),
        },
        message,
        reference,
        parameters,
    }
}

fn connect_packet(reference: u32, port: u32, size: u32, magic: u32) -> IhkIkcMasterPacket {
    packet(
        IHK_IKC_MASTER_MSG_CONNECT,
        reference,
        [
            (u64::from(size) << 32) | u64::from(port),
            0x1000,
            0x2000,
            0x3000,
            (7_u64 << 32) | u64::from(magic),
        ],
    )
}

#[test]
fn registry_collision_generation_and_validation() {
    let registry = ListenerRegistry::<8>::new();
    assert_eq!(
        ListenerSpec::try_new(-1, 64, 4096, 1, ListenerDirection::Send, 1),
        Err(MasterError::Invalid)
    );
    assert_eq!(
        ListenerSpec::try_new(512, 64, 4096, 1, ListenerDirection::Send, 1),
        Err(MasterError::Invalid)
    );
    assert_eq!(
        ListenerSpec::try_new(1, 0, 4096, 1, ListenerDirection::Send, 1),
        Err(MasterError::Invalid)
    );
    let first = registry.register(listener(3, ListenerDirection::Send)).unwrap();
    assert_eq!(
        registry.register(listener(3, ListenerDirection::Receive)),
        Err(MasterError::Busy)
    );
    let lease = registry.acquire(3).unwrap();
    assert_eq!(lease.spec(), listener(3, ListenerDirection::Send));
    drop(lease);
    assert_eq!(
        registry.begin_unregister(first),
        Ok(UnregisterState::Removed)
    );
    assert!(matches!(registry.acquire(3), Err(MasterError::NoEntry)));
    let second = registry.register(listener(3, ListenerDirection::Receive)).unwrap();
    assert_ne!(first.generation, second.generation);
    assert_eq!(
        registry.begin_unregister(first),
        Err(MasterError::Stale)
    );
}

#[test]
fn unregister_drains_live_accept_lease_before_reuse() {
    let registry = Arc::new(ListenerRegistry::<8>::new());
    let token = registry
        .register(listener(2, ListenerDirection::Receive))
        .unwrap();
    let lease = registry.acquire(2).unwrap();
    assert_eq!(
        registry.begin_unregister(token),
        Ok(UnregisterState::Pending)
    );
    assert!(matches!(registry.acquire(2), Err(MasterError::NoEntry)));
    assert_eq!(
        registry.finish_unregister(token),
        Ok(UnregisterState::Pending)
    );
    assert_eq!(lease.spec().owner, 0xcafe);
    drop(lease);
    let finalizers = Arc::new(Barrier::new(3));
    let results = thread::scope(|scope| {
        let first_registry = Arc::clone(&registry);
        let first_barrier = Arc::clone(&finalizers);
        let first = scope.spawn(move || {
            first_barrier.wait();
            first_registry.finish_unregister(token)
        });
        let second_registry = Arc::clone(&registry);
        let second_barrier = Arc::clone(&finalizers);
        let second = scope.spawn(move || {
            second_barrier.wait();
            second_registry.finish_unregister(token)
        });
        finalizers.wait();
        [first.join().unwrap(), second.join().unwrap()]
    });
    assert_eq!(
        results
            .iter()
            .filter(|result| **result == Ok(UnregisterState::Removed))
            .count(),
        1
    );
    assert!(results.iter().all(|result| matches!(
        result,
        Ok(UnregisterState::Removed | UnregisterState::Pending) | Err(MasterError::Stale)
    )));
    let replacement = registry
        .register(listener(2, ListenerDirection::Send))
        .unwrap();
    let replacement_lease = registry.acquire(2).unwrap();
    assert_eq!(replacement_lease.spec(), listener(2, ListenerDirection::Send));
    drop(replacement_lease);
    assert_eq!(
        registry.begin_unregister(replacement),
        Ok(UnregisterState::Removed)
    );
}

#[test]
fn concurrent_lookups_finish_before_listener_reuse() {
    let registry = Arc::new(ListenerRegistry::<8>::new());
    let token = registry
        .register(listener(1, ListenerDirection::Receive))
        .unwrap();
    let entered = Arc::new(Barrier::new(9));
    let release = Arc::new(Barrier::new(9));
    let workers: Vec<_> = (0..8)
        .map(|_| {
            let registry = Arc::clone(&registry);
            let entered = Arc::clone(&entered);
            let release = Arc::clone(&release);
            thread::spawn(move || {
                let lease = registry.acquire(1).unwrap();
                entered.wait();
                release.wait();
                assert_eq!(lease.token(), token);
            })
        })
        .collect();
    entered.wait();
    assert_eq!(
        registry.begin_unregister(token),
        Ok(UnregisterState::Pending)
    );
    assert!(matches!(registry.acquire(1), Err(MasterError::NoEntry)));
    release.wait();
    for worker in workers {
        worker.join().unwrap();
    }
    assert_eq!(
        registry.finish_unregister(token),
        Ok(UnregisterState::Removed)
    );
}

#[test]
fn router_preserves_master_messages_errors_release_and_lease() {
    let registry = ListenerRegistry::<8>::new();
    let token = registry
        .register(listener(4, ListenerDirection::Receive))
        .unwrap();
    let router = MasterRouter::new(&registry);

    let decision = router.route(
        &connect_packet(9, 4, 64, 0x1234),
        ExecutionContext::Interrupt,
    );
    assert!(decision.release_packet);
    assert_eq!(decision.context, ExecutionContext::Interrupt);
    let plan = match decision.action {
        RouteAction::Accept(plan) => plan,
        _ => panic!("expected accept"),
    };
    assert_eq!(plan.listener_token(), token);
    assert_eq!(plan.regular_channel_cpu(), Some(7));
    assert_eq!(
        registry.begin_unregister(token),
        Ok(UnregisterState::Pending)
    );
    let reply = plan
        .connect_reply(Ok(AcceptSuccess {
            receive_queue: 0x4000,
            accepted_channel_cookie: 0x5000,
        }))
        .unwrap()
        .packet();
    assert_eq!(reply.message, IHK_IKC_MASTER_MSG_CONNECT_REPLY);
    assert_eq!(reply.parameters, [0, 0x4000, 0x3000, 0x5000, 0]);
    assert_eq!(
        registry.finish_unregister(token),
        Ok(UnregisterState::Removed)
    );
    let replacement = registry
        .register(listener(4, ListenerDirection::Receive))
        .unwrap();

    for (bad, errno) in [
        (connect_packet(10, 511, 64, 0x1234), 111_u64),
        (connect_packet(10, 4, 64, 0x9999), 111_u64),
        (connect_packet(10, 4, 32, 0x1234), 103_u64),
    ] {
        let result = router.route(&bad, ExecutionContext::Interrupt);
        match result.action {
            RouteAction::SendConnectError(reply) => assert_eq!(reply.parameters[0], errno),
            _ => panic!("expected connect error"),
        }
        assert!(result.release_packet);
    }
    assert_eq!(
        registry.begin_unregister(replacement),
        Ok(UnregisterState::Removed)
    );
    let callback_listener = registry
        .register(listener(4, ListenerDirection::Receive))
        .unwrap();
    let callback_plan = match router
        .route(
            &connect_packet(11, 4, 64, 0x1234),
            ExecutionContext::Interrupt,
        )
        .action
    {
        RouteAction::Accept(plan) => plan,
        _ => panic!("expected callback accept plan"),
    };
    let callback_reply = callback_plan.connect_reply(Err(-12)).unwrap();
    assert_eq!(callback_reply.parameters[0], 12);
    let invalid_callback_plan = match router
        .route(
            &connect_packet(12, 4, 64, 0x1234),
            ExecutionContext::Interrupt,
        )
        .action
    {
        RouteAction::Accept(plan) => plan,
        _ => panic!("expected callback validation plan"),
    };
    assert_eq!(
        invalid_callback_plan.connect_reply(Err(5)),
        Err(MasterError::Protocol)
    );
    assert_eq!(
        registry.begin_unregister(callback_listener),
        Ok(UnregisterState::Removed)
    );

    let no_channel = router.route(
        &packet(IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL, 1, [0; 5]),
        ExecutionContext::Interrupt,
    );
    assert!(matches!(
        no_channel.action,
        RouteAction::Reject(MasterError::NoEntry)
    ));
    let channel = router.route(
        &packet(
            IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL,
            1,
            [0, 0, 0, 0xbeef, 0],
        ),
        ExecutionContext::Interrupt,
    );
    assert!(matches!(
        channel.action,
        RouteAction::DeliverPacket {
            channel_cookie: 0xbeef
        }
    ));
    let wake = router.route(
        &packet(IHK_IKC_MASTER_MSG_CONNECT_REPLY, 77, [0; 5]),
        ExecutionContext::Interrupt,
    );
    assert!(matches!(
        wake.action,
        RouteAction::WakeReply {
            message: IHK_IKC_MASTER_MSG_CONNECT_REPLY,
            reference: 77
        }
    ));
    let disconnect = router.route(
        &packet(
            IHK_IKC_MASTER_MSG_DISCONNECT,
            78,
            [0, 0, 0, 0xabcd, 0],
        ),
        ExecutionContext::Interrupt,
    );
    assert!(matches!(
        disconnect.action,
        RouteAction::ObserveDisconnect {
            channel_cookie: 0xabcd,
            reference: 78
        }
    ));
    let arch = router.route(&packet(0xdead, 0, [0; 5]), ExecutionContext::Interrupt);
    assert!(matches!(arch.action, RouteAction::Architecture { message: 0xdead }));
}

#[test]
fn connect_transaction_maps_send_interrupt_error_and_success() {
    let request = ConnectRequest::try_new(
        99,
        17,
        64,
        0x1000,
        0x2000,
        0x3000,
        -7,
        -2,
    )
    .unwrap()
    .master_packet();
    assert_eq!(request.message, IHK_IKC_MASTER_MSG_CONNECT);
    assert_eq!(request.reference, 99);
    assert_eq!(
        request.parameters,
        [
            (64_u64 << 32) | 17,
            0x1000,
            0x2000,
            0x3000,
            (u64::from((-2_i32) as u32) << 32) | u64::from((-7_i32) as u32),
        ]
    );
    assert_eq!(
        ConnectRequest::try_new(1, -1, 64, 1, 2, 3, 4, 5),
        Err(MasterError::Invalid)
    );

    let mut send_failure = ConnectTransaction::new(1);
    assert_eq!(
        send_failure.sent(-5),
        Ok(ConnectAction::Cleanup { status: -16 })
    );
    assert_eq!(send_failure.phase(), ConnectPhase::Failed);

    let mut interrupted = ConnectTransaction::new(2);
    assert_eq!(interrupted.sent(0), Ok(ConnectAction::WaitForReply));
    assert_eq!(
        interrupted.interrupted(),
        Ok(ConnectAction::Cleanup { status: -4 })
    );

    let mut refused = ConnectTransaction::new(3);
    refused.sent(0).unwrap();
    assert_eq!(
        refused.reply(&packet(
            IHK_IKC_MASTER_MSG_CONNECT_REPLY,
            3,
            [111, 0, 0, 0, 0],
        )),
        Ok(ConnectAction::Cleanup { status: -111 })
    );

    let mut success = ConnectTransaction::new(4);
    success.sent(0).unwrap();
    assert_eq!(
        success.reply(&packet(
            IHK_IKC_MASTER_MSG_CONNECT_REPLY,
            4,
            [0, 0x1000, 0x2000, 0x3000, 0],
        )),
        Ok(ConnectAction::Publish {
            remote_queue: 0x1000,
            echoed_local_cookie: 0x2000,
            remote_channel_cookie: 0x3000,
        })
    );
    assert_eq!(success.phase(), ConnectPhase::Connected);
    assert_eq!(
        success.reply(&packet(IHK_IKC_MASTER_MSG_CONNECT_REPLY, 4, [0; 5])),
        Err(MasterError::Protocol)
    );
}

#[test]
fn disconnect_has_one_initiator_and_preserves_non_status_flags() {
    let channel = Arc::new(ChannelLifecycle::new(IKC_FLAG_ENABLED | IKC_FLAG_NO_COPY));
    let barrier = Arc::new(Barrier::new(9));
    let workers: Vec<_> = (0..8)
        .map(|_| {
            let channel = Arc::clone(&channel);
            let barrier = Arc::clone(&barrier);
            thread::spawn(move || {
                barrier.wait();
                channel.begin_disconnect()
            })
        })
        .collect();
    barrier.wait();
    let results: Vec<_> = workers.into_iter().map(|worker| worker.join().unwrap()).collect();
    assert_eq!(results.iter().filter(|result| result.is_ok()).count(), 1);
    assert_eq!(
        results
            .iter()
            .filter(|result| **result == Err(MasterError::Busy))
            .count(),
        7
    );
    assert_eq!(
        channel.observe_disconnect(),
        IncomingDisconnectAction::WakeDisconnectWaiter
    );
    let flags = channel.flags();
    assert_eq!(flags & IKC_FLAG_ENABLED, 0);
    assert_ne!(flags & IKC_FLAG_DESTROYING, 0);
    assert_ne!(flags & IKC_FLAG_DESTROY_ACKED, 0);
    assert_ne!(flags & IKC_FLAG_NO_COPY, 0);
    assert!(channel.destroy_ready());

    let remote_first = ChannelLifecycle::new(IKC_FLAG_ENABLED);
    assert_eq!(
        remote_first.observe_disconnect(),
        IncomingDisconnectAction::InitiateReciprocalDisconnect
    );
    assert_eq!(
        remote_first.begin_disconnect(),
        Ok(DisconnectAction::SendWithoutWait)
    );
}
