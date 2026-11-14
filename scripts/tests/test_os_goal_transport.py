"""Pure functional communications classification; no network or campaign calls."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from os_goal_transport import classify_rpc_failure, classify_service_failure, classify_usage_failure

OBSERVED_502 = ('account/rateLimits/read: ' + json.dumps({
    'code': -32603, 'message': 'failed to fetch codex rate limits: GET '
    'https://chatgpt.com/backend-api/wham/usage failed: 502 Bad Gateway; '
    'content-type=text/plain; charset=UTF-8; body=error code: 502\n'}))


def usage_error(status=502, **extra):
    reason = {500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable',
              504: 'Gateway Timeout', 408: 'Request Timeout', 429: 'Too Many Requests'}[status]
    detail = {'code': -32603, 'message': 'failed to fetch codex rate limits: GET '
              'https://chatgpt.com/backend-api/wham/usage failed: '
              + str(status) + ' ' + reason + '; content-type=text/plain'}
    detail.update(extra)
    return 'account/rateLimits/read: ' + json.dumps(detail)


class UsageClassification(unittest.TestCase):
    def test_actual_saved_502_and_supported_statuses(self):
        self.assertEqual(classify_usage_failure(OBSERVED_502), 'http_502')
        for status in (500, 502, 503, 504):
            self.assertEqual(classify_usage_failure(usage_error(status)), 'http_' + str(status))

    def test_exact_timeout_connection_and_locally_scoped_transport(self):
        self.assertEqual(classify_usage_failure(
            'App-server request timed out: account/rateLimits/read'), 'timeout')
        error = usage_error(message='failed to fetch codex rate limits: error sending request for url '
                            '(https://chatgpt.com/backend-api/wham/usage)')
        self.assertEqual(classify_usage_failure(error), 'connection_send')
        for label in ('disconnected', 'broken_pipe', 'connection_reset'):
            self.assertEqual(classify_usage_failure(
                'Local account/rateLimits/read transport: ' + label), 'local_' + label)
        self.assertIsNone(classify_usage_failure('Codex app server disconnected; see retained stderr.'))

    def test_real_holds_in_nested_payload_always_veto(self):
        for hold in ('cyberPolicy', 'usageLimitExceeded', 'sessionBudgetExceeded',
                     'creditBudgetExhausted', 'authentication required', 'billing',
                     'spendControlReached', 'spending control', 'quota', 'rateLimitExceeded'):
            self.assertIsNone(classify_usage_failure(usage_error(data={'codexErrorInfo': hold})))
        for status in (408, 429):
            self.assertIsNone(classify_usage_failure(usage_error(status)))

    def test_wrong_endpoint_method_shape_and_malformed_errors_rejected(self):
        cases = [None, '', 'account/rateLimits/read: invalid json',
                 usage_error().replace('/wham/usage', '/auth'),
                 usage_error().replace('account/rateLimits/read:', 'thread/resume:'),
                 usage_error(code=-32000), usage_error(code=True), usage_error(message=None),
                 usage_error(data=float('nan')),
                 'account/rateLimits/read: []',
                 'account/rateLimits/read: {"code":-32603,"code":-32603,"message":"x"}']
        for case in cases:
            self.assertIsNone(classify_usage_failure(case))

    def test_read_only_timeouts_distinguished_from_mutating_uncertainty(self):
        self.assertEqual(classify_rpc_failure('App-server request timed out: account/read'), 'rpc_timeout')
        self.assertEqual(classify_rpc_failure(
            'Codex app server disconnected; see retained stderr.'), 'disconnected')
        for method in ('turn/start', 'turn/steer', 'thread/resume', 'thread/goal/set', 'unknown/write'):
            self.assertIsNone(classify_rpc_failure('App-server request timed out: ' + method))

    def test_service_transients_are_exact_and_real_holds_override_them(self):
        for info in ('serverOverloaded', 'rateLimitExceeded'):
            self.assertEqual(classify_service_failure({'codexErrorInfo': info}), info)
            for hold in ('policy', 'authentication', 'billing', 'credit exhausted', 'quota'):
                self.assertIsNone(classify_service_failure({'codexErrorInfo': info,
                                                           'data': {'reason': hold}}))
        for error in (None, {}, {'codexErrorInfo': {}}, {'codexErrorInfo': 'usageLimitExceeded'}):
            self.assertIsNone(classify_service_failure(error))


if __name__ == '__main__':
    unittest.main()
