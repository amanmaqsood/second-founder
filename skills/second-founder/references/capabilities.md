# Discover, install and route capabilities

Use companions for a selected growth action. **Reuse what works; install missing skills by need.** The [companion routing guide](companion-skills.md) maps revenue bottlenecks to useful specialists. The [verified source registry](../assets/companion-registry.json) records public repositories, reviewed commits, complete skill folders, licenses, runtime requirements and integration limits. It is a reviewed starting set, not a requirement to install 54 skills or a promise of future availability.

## Discover before installing

1. Inspect the current host's exposed skills, connectors and tools. Check relevant project/user skill roots (`.agents/skills`, `.codex/skills`, `.claude/skills`) and installed plugin registries/caches on this machine. Honor custom roots, plugin ownership and resolved links; do not scan unrelated personal folders or credential values. A useful Claude plugin may exist even when absent from Codex's catalog.
2. Identify a companion by provider plus its actual path or plugin namespace. Deduplicate equivalent copies, without deleting or rewriting them. Names such as `research`, `plan` and `review` can belong to different providers. Never identify a vaguely named skill by guesswork.
3. Read the installed entrypoint and relevant references. An adequate existing installation wins over a newer catalog revision. Do not silently upgrade, overwrite a customization or create a duplicate of a plugin-managed skill. Instructions from another host can inform a scoped task, but its tools and permissions are not inherited.
4. Prefer a working connected tool or existing workflow when it already supplies the capability. Register only the providers needed for the current project. Missing optional companions must not delay independent work.

Discovery is broad; invocation is selective. Do not load every installed skill into every run. Recheck the affected capability after a failure, source update or changed project binding; do not reinstall and audit the whole machine each day.

## Installation authority

Install when the current owner's saved scope includes `necessary_no_cost_capability_installation` and the operation fits the saved budget. Without that grant, prepare the exact source, purpose, dependencies and permissions as one onboarding decision while ready work continues. Once granted, routine in-scope installation does not need repeated approval. The public skill template itself grants no installation authority.

Installing skill text does not authorize account creation, broad permission changes, browser-cookie extraction, paid trials, purchases, external messages, private-data uploads or global machine reconfiguration. Existing API keys do not prove included capacity. Runtime setup is a separate operation: inspect dependency installers and enable only required backends. Carry the saved limits through nested workers and installers too.

## Install the selected companion

1. Select the exact provider and skill entry from the registry. Read its routing cautions and current installed state. For a capability outside the registry, verify its official repository, license, exact revision, resource closure and runtime requirements first; record the reviewed source locally before installation. Search supported plugins/connectors when an external service is needed. Do not invent an installer for an unavailable service.
2. Fetch the source into a fresh task-owned staging folder. Check out the recorded commit, verify `git rev-parse HEAD`, and read that revision's `SKILL.md`, referenced resources and relevant executable setup. A registry entry is evidence of a previous review, not permission to skip inspection of the actual bytes. Do not execute downloaded code just to inspect it.
3. Install only the selected **complete skill folder**, including its references/scripts/assets. Prefer the host's supported installer. On Codex and Claude Code with Node/Git, a reviewed Skills CLI can install the checked-out local folder to the selected host(s). Use project scope by default, unless the owner chose user-wide scope. Inspect destination collisions before invoking a noninteractive installer; it may overwrite files.
4. For manual installation, copy that full folder into the host's documented skill root under its exact skill name and retain the upstream license/copyright. Do not copy only `SKILL.md`. Codex's skill-installer may also accept exact repository/path/ref; Claude does not automatically have that helper. For Claude web/Desktop, use its supported upload/install flow; local filesystem copies in an ephemeral chat do not register persistent skills. Prepare the companion package and connection instructions if the host cannot install it directly.
5. Handle provider dependencies from the selected workflow, not all neighboring references. Co-founder's full persistent workflow is an exception: prefer its namespaced native plugin or complete linked suite after establishing a separate business workspace; its vault setup and Ruby helper must be ready. A standalone `gauntlet` verbal review need not create a vault. Do not automatically run setup in a product repository or overwrite `AGENTS.md`/`CLAUDE.md`. Plugin flows that cannot pin a commit require inspection of the actually installed revision before use.
6. Retain the upstream license and copyright with the installed files if the installer omits the repository-root license. Verify installation and readiness separately. Confirm the installed name/resources and actual source; confirm host discovery or report that a new session is needed. Then check only required runtime/backend/authentication and run a harmless relevant smoke check. No dummy public post, customer mutation or live purchase. Record limits and continue with a fallback if full setup cannot complete.

For example, **after selecting Brag and checking installation authority**, these command shapes use a reviewed immutable source. Replace `<fresh-checkout>` with a new path and quote it correctly for the shell; select only hosts in use. Inspect source and destination between checkout and installation.

```text
git clone --no-checkout --filter=blob:none https://github.com/latent-spaces/brag.git <fresh-checkout>
git -C <fresh-checkout> checkout --detach 8531ccb9f471ef5099abf930079e47b55c55bb21
git -C <fresh-checkout> rev-parse HEAD
npx --yes skills@1.7.2 add <fresh-checkout>/skills/brag --skill brag --agent codex claude-code --yes --copy
```

The CLI version is a verified compatible example, not an instruction to replace a working installer. `--global` is deliberately absent from this project-scoped example. This installs instructions; it does not configure Node/FFmpeg/HyperFrames, render a video, or grant publishing authority. Adapt source/path/name from the registry for other providers. Preserve the source receipt when a local-folder install cannot retain upstream provenance automatically.

On a missing commit, failed integrity check, unsupported runtime or changed license, do not silently switch to an unreviewed branch or similarly named fork. Review a replacement explicitly, use an adequate existing capability, or mark the affected lane unavailable. Updates use the same review process, preserve local modifications and readiness history, and never mutate plugin-managed files through another updater. A revocable provider entry or source pin is not a security certification.

## Record project readiness

Keep `.second-founder/capabilities.json` private. Store a compact entry for each selected role: provider/skill names; host, scope and resolved installation path; actual repository/revision or plugin version; install status; runtime/backend; exact project/account binding; credential reference only; applicable saved authority; cost/allowance evidence; verification operation/time/result; limitation and fallback. Use statuses `missing`, `installed_setup_required`, `ready` and `unavailable`. Only the selected operation can be ready: a research connection does not establish a publishing connection, and a local renderer does not establish Instagram access.

`profile.capabilities.installation_policy` defaults to `on_demand`; `registry_file` points to this private readiness file. These fields record policy and evidence locations, not a new authority grant. For older profiles, add missing fields without resetting existing setup, accounts, history or permissions. Batch unresolved logins into one precise request and continue ready work. Reuse successful readiness checks until the relevant tool, account, source or runtime changes; respect token expiry and provider failures.

## Native capabilities still matter

| Need | Route |
|---|---|
| Social publication | Project's verified provider, connector or CLI, such as Postiz; exact account bindings and shared publication ledger |
| Images | Available image generator or design tools; saved visual policy and final asset review |
| Database/revenue | Existing scoped provider client/API; aggregate read-only analytics and verified metric definitions |
| Code/deployment | Applicable installed engineering skills plus the project's tested deployment and rollback workflow |
| Recurrence | Codex app automation only where exposed, or the current host's supported persistent runner; reuse the existing job |

Project-specific publishing or SEO wrappers can supply reusable ideas, but never transfer their accounts, domains, private assets, authorization or schedulers. Keep private wrappers out of the public auto-install catalog. The final output still passes Second Founder's factual, content, scope, duplicate and live-verification checks.
