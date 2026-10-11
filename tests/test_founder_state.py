"""Black-box tests, with isolated database fixtures for expiry and legacy state."""
import concurrent.futures
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/second-founder/scripts/founder_state.py'
SLOT_DATE = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / 'shared.sqlite3'
        self.call('init')
        self.call('register-project', '--project', 'alpha', '--root', str(self.root / 'alpha'), '--domain', 'https://alpha.example')
        self.run = self.call('start-run', '--project', 'alpha')

    def tearDown(self):
        self.temp.cleanup()

    def call(self, *args, fail=False):
        result = subprocess.run([sys.executable, str(SCRIPT), '--db', str(self.db), *args], capture_output=True, text=True)
        try:
            data = json.loads(result.stdout)
        except ValueError:
            self.fail(f'Non-JSON output: {result.stdout} {result.stderr}')
        self.assertEqual(result.returncode, 1 if fail else 0, result.stdout + result.stderr)
        self.assertEqual(data['ok'], not fail)
        return data

    def credentials(self, project='alpha', run=None):
        run = run or self.run
        return ('--project', project, '--run-id', run['run_id'], '--lease-token', run['lease_token'])

    def reserve(self, key='post-1', dest='postiz:founder-id', project='alpha', run=None, text='article', slots=False, fail=False):
        args = ['reserve-action', *self.credentials(project, run), '--operation-key', key,
                '--kind', 'social', '--destination', dest, '--fingerprint', hashlib.sha256(text.encode()).hexdigest()]
        if slots:
            args += ['--slot-start', f'{SLOT_DATE}T09:00:00Z', '--slot-end', f'{SLOT_DATE}T09:30:00Z']
        return self.call(*args, fail=fail)

    def outcome(self, state, *extra, fail=False, run=None):
        return self.call('record-outcome', *self.credentials(run=run), '--operation-key', 'post-1',
                         '--outcome', state, '--evidence-ref', 'file:receipts/checked.json', *extra, fail=fail)

    def test_project_lock_and_identity_are_not_rebound(self):
        self.call('start-run', '--project', 'alpha', fail=True)
        self.call('register-project', '--project', 'alpha', '--root', str(self.root / 'other'), '--domain', 'https://alpha.example', fail=True)
        self.call('register-project', '--project', 'alias', '--root', str(self.root / 'alpha'), '--domain', 'https://alpha.example', fail=True)
        self.call('renew-run', '--project', 'alpha', '--run-id', self.run['run_id'], '--lease-token', 'wrong', fail=True)
        self.call('renew-run', *self.credentials(), '--lease-seconds', '3600')

    def test_only_first_exact_reservation_permits_initial_attempt(self):
        first = self.reserve()
        repeat = self.reserve()
        self.assertTrue(first['submit_authorized'])
        self.assertFalse(repeat['submit_authorized'])
        self.assertEqual(first['action'], repeat['action'])
        self.reserve(text='changed content', fail=True)
        self.reserve(dest='postiz:another-account', fail=True)
        self.reserve(key='new-key-same-package', fail=True)

    def test_shared_account_requires_interval_and_concurrent_slots_have_one_winner(self):
        self.call('register-shared-account', '--destination', 'postiz:founder-id')
        self.reserve(fail=True)
        cases = []
        for number in range(8):
            project = f'p{number}'
            self.call('register-project', '--project', project, '--root', str(self.root / project), '--domain', f'https://{project}.example')
            run = self.call('start-run', '--project', project)
            cases.append((project, run))

        def attempt(case):
            project, run = case
            result = subprocess.run([sys.executable, str(SCRIPT), '--db', str(self.db), 'reserve-action',
                *self.credentials(project, run), '--operation-key', 'launch', '--kind', 'social',
                '--destination', 'postiz:founder-id', '--fingerprint', hashlib.sha256(project.encode()).hexdigest(),
                '--slot-start', f'{SLOT_DATE}T09:00:00Z', '--slot-end', f'{SLOT_DATE}T09:30:00Z'], capture_output=True, text=True)
            return json.loads(result.stdout)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, cases))
        self.assertEqual(sum(r['ok'] for r in results), 1)
        self.assertTrue(all(r.get('submit_authorized') for r in results if r['ok']))
        self.assertTrue(all('overlaps' in r['error'] for r in results if not r['ok']))
        status = self.call('status')
        self.assertEqual(len(status['actions']), 1)

    def test_overlapping_intervals_and_immutable_slot(self):
        self.reserve(slots=True)
        self.reserve(slots=False, fail=True)
        for start, end in [('09:15', '09:45'), ('08:45', '09:15'), ('08:00', '10:00')]:
            self.call('reserve-action', *self.credentials(), '--operation-key', f'slot-{start.replace(":", "")}', '--kind', 'social',
                '--destination', 'postiz:founder-id', '--fingerprint', hashlib.sha256(start.encode()).hexdigest(),
                '--slot-start', f'{SLOT_DATE}T{start}:00Z', '--slot-end', f'{SLOT_DATE}T{end}:00Z', fail=True)
        self.call('reserve-action', *self.credentials(), '--operation-key', 'adjacent', '--kind', 'social',
            '--destination', 'postiz:founder-id', '--fingerprint', hashlib.sha256(b'adjacent').hexdigest(),
            '--slot-start', f'{SLOT_DATE}T09:30:00Z', '--slot-end', f'{SLOT_DATE}T10:00:00Z')

    def test_unknown_cannot_be_reset_or_resent_and_reconciliation_is_required(self):
        self.reserve()
        self.outcome('unknown')
        self.assertFalse(self.reserve()['submit_authorized'])
        self.outcome('prepared', '--reconciliation-ref', 'file:reconciled.json', fail=True)
        self.outcome('scheduled', '--remote-id', 'provider-123', fail=True)
        result = self.outcome('scheduled', '--remote-id', 'provider-123', '--reconciliation-ref', 'file:provider-lookup.json')
        self.assertEqual(result['action']['state'], 'scheduled')
        self.assertFalse(result['submit_authorized'])
        self.outcome('published', '--public-url', 'https://social.example/posts/123')
        self.outcome('verified')
        self.outcome('failed', fail=True)
        self.outcome('verified', '--remote-id', 'different-id', fail=True)
        status = self.call('status', '--project', 'alpha', '--operation-key', 'post-1')
        self.assertEqual([e['state'] for e in status['events']], ['prepared', 'unknown', 'scheduled', 'published', 'verified'])

    def test_outcomes_need_receipts_and_publication_evidence(self):
        self.reserve()
        self.outcome('scheduled', fail=True)
        self.outcome('published', '--remote-id', 'id-1', fail=True)
        self.outcome('verified', fail=True)
        self.outcome('scheduled', '--remote-id', 'id-1', '--evidence-ref', '', fail=True)
        self.outcome('published', '--remote-id', 'id-1', '--public-url', 'https://u:p@example.com/post', fail=True)
        self.outcome('published', '--remote-id', 'id-1', '--public-url', 'https://example.com/post')

    def test_stale_takeover_is_deliberate_and_does_not_release_actions(self):
        self.reserve(slots=True)
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('UPDATE runs SET expires=0 WHERE id=?', (self.run['run_id'],))
            db.commit()
        self.reserve(key='later', text='later', fail=True)
        self.call('start-run', '--project', 'alpha', fail=True)
        self.call('start-run', '--project', 'alpha', '--takeover-stale', fail=True)
        new_run = self.call('start-run', '--project', 'alpha', '--takeover-stale', '--evidence-ref', 'file:old-worker-stopped.json')
        self.assertFalse(self.reserve(slots=True, run=new_run)['submit_authorized'])
        self.outcome('blocked', run=new_run, fail=True)
        self.outcome('blocked', '--reconciliation-ref', 'file:provider-lookup.json', run=new_run)
        self.reserve(key='another', text='different', slots=True, run=new_run, fail=True)

    def test_finish_closes_lease_and_preserves_uncertainty(self):
        self.reserve()
        self.call('finish-run', *self.credentials(), '--evidence-ref', 'file:run-summary.json')
        self.reserve(key='too-late', text='changed', fail=True)
        status = self.call('status', '--project', 'alpha')
        self.assertEqual(status['actions'][0]['state'], 'unknown')
        self.assertNotIn('token_hash', status['runs'][0])
        new_run = self.call('start-run', '--project', 'alpha')
        self.assertFalse(self.reserve(run=new_run)['submit_authorized'])

    def retry(self, attempt='recovery-1', fail=False):
        return self.call('reserve-retry', *self.credentials(), '--operation-key', 'post-1', '--attempt-key', attempt,
            '--evidence-ref', 'file:receipts/definitive-failure.json', '--reconciliation-ref', 'file:receipts/no-side-effects.json',
            '--confirmed-no-side-effects', fail=fail)

    def test_retry_is_bounded_evidenced_and_never_granted_from_unknown(self):
        self.reserve()
        self.outcome('unknown')
        self.retry(fail=True)
        self.outcome('failed', '--reconciliation-ref', 'file:receipts/permanent-rejection.json')
        self.call('reserve-retry', *self.credentials(), '--operation-key', 'post-1', '--attempt-key', 'recovery-1',
            '--evidence-ref', 'file:failure.json', '--reconciliation-ref', 'file:reconciled.json', fail=True)
        self.assertTrue(self.retry()['submit_authorized'])
        self.assertFalse(self.retry()['submit_authorized'])
        self.assertFalse(self.reserve()['submit_authorized'])
        self.outcome('unknown')
        self.assertFalse(self.retry()['submit_authorized'])
        self.retry('recovery-2', fail=True)
        self.outcome('failed', '--reconciliation-ref', 'file:receipts/second-permanent-rejection.json')
        self.assertTrue(self.retry('recovery-2')['submit_authorized'])
        self.outcome('failed')
        self.retry('recovery-3', fail=True)
        state = self.call('status', '--project', 'alpha', '--operation-key', 'post-1')
        self.assertEqual(len(state['attempts']), 3)
        self.assertEqual([e['attempt_key'] for e in state['events'] if e['state'] == 'prepared'], ['initial', 'recovery-1', 'recovery-2'])

    def test_concurrent_retry_replays_authorize_exactly_once(self):
        self.reserve()
        self.outcome('failed')
        def attempt(_):
            return self.retry()
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(attempt, range(6)))
        self.assertEqual(sum(r['submit_authorized'] for r in results), 1)

    def test_retry_does_not_release_or_rewrite_elapsed_slot(self):
        self.call('register-shared-account', '--destination', 'postiz:founder-id')
        self.call('reserve-action', *self.credentials(), '--operation-key', 'post-1', '--kind', 'social',
            '--destination', 'postiz:founder-id', '--fingerprint', hashlib.sha256(b'old').hexdigest(),
            '--slot-start', '2000-01-01T09:00:00Z', '--slot-end', '2000-01-01T09:30:00Z')
        self.outcome('failed')
        self.retry(fail=True)
        state = self.call('status', '--project', 'alpha', '--operation-key', 'post-1')
        self.assertEqual(len(state['attempts']), 1)
        self.assertEqual(state['actions'][0]['state'], 'failed')

    def test_querystring_public_urls_are_valid_but_not_origins(self):
        self.reserve()
        self.outcome('published', '--remote-id', 'video-1', '--public-url', 'https://www.youtube.com/watch?v=video-1')
        self.outcome('verified')
        self.call('register-project', '--project', 'bad-origin', '--root', str(self.root / 'bad'), '--domain', 'https://example.com/?token=x', fail=True)

    def test_published_history_blocks_indirect_unsent_transitions_and_preserves_receipts(self):
        self.reserve()
        self.outcome('published', '--remote-id', 'already-posted', '--public-url', 'https://social.example/posts/already-posted')
        self.outcome('unknown')
        for state in ('failed', 'blocked', 'scheduled', 'prepared'):
            self.outcome(state, '--reconciliation-ref', 'file:provider-lookup.json', fail=True)
        self.retry(fail=True)
        status = self.call('status', '--project', 'alpha', '--operation-key', 'post-1')
        self.assertEqual([event['state'] for event in status['events']], ['prepared', 'published', 'unknown'])
        self.assertEqual(status['actions'][0]['remote_id'], 'already-posted')
        self.assertEqual(status['actions'][0]['public_url'], 'https://social.example/posts/already-posted')
        self.assertEqual(len(status['attempts']), 1)
        self.outcome('published', '--reconciliation-ref', 'file:provider-lookup.json')
        self.outcome('verified')

    def test_retry_rejects_legacy_failed_rows_with_success_history(self):
        for state in ('published', 'verified'):
            with self.subTest(prior_state=state):
                key = 'legacy-' + state
                self.reserve(key=key, text=key)
                self.call('record-outcome', *self.credentials(), '--operation-key', key, '--outcome', state,
                          '--remote-id', key, '--public-url', 'https://social.example/posts/' + key,
                          '--evidence-ref', 'file:confirmed-publication.json')
                # Simulate the persisted failed row allowed by the old transition guard.
                with closing(sqlite3.connect(self.db)) as db:
                    db.execute("UPDATE actions SET state='failed' WHERE project='alpha' AND operation_key=?", (key,))
                    db.commit()
                result = self.call('reserve-retry', *self.credentials(), '--operation-key', key, '--attempt-key', 'legacy-recovery',
                    '--confirmed-no-side-effects', '--evidence-ref', 'file:claimed-failure.json', '--reconciliation-ref', 'file:claimed-no-effects.json', fail=True)
                self.assertIn('Previously published or verified', result['error'])
                status = self.call('status', '--project', 'alpha', '--operation-key', key)
                self.assertEqual(len(status['attempts']), 1)
                self.assertEqual(status['actions'][0]['remote_id'], key)

    def test_pending_view_includes_old_actions_without_history_limit(self):
        self.reserve()
        self.outcome('scheduled', '--remote-id', 'old-schedule')
        for number in range(101):
            self.reserve(key=f'newer-{number}', text=f'newer-{number}')
        self.call('record-outcome', *self.credentials(), '--operation-key', 'newer-100', '--outcome', 'verified',
                  '--remote-id', 'verified-post', '--public-url', 'https://social.example/posts/verified-post', '--evidence-ref', 'file:live-check.json')
        recent = self.call('status', '--project', 'alpha')
        self.assertNotIn('post-1', [action['operation_key'] for action in recent['actions']])
        pending = self.call('status', '--pending', '--project', 'alpha', '--limit', '1')
        self.assertEqual(len(pending['actions']), 101)
        self.assertEqual(pending['actions'][0]['operation_key'], 'post-1')
        self.assertNotIn('newer-100', [action['operation_key'] for action in pending['actions']])
        self.assertEqual(len(pending['runs']), 1)
        self.call('register-project', '--project', 'beta', '--root', str(self.root / 'beta'), '--domain', 'https://beta.example')
        beta_run = self.call('start-run', '--project', 'beta')
        self.reserve(key='beta-post', project='beta', run=beta_run, text='beta-content')
        self.assertEqual(len(self.call('status', '--pending')['actions']), 102)
        self.assertEqual(len(self.call('status', '--pending', '--project', 'beta')['actions']), 1)
        self.assertEqual(len(self.call('status', '--limit', '-1')['actions']), 103)

    def test_equivalent_default_port_origins_share_one_registration(self):
        equivalent = self.call('register-project', '--project', 'alpha', '--root', str(self.root / 'alpha'), '--domain', 'https://ALPHA.example:443/')
        self.assertTrue(equivalent['existing'])
        self.assertEqual(equivalent['project']['domain'], 'https://alpha.example')
        self.call('register-project', '--project', 'alpha-alias', '--root', str(self.root / 'alpha'), '--domain', 'https://alpha.example:443', fail=True)
        self.call('start-run', '--project', 'alpha-alias', fail=True)
        for key, explicit, canonical in (
            ('http', 'http://http.example:80', 'http://http.example'),
            ('https', 'https://https.example:443', 'https://https.example'),
            ('ipv6', 'https://[2001:db8::1]:443', 'https://[2001:db8::1]'),
        ):
            with self.subTest(origin=explicit):
                root = str(self.root / key)
                registered = self.call('register-project', '--project', key, '--root', root, '--domain', explicit)
                self.assertEqual(registered['project']['domain'], canonical)
                self.assertTrue(self.call('register-project', '--project', key, '--root', root, '--domain', canonical)['existing'])
                self.call('register-project', '--project', key + '-alias', '--root', root, '--domain', canonical, fail=True)

    def test_nondefault_origins_remain_distinct_and_public_urls_are_unchanged(self):
        for key, domain in (('alternate-https', 'https://alpha.example:8443'), ('alternate-http', 'http://alpha.example:443')):
            registered = self.call('register-project', '--project', key, '--root', str(self.root / 'alpha'), '--domain', domain)
            self.assertEqual(registered['project']['domain'], domain)
            self.call('start-run', '--project', key)
        self.reserve()
        url = 'https://social.example:443/posts/1?v=exact'
        self.outcome('published', '--remote-id', 'exact-post', '--public-url', url)
        status = self.call('status', '--project', 'alpha', '--operation-key', 'post-1')
        self.assertEqual(status['actions'][0]['public_url'], url)
        self.assertEqual(status['events'][-1]['public_url'], url)

    def test_legacy_default_port_bindings_are_compared_without_rewriting(self):
        for stored, equivalent in (('https://alpha.example:443', 'https://alpha.example'), ('http://alpha.example:80', 'http://alpha.example')):
            with self.subTest(stored_origin=stored):
                with closing(sqlite3.connect(self.db)) as db:
                    db.execute("UPDATE projects SET domain=? WHERE id='alpha'", (stored,))
                    db.commit()
                result = self.call('register-project', '--project', 'alpha', '--root', str(self.root / 'alpha'), '--domain', equivalent)
                self.assertTrue(result['existing'])
                self.assertEqual(result['project']['domain'], stored)
                self.call('register-project', '--project', 'legacy-alias', '--root', str(self.root / 'alpha'), '--domain', equivalent, fail=True)
                self.call('renew-run', *self.credentials())
                self.assertEqual(self.call('status', '--project', 'alpha')['projects'][0]['domain'], stored)

    def test_legacy_equivalent_identities_stop_new_effects_but_preserve_recovery(self):
        self.reserve()
        original = self.call('status', '--project', 'alpha')['projects'][0]
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('INSERT INTO projects VALUES(?,?,?)', ('legacy-alias', original['root'], 'https://alpha.example:443'))
            db.commit()
        for project in ('alpha', 'legacy-alias'):
            result = self.call('start-run', '--project', project, fail=True)
            self.assertIn('Equivalent root/origin conflicts', result['error'])
            self.assertIn('status --limit -1', result['error'])
        self.call('register-project', '--project', 'alpha', '--root', str(self.root / 'alpha'), '--domain', 'https://alpha.example', fail=True)
        self.call('renew-run', *self.credentials(), fail=True)
        self.reserve(key='blocked-effect', text='blocked-effect', fail=True)
        self.outcome('failed')
        self.retry(fail=True)
        self.call('finish-run', *self.credentials(), '--evidence-ref', 'file:identity-conflict.json')
        self.call('start-run', '--project', 'legacy-alias', fail=True)
        status = self.call('status', '--limit', '-1')
        self.assertEqual(len(status['projects']), 2)
        self.assertEqual(len(status['runs']), 1)
        self.assertEqual(status['runs'][0]['state'], 'finished')
        self.assertEqual(status['actions'][0]['state'], 'failed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
