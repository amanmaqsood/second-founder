# Durable state and the shared founder calendar

`scripts/founder_state.py` is a Python 3 standard-library helper. It coordinates local work; it never authenticates, calls a provider, posts, schedules remotely, deploys, or verifies a live result. Installing the skill does not create a database or automation. Create state when onboarding a project.

Use **one absolute SQLite database path for every enrolled project and every automation on the execution host**, including founder-account scheduling. Codex and Claude Code workers on the same host must use that same file, not separate assistant-specific calendars. Store this path in each project profile. Do not create a separate calendar database per project, copy the live database to another machine, or place it in the skill installation folder. Suitable private local locations include `%LOCALAPPDATA%\SecondFounder\state.sqlite3` on Windows, `~/.local/state/second-founder/state.sqlite3` on Linux (or a resolved `$XDG_STATE_HOME`), and `~/Library/Application Support/SecondFounder/state.sqlite3` on macOS. Resolve environment variables and `~` before saving the absolute path. SQLite coordination applies only to workers using this same file; independent copies cannot prevent collisions. Multiple hosts need a separately designed shared coordination service or one designated execution host; copying this database does not solve that problem. Back up the database through SQLite's backup API while active, or while all workers are stopped. Avoid a network or live-synced filesystem for this coordination file.

The database holds project IDs, canonical repository roots and site origins, action hashes, destination IDs, run leases, time slots and evidence references. It has no fields for customer rows, raw content, provider credentials, API keys or cookies. Never put secrets or personal customer data into an identifier, URL, evidence reference or other field. Keep evidence in the project's controlled state folder and store only a reference here. Public URLs may contain legitimate queries, such as YouTube's `watch?v=...`, but never store private signed URLs or token-bearing links. Embedded URL credentials are rejected; site origins additionally reject paths, queries and fragments. Local lease tokens are coordination capabilities: retain them only for the active worker, do not paste them into reports, and do not confuse them with provider credentials. Only a hash of the token is stored.

## Onboard and register the founder account

Examples use placeholders. Resolve `scripts/founder_state.py` relative to the directory containing the **loaded** `SKILL.md`; installations can be global, project-local or plugin-managed in either assistant. Do not assume a `.codex` or `.claude` installation path. Verify a Python 3 interpreter and use its saved executable (`python`, `python3` or another actual path) consistently. Bind the canonical project ID once, such as a UUID or stable slug. A project ID cannot be rebound to another root or domain. Registration canonicalizes the root and site origin, including treating HTTP port 80 and HTTPS port 443 as equivalent to an omitted port; nondefault ports remain distinct. This does not alter public post URLs or prove the directory, live site, account access or ownership is valid. Perform those onboarding checks separately. The same canonical root/origin cannot be registered under another project ID. Existing stored origins are compared semantically without rewriting their bindings.

If older registrations already contain equivalent IDs, new or renewed runs and new send reservations stop with the conflicting IDs, root and canonical origin in the error. Inspect `status --limit -1`, stop the affected workers, and prepare a deliberate reconciliation of their identities and histories before resuming; do not create another ID or discard evidence to bypass the conflict. The helper does not automatically merge, delete or migrate those records. Read-only inspection, outcome recording and finishing owned runs remain available so existing receipts and uncertainty can be preserved. Unrelated projects can continue.

```powershell
$founderSkillDir = 'C:\actual\loaded\second-founder' # Replace from the loaded SKILL.md location.
$founderCli = Join-Path $founderSkillDir 'scripts\founder_state.py'
$stateDb = Join-Path $env:LOCALAPPDATA 'SecondFounder\state.sqlite3'
python $founderCli --db $stateDb init
python $founderCli --db $stateDb register-project --project example-saas --root 'C:\Projects\example-saas' --domain 'https://example.com'
python $founderCli --db $stateDb register-shared-account --destination 'provider:EXACT_FOUNDER_ACCOUNT_ID'
```

Equivalent POSIX-shell initialization (replace all project and skill placeholders; on macOS choose the state location above):

```sh
founder_skill_dir='/absolute/path/to/loaded/second-founder'
founder_cli="$founder_skill_dir/scripts/founder_state.py"
founder_state_root="${XDG_STATE_HOME:-$HOME/.local/state}/second-founder"
founder_db="$founder_state_root/state.sqlite3"
python3 "$founder_cli" --db "$founder_db" init
python3 "$founder_cli" --db "$founder_db" register-project --project example-saas --root '/absolute/path/to/example-saas' --domain 'https://example.com'
python3 "$founder_cli" --db "$founder_db" register-shared-account --destination 'provider:EXACT_FOUNDER_ACCOUNT_ID'
```

The remaining examples use PowerShell to show JSON handling; the helper's subcommands, flags and JSON results are identical on supported hosts. Translate shell syntax, quote paths and parse JSON with the available language rather than invoking PowerShell syntax from a POSIX shell. Check each process exit code as well as its JSON `ok` field.

Register every shared personal account **before its first reservation**. Use `provider:immutable-account-id` consistently; display names, handles and per-project aliases do not identify the same calendar. Shared-account registration then makes time slots mandatory for that destination. All supplied slots, including brand-account slots, are checked against every project. Overlap uses half-open intervals `[start, end)`; adjacent slots are allowed. The interval must cover the saved spacing policy, not merely the second of publication. A slot remains reserved after failure or uncertainty. There is deliberately no release command.

Overlap protection **does not enforce a global daily post-count cap, quiet hours, relevance, or per-project allocation**. Save a shared calendar policy with fixed allowed windows, daily limits and project allocation during onboarding. Before reserving, read all projects' reservations with `status --limit -1`, including verified publications, and choose only those configured windows; serialize allocation through the shared founder-calendar planning run if multiple projects could compete. A worker must not invent additional nonoverlapping windows to escape the cap. The CLI enforces collision prevention, not that higher-level calendar policy. A recovery attempt within an existing slot does not create an additional intended post.

Registration refuses to designate an account shared when it already has unslotted actions. Investigate and migrate that history deliberately with all workers stopped; do not change its identifier to bypass the check. Accounts with multiple connected provider IDs still need one canonical calendar identity or a higher-level shared calendar allocation; this helper cannot infer that two provider IDs refer to one social account.

## Acquire, renew and finish a run

```powershell
$run = python $founderCli --db $stateDb start-run --project example-saas --lease-seconds 3600 | ConvertFrom-Json
if (-not $run.ok) { throw $run.error }
$leaseArgs = @('--project','example-saas','--run-id',$run.run_id,'--lease-token',$run.lease_token)
$renewal = python $founderCli --db $stateDb renew-run @leaseArgs --lease-seconds 3600 | ConvertFrom-Json
if (-not $renewal.ok) { throw $renewal.error }
# Execute bounded work, renewing before the lease expires and before external effects.
python $founderCli --db $stateDb finish-run @leaseArgs --evidence-ref 'file:state/runs/2026-10-12-summary.json'
```

Only one active lease is allowed per project. Lease durations range from 30 seconds to 24 hours, defaulting to 30 minutes. Mutation calls require the matching active run and token. Renew regularly during long research/render operations; a renewal after expiry is refused. **Immediately before each external API attempt or deployment, renew successfully and recheck the returned operation/attempt ownership.** If renewal fails, stop that effect and reconcile; a stale resumed worker must not continue from a previously printed `submit_authorized: true`. The time between ownership check and remote call cannot be fenced by this local helper, so never take over a worker that may still send. A project lease is not a Git or filesystem lock for other tools or projects. Coordinate separate projects sharing a repository before editing it.

An expired lease remains a lock until a deliberate takeover. First establish that the old worker has stopped and inspect outstanding provider requests. Then use:

```powershell
$run = python $founderCli --db $stateDb start-run --project example-saas --takeover-stale --evidence-ref 'file:state/recovery/old-worker-stopped.json' | ConvertFrom-Json
```

An unexpired lease cannot be taken over. Expiry by itself does not cancel a network request or fence a stale worker at a remote provider. Never take over a live worker merely because it is slow. Takeover marks the old run abandoned and any remaining `prepared` actions `unknown`; existing reservations and calendar slots stay intact. Finishing a run also marks its unresolved `prepared` actions `unknown`. Scheduled and published actions retain their states.

## Reserve before any external attempt

Use a stable operation key for the intended operation, independent of run ID, attempt count or current time. Fingerprint a canonical manifest containing the exact final copy, ordered asset hashes, target and any provider-affecting settings. A SHA-256 of a source filename or mutable URL alone is insufficient. Do not add a timestamp or change a key simply to bypass duplicate protection.

```powershell
$packageHash = (Get-FileHash -LiteralPath 'C:\Projects\example-saas\state\packages\launch-v1.json' -Algorithm SHA256).Hash.ToLowerInvariant()
$reservation = python $founderCli --db $stateDb reserve-action @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --kind social --destination 'postiz:EXACT_FOUNDER_INTEGRATION_ID' --fingerprint $packageHash --slot-start '2026-10-12T09:00:00Z' --slot-end '2026-10-12T09:30:00Z' | ConvertFrom-Json
if (-not $reservation.ok) { throw $reservation.error }
if (-not $reservation.submit_authorized) { throw 'Existing operation: inspect and reconcile; do not resend.' }
# Independently check saved authority, live account identity, content/media QA and provider rules.
# Make at most one initial provider attempt for this new reservation; immediately record its result.
```

For brand destinations, the same pattern applies. Slot flags can be omitted only for destinations not registered as shared. Use kinds `social` and `blog` for publications; the helper applies stronger URL/receipt requirements to their `verified` state. Other descriptive kind identifiers can represent a deploy or reversible change. Destinations for other actions identify an immutable target, for example `vercel:PROJECT_ID_PRODUCTION`. The profile and approved package must supply action-specific checks and rollback details.

Reservation happens inside `BEGIN IMMEDIATE`; calendar overlap checks, duplicate checks and insertion are atomic across processes. A global uniqueness constraint also prevents the same exact package fingerprint at the same destination under a second operation key. Reusing an operation key with different kind, destination, hash or slot is rejected. An exact repeat returns the existing action and **`submit_authorized: false` in every state**. That includes `prepared`, `failed`, `blocked` and `unknown`. A successful reservation is local eligibility for one initial attempt, not new user authorization or a guarantee of remote success.

If the process dies or output is lost after committing a reservation, a repeat does not authorize another attempt. Treat the operation as potentially submitted and reconcile first. This conservative behavior can leave an unsent item reserved; it avoids automatically duplicating a successful but unrecorded request.

## Record outcomes and reconcile uncertainty

```powershell
python $founderCli --db $stateDb record-outcome @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --outcome scheduled --remote-id 'PROVIDER_POST_ID' --evidence-ref 'file:state/receipts/provider-response.json'
python $founderCli --db $stateDb record-outcome @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --outcome published --public-url 'https://social.example/posts/123' --evidence-ref 'file:state/receipts/published-status.json'
python $founderCli --db $stateDb record-outcome @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --outcome verified --evidence-ref 'file:state/receipts/live-post-check.json'
```

`record-outcome` requires a nonempty evidence reference. `scheduled` and `published` require the provider's remote ID; `published` additionally requires a public URL. `verified` social/blog publication needs both plus actual verification evidence. The remote ID cannot change within an attempt. A supported new recovery attempt clears its current receipt fields while preserving prior receipts in the event history. Verified operations cannot be downgraded. Published operations cannot be reset to an unsent state, including through an intermediate `unknown` state: their durable published/verified history prevents a later `failed`, `blocked` or `prepared` outcome and prevents a no-side-effects retry. If a previously published result later becomes uncertain, retain its receipt and reconcile that existing result; do not create a replacement automatically. Every accepted outcome appends an event tagged with its attempt key.

Use `prepared` for a locally ready package; `scheduled` only for provider acceptance; `published` only for the provider's published result with a public URL; and `verified` only after checking the expected live result. `failed` means evidenced failure; `blocked` means a known unmet prerequisite; `unknown` means delivery or completion remains uncertain. A queue response is not publication. For a nonpublication action, `verified` requires references to its meaningful checks and observed result. The helper checks field presence, **not the truth or contents of referenced evidence**. It cannot turn an uninspected receipt into verification.

For timeouts or ambiguous provider responses:

```powershell
python $founderCli --db $stateDb record-outcome @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --outcome unknown --evidence-ref 'file:state/receipts/timeout.json'
# Read provider status/search results and inspect any matching live result before recording a resolution.
python $founderCli --db $stateDb record-outcome @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --outcome published --remote-id 'MATCHED_PROVIDER_POST_ID' --public-url 'https://social.example/posts/123' --evidence-ref 'file:state/receipts/published-status.json' --reconciliation-ref 'file:state/recovery/exact-package-match.json'
```

Updating an `unknown`, `failed` or `blocked` action, or an action reserved by an earlier run, requires a reconciliation reference. The agent must actually perform that reconciliation with the provider/tool; the helper does not perform it. A negative search or elapsed time alone does not establish that a delayed request cannot complete. `record-outcome` cannot reset an operation to prepared. There is no unreserve or deletion command.

### Bounded recovery after conclusive failure

Routine recovery within the saved scope needs no fresh owner approval when provider-specific evidence conclusively establishes that the prior attempt failed with **no side effects and no pending request that could later succeed**. Record that definitive failure first; resolving an `unknown` outcome to `failed` requires the reconciliation reference. A timeout, HTTP error, empty search result, missing public URL or provider `ERROR` with a possible partial thread is insufficient. Preserve successful destinations; recover only the failed destination.

```powershell
python $founderCli --db $stateDb record-outcome @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --outcome failed --evidence-ref 'file:state/receipts/definitive-rejection.json' --reconciliation-ref 'file:state/recovery/no-pending-or-partial-effect.json'
$retry = python $founderCli --db $stateDb reserve-retry @leaseArgs --operation-key 'launch-tutorial-v1-founder-x' --attempt-key 'recovery-definitive-rejection-1' --confirmed-no-side-effects --evidence-ref 'file:state/receipts/definitive-rejection.json' --reconciliation-ref 'file:state/recovery/no-pending-or-partial-effect.json' | ConvertFrom-Json
if (-not $retry.ok) { throw $retry.error }
if (-not $retry.submit_authorized) { throw 'Recovery already reserved: reconcile instead of sending.' }
$renewal = python $founderCli --db $stateDb renew-run @leaseArgs | ConvertFrom-Json
if (-not $renewal.ok) { throw $renewal.error }
# Only after renewal succeeds, use the provider's documented recovery/idempotency behavior once.
# Record the outcome immediately. If uncertain again, record unknown and reconcile.
```

The stable retry key names this particular evidenced recovery, never a new random key on rerun. `reserve-retry` atomically allows one new attempt only from `failed`, requires both evidence references and an explicit no-side-effects assertion, and caps an operation at **three total attempts**. Replaying the same retry key returns `submit_authorized: false`; another retry key cannot authorize from `prepared` or `unknown`. Its fingerprint, original operation identity and reserved calendar interval remain unchanged. An expired calendar interval blocks this helper's retry; defer to a deliberate provider scheduling/recovery plan that preserves the original operation and shared calendar policy. This helper does not reschedule slots or release them. Do not silently move the date, invent a new operation key, or edit the database to bypass that limit.

As with outcome evidence, the helper cannot verify the assertion's truth. The agent must inspect the provider's actual state and rules before calling it, and must keep the same saved authorization and no-additional-spend constraints. Stop after the bounded attempts fail; investigate and preserve the exact package instead of looping.

## Inspect and report

```powershell
python $founderCli --db $stateDb status
python $founderCli --db $stateDb status --project example-saas
python $founderCli --db $stateDb status --pending --project example-saas
python $founderCli --db $stateDb status --limit -1
python $founderCli --db $stateDb status --project example-saas --operation-key 'launch-tutorial-v1-founder-x'
```

Status returns the latest 100 runs/actions by default (`--limit` changes that; `--limit -1` returns all), and an operation-specific view includes its ordered event history. **Start each recovery scan with `status --pending --project PROJECT_ID`**: it returns every nonverified action, oldest first, regardless of `--limit`, so older scheduled, published, uncertain, failed or blocked work cannot disappear behind newer history. Run history still respects `--limit`. Omit `--project` to scan all projects; `--pending` and `--operation-key` are separate views and cannot be combined. Use `status --limit -1` for shared calendar planning, because already verified posts still count toward spacing and daily caps. Status excludes lease-token hashes. Slot and run times are UTC Unix seconds; slot input requires an explicit timezone. Expected operational errors return JSON with `ok: false`, an explanation, and exit code 1. Argument syntax errors use argparse's usual exit code 2. Read-only status is a local snapshot, not fresh provider status. Reconcile unfinished work before beginning another daily batch, preserve successful destinations, and report separate prepared/scheduled/published/verified totals.
