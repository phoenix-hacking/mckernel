"""Execute the notification workflow's actual JS with isolated fake GitHub APIs."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github/workflows/mckernel-mailbox-notify.yml'
EVENT = 'a' * 64
NUMBER = 3
BOT = {'type': 'Bot', 'login': 'github-actions[bot]'}

NODE_RUNNER = r'''
let text = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => text += chunk);
process.stdin.on('end', async () => {
  const input = JSON.parse(text), calls = [], messages = [];
  const github = {
    rest: {
      pulls: {get: async args => {calls.push({method:'pulls.get', args}); return {data:input.mailbox};}},
      issues: {
        listComments: function listComments() {},
        createComment: async args => {
          calls.push({method:'issues.createComment', args});
          if (input.createError) throw new Error('Synthetic lost response');
          return {data:{id:789}};
        }
      }
    },
    paginate: {iterator: async function* (method, args) {
      if (method !== github.rest.issues.listComments) throw new Error('Wrong API');
      calls.push({method:'issues.listComments', args});
      for (const data of input.pages) {
        if (input.pageError) throw new Error('Synthetic read failure');
        calls.push({method:'page'});
        yield {data};
      }
    }}
  };
  const core = {info: message => messages.push(message)};
  const limitedRequire = name => {
    if (name !== 'crypto') throw new Error('Unexpected module');
    return require('crypto');
  };
  const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
  try {
    const value = await new AsyncFunction('github','context','core','require','Buffer',input.script)(
      github,input.context,core,limitedRequire,Buffer);
    process.stdout.write(JSON.stringify({value,calls,messages,sideEffect:global.__mailboxSideEffect || false}));
  } catch (error) {
    process.stdout.write(JSON.stringify({error:error.message,calls,messages}));
  }
});
'''


class MailboxWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text()
        cls.workflow = yaml.safe_load(cls.text)
        cls.step = cls.workflow['jobs']['notify']['steps'][0]
        cls.script = cls.step['with']['script']
        cls.node = shutil.which('node')
        if not cls.node:
            raise RuntimeError('Node is required to execute the workflow regression tests')

    def fixture(self):
        return {
            'script': re.sub(r'const MAILBOX_NUMBER = \d+;',
                             'const MAILBOX_NUMBER = %d;' % NUMBER, self.script),
            'context': {
                'repo': {'owner': 'phoenix-hacking', 'repo': 'mckernel'},
                'actor': 'phoenix-hacking', 'ref': 'refs/heads/development',
                'eventName': 'workflow_dispatch',
                'payload': {'sender': {'id': 175406809}, 'inputs': {
                    'event_id': EVENT, 'body': 'Blocked: missing supported source.\nAction: supply the exact input.'}},
            },
            'mailbox': {'number': NUMBER, 'user': {'id': 175406809},
                        'base': {'repo': {'full_name': 'phoenix-hacking/mckernel'}},
                        'state': 'open', 'draft': True, 'merged': False},
            'pages': [[]],
        }

    def run_script(self, fixture):
        result = subprocess.run([self.node, '-e', NODE_RUNNER],
                                input=json.dumps(fixture), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def posts(self, result):
        return [row['args'] for row in result['calls'] if row['method'] == 'issues.createComment']

    def test_workflow_is_fixed_scope_and_has_no_checkout_or_shell(self):
        triggers = self.workflow.get('on', self.workflow.get(True))
        self.assertEqual(set(triggers), {'workflow_dispatch', 'push'})
        self.assertEqual(set(triggers['workflow_dispatch']['inputs']), {'event_id', 'body'})
        self.assertEqual(triggers['push'], {
            'branches': ['development'], 'paths': ['.github/workflows/mckernel-mailbox-notify.yml']})
        self.assertEqual(self.workflow['permissions'], {'contents': 'read', 'pull-requests': 'write'})
        self.assertEqual(self.workflow['concurrency'], {
            'group': "mckernel-mailbox-${{ github.event.inputs.event_id || 'setup' }}", 'cancel-in-progress': False})
        self.assertEqual(len(self.workflow['jobs']['notify']['steps']), 1)
        self.assertEqual(self.step['uses'], 'actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd')
        self.assertEqual(self.step['with']['retries'], 0)
        self.assertNotIn('${{', self.script)
        self.assertNotIn('run', self.step)
        condition = self.workflow['jobs']['notify']['if']
        for expected in ("github.repository == 'phoenix-hacking/mckernel'",
                         "github.actor == 'phoenix-hacking'",
                         "github.triggering_actor == 'phoenix-hacking'",
                         "github.ref == 'refs/heads/development'"):
            self.assertIn(expected, condition)

    def test_dispatch_posts_only_to_fixed_mailbox_with_reply_help(self):
        fixture = self.fixture()
        fixture['context']['payload']['inputs']['body'] = (
            'Missing input @someone / @org/team <script>.\n'
            '`global.__mailboxSideEffect=true` $(touch /never-executed)')
        result = self.run_script(fixture)
        self.assertEqual(result['value']['status'], 'posted')
        self.assertFalse(result['sideEffect'])
        post, = self.posts(result)
        self.assertEqual((post['owner'], post['repo'], post['issue_number']),
                         ('phoenix-hacking', 'mckernel', NUMBER))
        self.assertIn('<!-- mckernel-mailbox:' + EVENT + ' -->', post['body'])
        self.assertEqual(post['body'].count('@'), 1)
        self.assertIn('@phoenix-hacking', post['body'])
        self.assertIn('&lt;script&gt;', post['body'])
        self.assertIn('/mckernel-resume', post['body'])
        self.assertIn('/mckernel-instruct', post['body'])
        self.assertIn('📤 **SENT', post['body'])
        self.assertIn('📥 **Your email/phone receipt is unconfirmed', post['body'])
        self.assertIn('every 10 minutes', post['body'])
        self.assertIn('does not confirm email delivery', post['body'])
        self.assertFalse(any('Missing input' in line for line in result['messages']))

    def test_existing_bot_marker_on_later_page_prevents_duplicate(self):
        fixture = self.fixture()
        fixture['pages'] = [[{'user': BOT, 'body': 'earlier unrelated notice'}],
                            [{'user': BOT, 'body': '<!-- mckernel-mailbox:' + EVENT + ' -->'}]]
        result = self.run_script(fixture)
        self.assertEqual(result['value']['status'], 'already_posted')
        self.assertEqual(self.posts(result), [])
        self.assertEqual(sum(row['method'] == 'page' for row in result['calls']), 2)

    def test_human_cannot_spoof_bot_deduplication_receipt(self):
        fixture = self.fixture()
        fixture['pages'] = [[{'user': {'type': 'User', 'login': 'phoenix-hacking'},
                              'body': '<!-- mckernel-mailbox:' + EVENT + ' -->'}]]
        self.assertEqual(len(self.posts(self.run_script(fixture))), 1)

    def test_invalid_inputs_are_rejected_before_any_api_access(self):
        cases = [
            {'event_id': EVENT.upper(), 'body': 'reason'},
            {'event_id': EVENT, 'body': ''},
            {'event_id': EVENT, 'body': 'é' * 3001},
            {'event_id': EVENT, 'body': 'bad\x00body'},
            {'event_id': EVENT, 'body': 'reason', 'mailbox_number': 999},
            {'event_id': EVENT, 'body': {'command': 'invalid'}},
            {'body': 'reason'},
        ]
        for inputs in cases:
            with self.subTest(inputs=str(inputs)[:90]):
                fixture = self.fixture()
                fixture['context']['payload']['inputs'] = inputs
                result = self.run_script(fixture)
                self.assertIn('error', result)
                self.assertEqual(result['calls'], [])

    def test_context_scope_and_immutable_sender_id_are_required(self):
        for field, value in (('actor', 'other-user'), ('ref', 'refs/heads/work'),
                             ('eventName', 'pull_request')):
            with self.subTest(field=field):
                fixture = self.fixture()
                fixture['context'][field] = value
                result = self.run_script(fixture)
                self.assertEqual(result['calls'], [])
                self.assertIn('error', result)
        for mutate in (lambda c: c['repo'].update(repo='other'),
                       lambda c: c['payload']['sender'].update(id=1)):
            fixture = self.fixture()
            mutate(fixture['context'])
            result = self.run_script(fixture)
            self.assertEqual(result['calls'], [])
            self.assertIn('error', result)

    def test_fixed_destination_must_still_be_the_dedicated_open_draft(self):
        for changes in ({'number': 999}, {'state': 'closed'}, {'draft': False},
                        {'merged': True}, {'user': {'id': 1}},
                        {'base': {'repo': {'full_name': 'other/repository'}}}):
            with self.subTest(changes=changes):
                fixture = self.fixture()
                fixture['mailbox'].update(changes)
                result = self.run_script(fixture)
                self.assertIn('error', result)
                self.assertEqual(self.posts(result), [])

    def test_uncertain_create_response_has_no_automatic_resend(self):
        fixture = self.fixture()
        fixture['createError'] = True
        result = self.run_script(fixture)
        self.assertIn('error', result)
        self.assertEqual(len(self.posts(result)), 1)

    def test_incomplete_comment_scan_never_creates_notice(self):
        fixture = self.fixture()
        fixture['pageError'] = True
        result = self.run_script(fixture)
        self.assertIn('error', result)
        self.assertEqual(self.posts(result), [])

    def test_setup_push_is_stable_and_does_not_claim_a_real_blocker(self):
        fixture = self.fixture()
        fixture['context']['eventName'] = 'push'
        fixture['context']['payload'].pop('inputs')
        first = self.run_script(fixture)
        body = self.posts(first)[0]['body']
        self.assertIn('does not report an engineering blocker', body)
        self.assertRegex(first['value']['event_id'], r'^[0-9a-f]{64}$')
        fixture['pages'] = [[{'user': BOT, 'body': body}]]
        second = self.run_script(fixture)
        self.assertEqual(second['value']['event_id'], first['value']['event_id'])
        self.assertEqual(second['value']['status'], 'already_posted')
        self.assertEqual(self.posts(second), [])

    def test_unconfigured_destination_fails_closed(self):
        fixture = self.fixture()
        fixture['script'] = re.sub(r'const MAILBOX_NUMBER = \d+;',
                                   'const MAILBOX_NUMBER = 0;', self.script)
        result = self.run_script(fixture)
        self.assertIn('error', result)
        self.assertEqual(result['calls'], [])


if __name__ == '__main__':
    unittest.main()
