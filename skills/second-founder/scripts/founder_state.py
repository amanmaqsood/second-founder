#!/usr/bin/env python3
"""Local coordination only. This program never sends content to a provider."""
import argparse
import hashlib
import json
import os
import re
import secrets
import sqlite3
import sys
import time
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
 id TEXT PRIMARY KEY, root TEXT NOT NULL, domain TEXT NOT NULL,
 UNIQUE(root,domain));
CREATE TABLE IF NOT EXISTS shared_accounts (destination TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id),
 token_hash TEXT NOT NULL, state TEXT NOT NULL, started REAL NOT NULL,
 expires REAL NOT NULL, ended REAL, evidence_ref TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON runs(project) WHERE state='active';
CREATE TABLE IF NOT EXISTS actions (
 project TEXT NOT NULL REFERENCES projects(id), operation_key TEXT NOT NULL,
 kind TEXT NOT NULL, destination TEXT NOT NULL, fingerprint TEXT NOT NULL,
 slot_start REAL, slot_end REAL, run_id TEXT NOT NULL REFERENCES runs(id),
 state TEXT NOT NULL, remote_id TEXT, public_url TEXT, evidence_ref TEXT,
 attempt_key TEXT NOT NULL DEFAULT 'initial',
 created REAL NOT NULL, updated REAL NOT NULL,
 PRIMARY KEY(project,operation_key), UNIQUE(destination,fingerprint));
CREATE INDEX IF NOT EXISTS calendar ON actions(destination,slot_start,slot_end);
CREATE TABLE IF NOT EXISTS attempts (
 project TEXT NOT NULL, operation_key TEXT NOT NULL, attempt_key TEXT NOT NULL,
 destination TEXT NOT NULL, slot_start REAL, slot_end REAL,
 evidence_ref TEXT, reconciliation_ref TEXT, created REAL NOT NULL,
 PRIMARY KEY(project,operation_key,attempt_key),
 FOREIGN KEY(project,operation_key) REFERENCES actions(project,operation_key));
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, project TEXT NOT NULL, operation_key TEXT NOT NULL,
 state TEXT NOT NULL, recorded REAL NOT NULL, evidence_ref TEXT,
 reconciliation_ref TEXT, remote_id TEXT, public_url TEXT, attempt_key TEXT NOT NULL);
PRAGMA user_version=1;
"""
STATES = ('prepared', 'scheduled', 'published', 'verified', 'failed', 'blocked', 'unknown')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def clean(value, name):
    require(bool(value and value.strip()) and len(value) <= 1000 and
            not any(ord(c) < 32 for c in value), f'{name} must be nonempty, single-line, <=1000 characters')
    return value


def identifier(value):
    require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}', value)), 'Invalid project, destination, kind, or operation identifier')
    return value


def web_url(value, origin=False):
    parsed = urlsplit(value)
    require(parsed.scheme in ('http', 'https') and bool(parsed.hostname) and
            not parsed.username and not parsed.password, 'URL must be HTTP(S), without embedded credentials')
    if origin:
        require(parsed.path in ('', '/') and not parsed.query and not parsed.fragment, 'Domain must be a site origin without a path, query, or fragment')
        host, port = parsed.hostname.lower(), parsed.port
        authority = f'[{host}]' if ':' in host else host
        if port is not None and port != {'http': 80, 'https': 443}[parsed.scheme]:
            authority += f':{port}'
        return f'{parsed.scheme}://{authority}'
    return value


def utc(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(dt.tzinfo is not None, 'Slot timestamps require an explicit timezone')
    return dt.astimezone(timezone.utc).timestamp()


def row(value):
    return dict(value) if value is not None else None


@contextmanager
def transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


def project_exists(db, project):
    identifier(project)
    existing = db.execute('SELECT * FROM projects WHERE id=?', (project,)).fetchone()
    require(existing, 'Project is not registered')
    return existing


def unique_project_origin(db, project, root, domain):
    canonical = web_url(domain, origin=True)
    conflicts = [p['id'] for p in db.execute('SELECT id,domain FROM projects WHERE root=? AND id!=? ORDER BY id', (root, project))
                 if web_url(p['domain'], origin=True) == canonical]
    require(not conflicts,
            f'Equivalent root/origin conflicts for {project}: {", ".join(conflicts)}; root={root}, origin={canonical}. '
            'Inspect status --limit -1. Reuse the sole existing identity, or stop affected workers and reconcile legacy duplicate histories before resuming. No registrations were changed.')


def lease(db, args):
    run = db.execute('SELECT * FROM runs WHERE id=? AND project=?', (args.run_id, args.project)).fetchone()
    require(run is not None and run['state'] == 'active' and run['expires'] > time.time(), 'Run lease is absent, expired, or inactive')
    require(secrets.compare_digest(run['token_hash'], hashlib.sha256(args.lease_token.encode()).hexdigest()), 'Incorrect lease token')
    return run


def event(db, project, key, state, evidence=None, reconciliation=None, remote=None, url=None):
    attempt = db.execute('SELECT attempt_key FROM actions WHERE project=? AND operation_key=?', (project, key)).fetchone()[0]
    db.execute('INSERT INTO events(project,operation_key,state,recorded,evidence_ref,reconciliation_ref,remote_id,public_url,attempt_key) VALUES(?,?,?,?,?,?,?,?,?)',
               (project, key, state, time.time(), evidence, reconciliation, remote, url, attempt))


def has_success_history(db, project, key):
    return db.execute("SELECT 1 FROM events WHERE project=? AND operation_key=? AND state IN ('published','verified') LIMIT 1",
                      (project, key)).fetchone() is not None


def slot(db, destination, start_text, end_text):
    require(bool(start_text) == bool(end_text), 'Provide both --slot-start and --slot-end')
    start, end = (utc(start_text), utc(end_text)) if start_text else (None, None)
    require(start is None or end > start, 'Slot end must be after slot start')
    if db.execute('SELECT 1 FROM shared_accounts WHERE destination=?', (destination,)).fetchone():
        require(start is not None, 'Shared accounts require an explicit calendar slot')
    if start is not None:
        conflicts = db.execute('SELECT project,operation_key FROM attempts WHERE destination=? AND slot_start < ? AND slot_end > ?', (destination, end, start)).fetchall()
        require(not conflicts, 'Shared calendar slot overlaps an existing reservation; choose another slot')
    return start, end


def abandon_prepared(db, run_id, evidence):
    for action in db.execute("SELECT project,operation_key FROM actions WHERE run_id=? AND state='prepared'", (run_id,)).fetchall():
        db.execute("UPDATE actions SET state='unknown',updated=?,evidence_ref=? WHERE project=? AND operation_key=?",
                   (time.time(), evidence, action['project'], action['operation_key']))
        event(db, action['project'], action['operation_key'], 'unknown', evidence)


def dispatch(db, a):
    if a.command == 'init':
        require(db.execute('PRAGMA user_version').fetchone()[0] in (0, 1), 'Unsupported database version')
        db.executescript(SCHEMA)
        return {'initialized': True, 'schema_version': 1}
    require(db.execute('PRAGMA user_version').fetchone()[0] == 1, 'Run init on this database first')
    if a.command == 'status':
        where, params = (' WHERE project=?', (a.project,)) if a.project else ('', ())
        if a.project:
            project_exists(db, a.project)
        result = {'projects': [row(r) for r in db.execute('SELECT * FROM projects' + (' WHERE id=?' if a.project else ''), params)],
                  'shared_accounts': [r[0] for r in db.execute('SELECT destination FROM shared_accounts ORDER BY destination')],
                  'runs': [row(r) for r in db.execute('SELECT id,project,state,started,expires,ended,evidence_ref FROM runs' + where + ' ORDER BY started DESC LIMIT ?', params + (a.limit,))],
                  'actions': [row(r) for r in db.execute('SELECT * FROM actions' + where + ' ORDER BY updated DESC LIMIT ?', params + (a.limit,))]}
        if a.pending:
            pending_where = where + (' AND' if where else ' WHERE') + " state != 'verified'"
            result['actions'] = [row(r) for r in db.execute('SELECT * FROM actions' + pending_where + ' ORDER BY updated ASC,project,operation_key', params)]
        if a.operation_key:
            require(a.project, '--operation-key requires --project')
            result['actions'] = [row(r) for r in db.execute('SELECT * FROM actions WHERE project=? AND operation_key=?', (a.project, a.operation_key))]
            result['events'] = [row(r) for r in db.execute('SELECT * FROM events WHERE project=? AND operation_key=? ORDER BY id', (a.project, a.operation_key))]
            result['attempts'] = [row(r) for r in db.execute('SELECT * FROM attempts WHERE project=? AND operation_key=? ORDER BY created', (a.project, a.operation_key))]
        return result
    with transaction(db):
        if a.command == 'register-shared-account':
            identifier(a.destination)
            require(':' in a.destination, 'Destination must include provider:immutable-account-id')
            require(not db.execute('SELECT 1 FROM actions WHERE destination=? AND slot_start IS NULL', (a.destination,)).fetchone(), 'Existing unslotted actions require manual migration before sharing this account')
            db.execute('INSERT OR IGNORE INTO shared_accounts VALUES(?)', (a.destination,))
            return {'shared_account': a.destination}
        if a.command == 'register-project':
            identifier(a.project)
            require(Path(a.root).is_absolute(), '--root must be absolute')
            root, domain = os.path.normcase(str(Path(a.root).resolve())), web_url(a.domain, origin=True)
            existing = row(db.execute('SELECT * FROM projects WHERE id=?', (a.project,)).fetchone())
            if existing:
                require(existing['root'] == root and web_url(existing['domain'], origin=True) == domain, 'Project ID is already bound to a different root/domain; do not rebind it')
            unique_project_origin(db, a.project, root, domain)
            if existing:
                return {'project': existing, 'existing': True}
            db.execute('INSERT INTO projects VALUES(?,?,?)', (a.project, root, domain))
            return {'project': {'id': a.project, 'root': root, 'domain': domain}, 'existing': False}
        project = project_exists(db, a.project)
        if a.command in ('start-run', 'renew-run', 'reserve-action', 'reserve-retry'):
            unique_project_origin(db, project['id'], project['root'], project['domain'])
        if a.command == 'start-run':
            require(30 <= a.lease_seconds <= 86400, 'Lease duration must be 30..86400 seconds')
            existing = db.execute("SELECT * FROM runs WHERE project=? AND state='active'", (a.project,)).fetchone()
            if existing:
                require(existing['expires'] <= time.time(), 'Project already has an active run lease')
                require(a.takeover_stale and a.evidence_ref, 'Expired lease: explicit --takeover-stale and --evidence-ref are required after checking the old worker has stopped')
                clean(a.evidence_ref, 'evidence-ref')
                db.execute("UPDATE runs SET state='abandoned',ended=?,evidence_ref=? WHERE id=?", (time.time(), a.evidence_ref, existing['id']))
                abandon_prepared(db, existing['id'], a.evidence_ref)
            token, run_id, now = 'sf_' + secrets.token_urlsafe(32), str(uuid.uuid4()), time.time()
            db.execute('INSERT INTO runs(id,project,token_hash,state,started,expires) VALUES(?,?,?,?,?,?)',
                       (run_id, a.project, hashlib.sha256(token.encode()).hexdigest(), 'active', now, now + a.lease_seconds))
            return {'run_id': run_id, 'lease_token': token, 'expires': now + a.lease_seconds}
        lease(db, a)
        if a.command == 'renew-run':
            require(30 <= a.lease_seconds <= 86400, 'Lease duration must be 30..86400 seconds')
            expires = time.time() + a.lease_seconds
            db.execute('UPDATE runs SET expires=? WHERE id=?', (expires, a.run_id))
            return {'run_id': a.run_id, 'expires': expires}
        if a.command == 'finish-run':
            evidence = clean(a.evidence_ref, 'evidence-ref')
            abandon_prepared(db, a.run_id, evidence)
            db.execute("UPDATE runs SET state='finished',ended=?,evidence_ref=? WHERE id=?", (time.time(), evidence, a.run_id))
            return {'run_id': a.run_id, 'finished': True, 'unresolved_prepared_actions': 'marked unknown; reconcile before any further action'}
        identifier(a.operation_key)
        existing = row(db.execute('SELECT * FROM actions WHERE project=? AND operation_key=?', (a.project, a.operation_key)).fetchone())
        if a.command == 'reserve-retry':
            require(existing is not None, 'Operation has not been reserved')
            identifier(a.attempt_key)
            require(a.attempt_key != 'initial', 'Choose a stable recovery attempt key distinct from initial')
            evidence, reconciliation = clean(a.evidence_ref, 'evidence-ref'), clean(a.reconciliation_ref, 'reconciliation-ref')
            previous = row(db.execute('SELECT * FROM attempts WHERE project=? AND operation_key=? AND attempt_key=?', (a.project, a.operation_key, a.attempt_key)).fetchone())
            if previous:
                require(previous['evidence_ref'] == evidence and previous['reconciliation_ref'] == reconciliation, 'Retry attempt identity/evidence is immutable')
                return {'action': existing, 'attempt': previous, 'existing': True, 'submit_authorized': False}
            require(existing['state'] == 'failed', 'Only conclusively failed actions may reserve a retry; reconcile unknown first')
            require(not has_success_history(db, a.project, a.operation_key), 'Previously published or verified operation cannot retry as if it had no side effects; preserve its receipt history')
            require(a.confirmed_no_side_effects, 'Retry requires an explicit confirmed-no-side-effects assertion supported by reconciliation evidence')
            count = db.execute('SELECT COUNT(*) FROM attempts WHERE project=? AND operation_key=?', (a.project, a.operation_key)).fetchone()[0]
            require(count < 3, 'Maximum of three total attempts reached; hold for investigation')
            start, end = existing['slot_start'], existing['slot_end']
            require(end is None or end > time.time(), 'Original slot elapsed: defer to a deliberate scheduling recovery plan; reservation is retained')
            now = time.time()
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?)', (a.project, a.operation_key, a.attempt_key, existing['destination'], start, end, evidence, reconciliation, now))
            db.execute("UPDATE actions SET state='prepared',remote_id=NULL,public_url=NULL,evidence_ref=?,updated=?,run_id=?,attempt_key=? WHERE project=? AND operation_key=?", (evidence, now, a.run_id, a.attempt_key, a.project, a.operation_key))
            event(db, a.project, a.operation_key, 'prepared', evidence, reconciliation)
            return {'action': row(db.execute('SELECT * FROM actions WHERE project=? AND operation_key=?', (a.project, a.operation_key)).fetchone()),
                    'attempt': row(db.execute('SELECT * FROM attempts WHERE project=? AND operation_key=? AND attempt_key=?', (a.project, a.operation_key, a.attempt_key)).fetchone()),
                    'existing': False, 'submit_authorized': True, 'next_step': 'One evidenced recovery attempt only; renew lease and recheck provider before sending'}
        if a.command == 'reserve-action':
            identifier(a.kind)
            identifier(a.destination)
            require(':' in a.destination, 'Destination must include provider:immutable-account-or-target-id')
            require(bool(re.fullmatch(r'[0-9a-f]{64}', a.fingerprint)), 'Fingerprint must be a lowercase SHA-256 hex digest of the exact action package')
            require(bool(a.slot_start) == bool(a.slot_end), 'Provide both --slot-start and --slot-end')
            start, end = (utc(a.slot_start), utc(a.slot_end)) if a.slot_start else (None, None)
            require(start is None or end > start, 'Slot end must be after slot start')
            if db.execute('SELECT 1 FROM shared_accounts WHERE destination=?', (a.destination,)).fetchone():
                require(start is not None, 'Shared accounts require an explicit calendar slot')
            scope = {'kind': a.kind, 'destination': a.destination, 'fingerprint': a.fingerprint, 'slot_start': start, 'slot_end': end}
            if existing:
                require(all(existing[k] == v for k, v in scope.items()), 'Operation key is immutable: supplied scope differs from its reservation')
                return {'action': existing, 'existing': True, 'submit_authorized': False, 'next_step': 'Inspect/reconcile existing operation; never resend from this response'}
            require(not db.execute('SELECT 1 FROM actions WHERE destination=? AND fingerprint=?', (a.destination, a.fingerprint)).fetchone(), 'Exact destination/package already reserved under another operation; inspect existing state')
            slot(db, a.destination, a.slot_start, a.slot_end)
            now = time.time()
            db.execute('INSERT INTO actions(project,operation_key,kind,destination,fingerprint,slot_start,slot_end,run_id,state,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (a.project, a.operation_key, a.kind, a.destination, a.fingerprint, start, end, a.run_id, 'prepared', now, now))
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?)', (a.project, a.operation_key, 'initial', a.destination, start, end, None, None, now))
            event(db, a.project, a.operation_key, 'prepared')
            return {'action': row(db.execute('SELECT * FROM actions WHERE project=? AND operation_key=?', (a.project, a.operation_key)).fetchone()), 'existing': False,
                    'submit_authorized': True, 'next_step': 'One initial attempt only, subject to saved scope and provider preflight; record result immediately'}
        require(existing is not None, 'Operation has not been reserved')
        evidence = clean(a.evidence_ref, 'evidence-ref')
        require(a.outcome != 'prepared' or existing['state'] == 'prepared', 'Cannot reset an operation to prepared')
        require(not (existing['state'] == 'verified' and a.outcome != 'verified'), 'Verified operation cannot be downgraded')
        require(not (existing['state'] == 'published' and a.outcome not in ('published', 'verified', 'unknown')), 'Published operation cannot be reset or treated as unsent')
        require(a.outcome in ('published', 'verified', 'unknown') or not has_success_history(db, a.project, a.operation_key), 'Previously published or verified operation cannot be reset or treated as unsent')
        needs_reconcile = existing['state'] in ('unknown', 'failed', 'blocked') or existing['run_id'] != a.run_id
        if needs_reconcile:
            clean(a.reconciliation_ref, 'reconciliation-ref')
        if a.remote_id:
            clean(a.remote_id, 'remote-id')
            require(existing['remote_id'] in (None, a.remote_id), 'Remote ID is immutable; investigate inconsistent provider evidence')
        remote, url = a.remote_id or existing['remote_id'], a.public_url or existing['public_url']
        if url:
            web_url(url)
        if a.outcome in ('scheduled', 'published'):
            require(remote, 'Scheduled/published outcome requires a provider remote ID')
        if a.outcome == 'published':
            require(url, 'Published outcome requires a public URL and evidence')
        if a.outcome == 'verified' and existing['kind'] in ('social', 'blog'):
            require(remote and url, 'Verified social/blog publication requires remote ID, public URL, and verification evidence')
        db.execute('UPDATE actions SET state=?,remote_id=?,public_url=?,evidence_ref=?,updated=? WHERE project=? AND operation_key=?',
                   (a.outcome, remote, url, evidence, time.time(), a.project, a.operation_key))
        event(db, a.project, a.operation_key, a.outcome, evidence, a.reconciliation_ref, remote, url)
        return {'action': row(db.execute('SELECT * FROM actions WHERE project=? AND operation_key=?', (a.project, a.operation_key)).fetchone()), 'submit_authorized': False}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', required=True, help='Absolute path to the one shared SQLite database')
    commands = p.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    reg = commands.add_parser('register-project')
    reg.add_argument('--project', required=True)
    reg.add_argument('--root', required=True)
    reg.add_argument('--domain', required=True)
    shared = commands.add_parser('register-shared-account')
    shared.add_argument('--destination', required=True)
    start = commands.add_parser('start-run')
    start.add_argument('--project', required=True)
    start.add_argument('--lease-seconds', type=int, default=1800)
    start.add_argument('--takeover-stale', action='store_true')
    start.add_argument('--evidence-ref')
    for name in ('renew-run', 'finish-run', 'reserve-action', 'reserve-retry', 'record-outcome'):
        sub = commands.add_parser(name)
        sub.add_argument('--project', required=True)
        sub.add_argument('--run-id', required=True)
        sub.add_argument('--lease-token', required=True)
        if name == 'renew-run':
            sub.add_argument('--lease-seconds', type=int, default=1800)
        if name == 'finish-run':
            sub.add_argument('--evidence-ref', required=True)
        if name in ('reserve-action', 'reserve-retry', 'record-outcome'):
            sub.add_argument('--operation-key', required=True)
        if name == 'reserve-action':
            for field in ('kind', 'destination', 'fingerprint'):
                sub.add_argument('--' + field, required=True)
            sub.add_argument('--slot-start')
            sub.add_argument('--slot-end')
        if name == 'reserve-retry':
            sub.add_argument('--attempt-key', required=True)
            sub.add_argument('--evidence-ref', required=True)
            sub.add_argument('--reconciliation-ref', required=True)
            sub.add_argument('--confirmed-no-side-effects', action='store_true')
        if name == 'record-outcome':
            sub.add_argument('--outcome', choices=STATES, required=True)
            sub.add_argument('--evidence-ref', required=True)
            sub.add_argument('--reconciliation-ref')
            sub.add_argument('--remote-id')
            sub.add_argument('--public-url')
    status = commands.add_parser('status')
    status.add_argument('--project')
    view = status.add_mutually_exclusive_group()
    view.add_argument('--operation-key')
    view.add_argument('--pending', action='store_true', help='Return every nonverified action, oldest first, without the recent-history action limit')
    status.add_argument('--limit', type=int, default=100, help='Recent runs/actions per list; -1 returns all (default: 100)')
    return p


def main():
    args = parser().parse_args()
    try:
        path = Path(args.db)
        require(path.is_absolute(), '--db must be an absolute path shared by every project')
        require(args.command == 'init' or path.is_file(), 'Database does not exist; run init first')
        if args.command == 'init':
            path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(str(path), timeout=15, isolation_level=None)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            result = dispatch(db, args)
        print(json.dumps({'ok': True, 'db': str(path.resolve()), **result}, indent=2))
    except (ValueError, sqlite3.Error, OSError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, indent=2))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
