// SPDX-License-Identifier: GPL-2.0-only
//! Direct shared-observer tests. No native Memory, guest bytes, or kernel claims.
extern crate self as kernel;
pub static OBSERVER_LOG: std::sync::Mutex<Vec<String>> = std::sync::Mutex::new(Vec::new());
#[macro_export]
macro_rules! pr_info {
    ($($args:tt)*) => {{ $crate::OBSERVER_LOG.lock().unwrap().push(format!($($args)*)); }};
}
#[allow(dead_code)]
#[path = "stability-owner-observer/stability_observer.rs"]
mod stability_observer;

#[test]
fn bounded_inventory_and_original_serial_lifetime_are_explicit_and_fail_closed() {
    use stability_observer as observer;
    let tag = observer::Tag {
        index: 3,
        serial: Some(73),
        physical: 0x8000,
        end: 0x8028,
    };
    let mut rows = observer::Rows::<observer::Tag, 2>::new();
    rows.push(tag);
    rows.push(observer::Tag {
        serial: Some(74),
        ..tag
    });
    assert!(rows.complete());
    rows.push(observer::Tag {
        serial: Some(75),
        ..tag
    });
    assert_eq!((rows.total, rows.used), (3, 2));
    assert!(!rows.complete());
    assert_eq!(rows.rows[0], Some(tag));
    assert_eq!(rows.rows[1].unwrap().serial, Some(74));

    let selection = observer::Selection {
        os: 2,
        generation: 19,
        pid: 700,
        cpu: 0,
        requester: 700,
        application: 91,
        worker: 92,
        delivery: 93,
        ledger_serial: 73,
        ledger_index: 3,
        response: 0x8000,
        response_end: 0x8028,
    };
    assert_eq!(observer::selected(), None);
    assert_eq!(observer::select(selection), Ok(selection));
    assert_eq!(observer::select(selection), Ok(selection));
    assert_eq!(
        observer::select(observer::Selection {
            ledger_serial: 74,
            ..selection
        }),
        Err(-16)
    );
    let claim = observer::Claim {
        os: 2,
        generation: 19,
        response: tag,
        payload: None,
    };
    let sequence = observer::begin(observer::Phase::BlockedRead, selection).unwrap();
    assert!(observer::end(sequence, true));
    assert!(OBSERVER_LOG
        .lock()
        .unwrap()
        .iter()
        .any(|line| line.contains("address_calls=0") && line.contains("release_calls=0")));

    observer::address(claim);
    observer::address(observer::Claim {
        generation: 20,
        ..claim
    });
    observer::address(observer::Claim {
        response: observer::Tag {
            serial: Some(74),
            ..tag
        },
        ..claim
    });
    observer::payload(claim, 16);
    observer::release(claim);
    let next = observer::begin(observer::Phase::Recovery, selection).unwrap();
    assert_eq!(next, sequence + 1);
    assert!(observer::end(next, true));
    assert!(OBSERVER_LOG
        .lock()
        .unwrap()
        .iter()
        .any(|line| line.contains("address_calls=1")
            && line.contains("payload_calls=1")
            && line.contains("payload_bytes=16")
            && line.contains("release_calls=1")
            && line.contains("after_release_calls=0")
            && line.contains("duplicate_release=0")));

    observer::address(claim);
    observer::release(claim);
    let late = observer::begin(observer::Phase::Terminal, selection).unwrap();
    assert!(!observer::end(late, true));
    assert!(
        OBSERVER_LOG
            .lock()
            .unwrap()
            .iter()
            .any(|line| line.contains("after_release_calls=1")
                && line.contains("duplicate_release=1"))
    );
    assert!(OBSERVER_LOG
        .lock()
        .unwrap()
        .iter()
        .any(|line| line.contains("result=COUNTER_FAIL")));
    let incomplete = observer::begin(observer::Phase::TerminalPlusFive, selection).unwrap();
    assert!(!observer::end(incomplete, false));
    assert!(OBSERVER_LOG
        .lock()
        .unwrap()
        .iter()
        .any(|line| line.contains("result=INCOMPLETE_FAIL")));
}
