# Second Founder

**A reusable growth skill for Codex and Claude, focused on paying customers and sustainable revenue.**

Give your agent a coordinated daily workflow for search, useful content, social distribution, customer activation, purchase friction and retention. Apply it to any product; each project keeps its own accounts, evidence and operating scope.

## Install in one command

For **Codex and Claude Code**, run this in your terminal with Node.js 22.20+ (current LTS recommended) and Git installed:

```sh
npx --yes skills add amanmaqsood/second-founder --skill second-founder --agent codex claude-code --global --yes --copy
```

This installs the same skill for both agents across your projects. For just one, remove the other agent name. Remove `--global` to install only in the current project. The command uses the open-source [Skills CLI](https://github.com/vercel-labs/skills); copy mode works without creating symbolic links.

Open your product's project in your agent and start:

**Codex**

```text
$second-founder Onboard this project, establish my operating scope, and set up daily growth work focused on paying customers.
```

**Claude Code**

```text
/second-founder Onboard this project, establish my operating scope, and set up daily growth work focused on paying customers.
```

If the skill does not appear, restart your agent. See the official [Codex skills](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skills](https://code.claude.com/docs/en/skills) documentation.

### Claude web or Desktop

Download [second-founder.zip](https://github.com/amanmaqsood/second-founder/releases/latest/download/second-founder.zip). In Claude, open **Customize → Skills → + → Create skill → Upload a skill**, upload the ZIP and enable it. Then ask: “Use Second Founder to review my product and prepare its growth plan.” See [Claude's upload instructions](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

The upload provides the workflow and references. Publishing, repository changes and persistent daily execution need tools and a durable runtime that are actually available in that Claude environment. An ephemeral chat sandbox is suitable for analysis and drafts; uploading a ZIP does not create a background service.

### Install without Node.js

Download the same ZIP, extract it, and copy its complete `second-founder` folder into:

| Agent | User-wide skill folder |
|---|---|
| Codex | `~/.agents/skills/second-founder/` |
| Claude Code | `~/.claude/skills/second-founder/` |

Here `~` means your user home directory, including on Windows. `SKILL.md` must sit directly inside the `second-founder` folder. Copy all supporting files too. These are the agents' documented [Codex](https://learn.chatgpt.com/docs/build-skills) and [Claude Code](https://code.claude.com/docs/en/skills) locations.

## What it does

- **Find the buyer:** distinguish users from payers, purchase triggers, alternatives and real objections.
- **Choose the bottleneck:** first customers, activation, conversion, checkout or paid retention.
- **Grow useful search demand:** inspect available Search Console data, technical issues, intent and existing content; write researched tutorials and fair comparisons.
- **Distribute deliberately:** maintain a rolling 30-day plan, adapt posts to relevant channels, create images and videos through available tools, and coordinate shared founder accounts.
- **Improve the product:** prepare or ship scoped, tested, reversible improvements with live verification and a rollback path.
- **Measure real outcomes:** separate qualified demand, signups, collected payments, refunds and retained customers; respect attribution gaps and immature cohorts.
- **Recover reliably:** use a local SQLite helper for run leases, publication reservations, shared calendar conflicts and duplicate prevention.

Read the [skill entrypoint](skills/second-founder/SKILL.md) or its [customer and revenue playbook](skills/second-founder/references/customer-revenue.md).

## One setup per project

The agent discovers what already exists, then bundles the remaining setup questions. You provide the intended project/domain, connect the relevant publishing and analytics tools, set a schedule, and choose its operating scope. Credentials stay in your normal secret store or connection flow.

The public template begins with research and drafts. You can authorize automatic publication to specific accounts and tested reversible deployments during onboarding; that authority persists across runs. Pricing, billing, destructive operations, outreach and additional spending require separate scope. Installing the skill grants none of these permissions by itself.

Project settings and history live in `.second-founder/`, outside the installed skill. Each project has separate bindings. Shared personal accounts use one founder calendar on one persistent local database.

## Defaults you can configure

| Setting | Included default |
|---|---|
| Main outcome | Paying customers and sustainable revenue |
| Primary markets | U.S. and UK, with other markets included |
| Editorial | Two useful articles per day as a target; fewer when quality or evidence is insufficient |
| Distribution | Rolling 30-day plan and useful publishing at the saved channel cadence |
| Spending | No additional spending; verify existing included allowances |
| Media | Music-free, narration allowed, sound effects off |
| Content policy | A modest Islamic preset; factual product visuals preferred |

The preset excludes visible women, nudity, sexualized imagery, alcohol, gambling, pork, drugs, profanity and blasphemous wording. Record your own brand/content policy during onboarding. The skill must follow the saved policy consistently.

## Tools and daily automation

The skill uses your existing tools: a CMS or repository, social publisher, Search Console, analytics, aggregate business/revenue data and deployment workflow as applicable. No particular social service or paid subscription is required. Missing access blocks only the dependent work.

The local coordination helper needs **Python 3.10+** and uses only the standard library. It does not publish content or query providers itself. An actual daily run also needs a persistent workspace, authenticated integrations, included model/tool capacity and a verified scheduler. Codex app automation is used where available; Claude Code and other environments use their supported configured runner. Setup reports when scheduling is incomplete.

## Updates and development

Rerun the install command to take the current version. Keep project configuration in `.second-founder/`; preserve any edits you made to installed skill files before replacing them.

From a clone of this repository:

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
```

To build the uploadable ZIP and its checksum, run `python scripts/package.py`. Files are written under `dist/`.

Tests exercise isolated local state. They do not demonstrate live publishing, agent reasoning quality or revenue uplift. Report reproducible issues through [GitHub Issues](https://github.com/amanmaqsood/second-founder/issues), with credentials and customer data removed.

## License

[MIT](LICENSE). You can use, modify and redistribute the skill, including commercially, under that license.
