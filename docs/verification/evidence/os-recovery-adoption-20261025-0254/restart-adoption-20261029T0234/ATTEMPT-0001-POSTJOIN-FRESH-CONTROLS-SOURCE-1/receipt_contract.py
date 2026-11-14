"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure current-controller metadata checks. NOT an admission guard or release.
Callers supply bytes; no process, clock, account, filesystem or controller access.
"""
import hashlib
import json
import math

RECEIPT_SHA = '4ff25cbf4135e78c58d973bd3f22c4fc7f305e96cb37bc620ebff0c617cf2db2'
CONFIG_SHA = '15749406bc63e9cfc0f976b8b7433c2e18caad82865766c1a61becfc6d7e9a5c'
PACKET_SHA = '218fcd01f401826e942512b68718d7b990b3e0bebda06fcf7c1f1bbcdcb6e0b1'
MONITOR_SHA = '151d1484b1812012dcefc3cfb7cd4a498aad908c12820919d606997f4af633d6'
THREAD = '01a18a76-4f1e-7900-8ed6-127394e93689'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
WINDOW_SHA = 'c19b84c10175b49f5db8129ef17b5041ceab3ee41ac1a7688e8ff706ceb3f596'
MAXIMA = (1793774133, 1556234.56891299, 1571572.6959598332)
ACTORS = {'watcher': (2659029, '112181497', 2526816),
          'worker': (2659031, '112181511', 2659029),
          'server': (2659033, '112181528', 2659031),
          'guardian': (2659144, '112181699', 2526816),
          'monitor': (2659146, '112181810', 2526816)}

def need(ok, message):
    if not ok:
        raise ValueError(message)

def decode(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            need(k not in result, 'duplicate key')
            result[k] = v
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))

def exact(raw, sha):
    need(type(raw) is bytes and hashlib.sha256(raw).hexdigest() == sha, 'exact frozen bytes')
    return decode(raw)

def validate(receipt_raw, config_raw, packet_raw, monitor_raw):
    r = exact(receipt_raw, RECEIPT_SHA)
    c = exact(config_raw, CONFIG_SHA)
    p = exact(packet_raw, PACKET_SHA)
    m = exact(monitor_raw, MONITOR_SHA)
    need(r['thread_id'] == c['expected_thread'] == m['thread_id'] == THREAD, 'current thread')
    need(r['native_release'] is False and r['guardian_packet_sha256'] == m['guardian_packet_sha256'] == PACKET_SHA
         and r['monitor_arm_sha256'] == MONITOR_SHA, 'receipt publications')
    need(r['deadline_utc'] == c['deadline_utc'] == m['deadline_utc'] == '2026-11-04T06:35:33+00:00', 'deadline')
    caps = r['caps']
    need(caps['boot_id'] == m['boot_id'] == BOOT and
         (caps['deadline'], caps['monotonic_deadline'], caps['boot_deadline']) == MAXIMA, 'earliest caps')
    clock = c['initial_watch_clock']
    need((clock['deadline'], clock['watcher_cutoff_lower'], clock['boot_deadline']) == MAXIMA
         and clock['boot_id'] == BOOT, 'configuration caps')
    need(c['billing_mode'] == 'included_only' and c['initial_credit_budget'] is None
         and c['allow_prepaid_fallback'] is False and c['automatic_credit_purchase'] is False
         and c['api_key_billing'] is False and c['window_sha256'] == m['window_sha256'] == WINDOW_SHA,
         'weekly only')
    need(set(r['binding']) == set(ACTORS), 'actor set')
    for name, identity in ACTORS.items():
        a = r['binding'][name]
        need((a['pid'], a['start'], a['ppid']) == identity and a['state'] in ('R', 'S'), 'recorded actor ' + name)
    need(clock['watcher_pid'] == ACTORS['watcher'][0] and clock['watcher_start'] == ACTORS['watcher'][1], 'watcher binding')
    need(m['review_interval_seconds'] == 1200 and m['status'] == 'FINALIZED_FOR_EXPLICIT_ARM', 'monitor metadata')
    need(p['private']['CONFIG.json'] == CONFIG_SHA and p['deadline_utc'] == r['deadline_utc'], 'packet metadata')
    need(all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in MAXIMA), 'finite caps')
    return MAXIMA
