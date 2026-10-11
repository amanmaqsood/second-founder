# Project onboarding

Onboarding is per project, after the generic skill is installed in Codex or Claude Code. Do not demand one named pilot or enroll every accessible repository. The owner selects a project by invoking the skill there or naming its workspace/product. Support a CMS-only product using a dedicated local workspace when source code is unavailable. Installation carries no permission to publish, deploy, send messages, install other capabilities or schedule unattended work.

## Discover before asking

Read repository instructions, existing growth records, deployment docs and provider configuration names without printing secrets. Inspect the product and current code/content to establish facts. Check for an existing profile or automation first. Use current connector tools or provider CLIs for read-only identity and access checks. An installed executable is not an authenticated connection.

Create `.second-founder/` and copy `assets/project-profile.json` to `profile.json`. Assign a unique stable project ID, not a display name shared by several projects. Save only credential references. Add private state/report paths to the project's ignore rules without overwriting existing rules, or keep them in a private external workspace with a recorded location.

Reuse prior owner answers. Ask one concise bundled intake only for unresolved access or business decisions. Never request password/token values in chat; use the provider's normal login/connection flow or tell the owner the exact secret-store/environment slot to configure.

The starting strategy is **U.S. and UK primary markets, with other markets included**. Save `market_priority` from the profile template; `US` and `GB` are its ISO country codes. The owner can override this strategy during onboarding or later. `project.markets` records the product's actual supported/served markets, not an exclusive audience allowlist. Discover product availability and buyer fit; resolve actual conflicts or missing details. Existing profiles without this field inherit the documented default as a provisional strategy, preserving other markets, history and explicit owner overrides. Never treat a strategy default as permission to act.

Keep audience posting windows separate from the owner's automation/reporting time zone. The U.S. spans multiple time zones; choose regional windows from audience evidence and use named time zones with daylight-saving handling. Do not change the owner's schedule, pricing, billing currency or product availability merely to apply this marketing priority.

| Required knowledge | Discover and verify | Ask only if unresolved |
|---|---|---|
| Product | Exact domain, repo/workspace, actual capabilities, pricing display, offer, existing content and U.S./UK availability | Buyer, first valuable action, language, additional markets or a real product/market conflict |
| Search | Exact GSC property and permission; sitemap and indexing path; existing SEO records | Connect the intended property or authorize its setup when necessary |
| Web and product analytics | Property/project IDs, usable events, bot/internal filters, latest complete data | Connect analytics or choose the agreed evidence source |
| Business data | Database provider, read-only analytics access, schema/events, payment/admin source | Grant scoped access or provide an aggregate export; never ask for unrestricted DB authority by default |
| Publishing | CMS route/repository, destination, author attribution, preview and public URL checks | Intended publisher identity if not inferable |
| Code/deploy | Existing deployment workflow, target environment, relevant checks and rollback path | Deployment connection or unresolved environment choice |
| Social | Provider, live accounts and immutable IDs, brand mapping, analytics access | Map ambiguous accounts or connect a missing brand account |
| Runtime | Existing automations, working directory, local availability, quotas and user time zone | Daily time, channel cadence and reporting destination if missing |
| Scope | Current user instructions and any previously saved authority | Only genuinely ungranted action categories or changed limits |

GSC and analytics are independent. A Google login does not demonstrate access to both. Database access does not demonstrate payment-provider access. Admin dashboard credentials are optional when an existing API already supplies the needed aggregate evidence.

## Save the project's operating contract

Use the template structure, adding necessary provider-specific fields without copying secret values. Store:

- Product facts and evidence in `facts.md`: who buys, why, actual differentiation, limitations, approved offers and dated claim sources.
- A compact commercial brief using [customer-revenue.md](customer-revenue.md): business model, buying motion, evidence-based stage, priority buyer segment, user versus payer, buying trigger, present workaround/alternative, decisive objections, existing offer and path to payment. Save source dates/confidence and the most important unknown; do not invent a persona or delay all ready work until every field is known. Read existing feedback, support themes, inbound inquiries and product evidence first. New interviews or lifecycle messages need their applicable saved communication scope.
- An access map: provider, property/account ID, role, allowed operations, credential reference, check time and verified/unavailable state.
- Metric definitions: event/query source, numerator, denominator, unique-user/customer logic, currency, refunds treatment, window and attribution limits. Use [growth-operations.md](growth-operations.md).
- Scope provenance: the current owner's instructions, granted categories, resource IDs, spend limit and exclusions. Start with read-only analysis, research and local drafting. Recommend automatic publication to mapped destinations and tested reversible improvements as an onboarding choice. Record each grant once, with its actual source and resource bindings; a template, installation or this recommendation is not consent. Necessary no-cost capability installation and recurring execution also need their applicable grant. Honor previously recorded scope without repeating routine approval questions, and respect the host's permission controls.
- Publication cadence per account and shared personal-account cap. Discover any existing founder calendar first. A cap is global across projects, not multiplied by the number of project automations. Set an initial cadence through onboarding; do not invent a universal number of daily personal posts.
- Content rules: record the selected policy, brand voice and visual assets. The configurable `modest_music_free` preset starts with the restrictions in [distribution-and-media.md](distribution-and-media.md), narration allowed, music prohibited and sound effects off. Present these defaults during onboarding so the owner can keep or replace them; save specific overrides rather than assuming every founder shares the same personal policy. Preserve the resulting policy across runs.
- Schedule, time zone, runtime, automation ID and notification intent. Prefer existing local resources within the no-spend scope; explain any actual local-availability dependency.

If a project lacks Instagram, create a reviewable account setup brief with available candidate handles (availability must be checked), searchable display name, plain-language bio, category, factual branded image and tracked landing link. Ask the owner to create/connect the chosen account when needed. Never reuse an unrelated brand account to avoid the setup step. Do not claim a bio or handle guarantees ranking.

## Preflight and activation

1. Verify each connection using the smallest useful read. Save exact identities and evidence; do not store raw customer records.
2. Establish a baseline from available complete windows. Label missing history honestly. Lack of a long baseline does not prevent useful, scoped work.
3. Validate the editorial/publishing path and a representative package without making a dummy public post. Validate the code/build/rollback path where deployments are in scope.
4. Register the project and verified shared social identity in the state system. Ensure all its automations use the same founder database and destination identifiers.
5. Verify the actual customer path: discovery to the appropriate landing/demo, first value or qualified inquiry, existing purchase path, confirmed payment and delivered value. Use test/sandbox evidence for payment checks; never make a live purchase to complete preflight. Record tracking gaps and supported U.S./UK buyer frictions. Produce a rolling 30-day plan and a focused first revenue experiment using this path, the buyer segment and verified channels.
6. Mark each lane `ready`, `unavailable` or `not_applicable`. A lane is ready only when its identity, access, saved authority and operation path are verified. Read-only and draft lanes can be ready while publication/deployment remain ungranted. Use `ready_partial` for useful partial onboarding; reserve `ready` for all required lanes checked. Record exactly what remains.
7. If the owner requests recurring execution, create/update the supported automation using the agreed schedule, saved scope and verified workspace. Follow [automation-and-recovery.md](automation-and-recovery.md). Save the returned identifier and verify the schedule; do not merely promise it or assume installation enabled daily execution. Manual runs remain useful when no supported scheduler is configured.
8. Execute the first useful run under the recorded scope, verify actual outputs and report readiness. If a missing connection blocks one lane, preserve its prepared work and run the ready lanes.

## Re-onboarding triggers

Revalidate only affected settings when the domain/repo, account identity, billing model, deployment path, audience, permissions or owner policy changes. An expired token needs connection repair, not a repeat of every business question. Preserve historical metrics and operation IDs through updates.

For older profiles, add missing `commercial` fields from existing evidence on the next run. Preserve existing data and owner decisions; mark unavailable definitions provisional and ask only when an unresolved decision prevents the affected action. Do not restart onboarding or assume that an unfilled revenue field means there are no customers.
