# project-journal — a flight recorder for your projects

> **Install once. From then on, every AI session automatically records your decisions, blockers, solutions, and real numbers (time / cost / conversion / revenue) — until the project succeeds or fails. On closeout, it hands you a redacted, sellable case-study asset pack. It also logs and patches itself.**
>
> ### Projects can fail. They shouldn't die in vain.

<!-- 🎬 Demo GIF: record per the demo script, export demo.gif into assets/ and uncomment the line below -->
<!-- ![30-second demo: from install to your first asset pack](assets/demo.gif) -->

**The 30-second version**

- **No discipline required** — a session anchor is injected into your repo root. Any future session (new tool, new agent, three days later) auto-discovers the recording protocol and keeps logging, so you never have to remember to "write things down".
- **No diary spam** — it only captures what carries judgment, conclusions, or numbers: decisions, blockers, solutions, insights, real metrics.
- **Closes the loop** — you write your success and stop-loss lines up front. At closeout, the tool judges the outcome against them and generates a case study / playbook / lessons asset pack.

[Install (30s)](#install-30-seconds) ｜ [Full methodology pack ↓](#want-the-full-methodology) ｜ [中文](README.md)

---

## Six commands

**Short phrases are the commands** — no long sentences to memorize:

| You say | It does |
|---|---|
| **track this project** | Start tracking (first time) / resume tracking (existing) |
| **journal this** | Persist what just happened (decisions / problems / solutions / insights / numbers) |
| **project status** | One-line check-in: stage / stalled days / open items / metrics |
| **retro** | Generate a weekly or monthly review skeleton |
| **closeout** | Final verdict: success / failure / pivot / paused |
| **publish** | Generate the redacted, sellable asset pack |

Natural language works too ("start tracking this project", "log today's work", "how's this project doing", "can we sell it yet").
Chinese keywords also supported: 跟踪项目 / 记一下 / 项目状态 / 复盘 / 结项 / 出资产.

## Install (30 seconds)

```bash
git clone https://github.com/lh123aa/project-journal.git ~/.agents/skills/project-journal
# Windows: %USERPROFILE%\.agents\skills\project-journal
python ~/.agents/skills/project-journal/scripts/install-global.py   # register to all tools
```

Covers: Claude Code / opencode / Cursor / Codex CLI / Gemini CLI / Windsurf.
Requirements: **Python 3.8+, standard library only. Zero third-party dependencies.**

> The first time you run "track this project", it asks you to write your **success line** and **stop-loss line** — the only objective yardstick that will judge whether the project succeeded. Don't skip it.

## What problem it solves

The things that are actually worth money mid-project — **why you chose this, where you got stuck, how you got around it, what the real numbers were** — evaporate within days if they're not written down. Three months later you can't even answer "why did I decide that?" Yet those are exactly the most valuable assets a finished project can produce:

- **For future you**: don't re-trip the same traps; reuse what worked
- **For the next AI / collaborator**: 30-second context recovery, no chat history required
- **For paying readers**: real process + real numbers + real lessons = a sellable case study

## How persistence works ("install once" is enough)

| Device | Role |
|---|---|
| ① Session anchor | A managed block injected into the repo's `AGENTS.md` (idempotent) — every future session picks up the protocol automatically |
| ② On-disk state | `STATE.md` + `tracker.json` give humans and agents a 30-second context reload, independent of chat history |
| ③ Closeout capture | "Unrecorded = it never happened for those who come later" — everything is persisted before the session ends |
| ④ Optional heartbeat | Host scheduled task to nudge daily capture |

Three data layers + one output:

```
Raw       journal/YYYY-MM-DD.md     append-only, never rewritten
Records   records/ (decisions / problems / solutions / experiments / insights / lessons / risks / milestones)
Numbers   metrics.csv · ledger.csv (metrics, income & cost)
Output    publish/<date>/           8 redacted, sellable asset files
```

## It records and patches itself

This skill manages itself as a project too:

- Everything that breaks in real use goes into [`evolution/LEDGER.md`](evolution/LEDGER.md) — **21 real fix entries, each with a reproduction and a regression test**
- Every fix must pass `scripts/selftest.py` — **38 regression checks** gating each release; failures abort the release
- After a fix: automatic version bump, CHANGELOG entry, and migration of existing projects (**without touching any journal or record**)

> In other words: **this is itself a complete case study of "a flight recorder recording its own birth."** Open the ledger and watch.

## Want the full methodology?

This README covers ~20% of it. The **"Project Journal · Methodology Pack"** includes:

- 📖 **Methodology handbook**: why record / what to record / how to judge (success & stop-loss lines) / how to turn process into sellable assets
- 🧰 **12 ready-to-use templates**: charter, weekly review, closeout verdict, case-study framework, redaction checklist…
- 📚 **Real case library**: full tracking → verdict → monetization records of real projects (updated quarterly)
- 🎬 **30-minute video**: from install to your first asset pack
- 🔄 **One year of updates**

**$19 early bird (first 100 copies; $29 regular)** · 7-day no-questions refund
👉 [Gumroad](#)

> Want **1-on-1 onboarding** (we install the recorder in your real project, 4 weeks + a closeout asset pack, $399)? [Contact me](#)

## Quickstart

From your project root:

```bash
S=~/.agents/skills/project-journal/scripts/journal.py

# 1) Kickoff (convention: record folder = <project root>/project-journal/)
python $S init --project "My Project" --stage S0 --currency USD \
  --hypothesis "who + what pain + willingness to pay + why you believe it" \
  --success   "3 consecutive months of net revenue >= $500 with < 1h/day effort" \
  --stop-loss "200 cumulative hours with < $100 revenue"

# 2) Read before every work session
python $S resume --root project-journal

# 3) Capture as you go (use --body-file for long text)
python $S add --root project-journal --type decision --title "Dropped the WhatsApp channel" --body-file d.md
python $S metric --root project-journal --name MRR --value 120 --unit USD --source Stripe
python $S ledger --root project-journal --kind income --amount 99 --channel Gumroad
python $S stage  --root project-journal --set S5 --why "first paying customer"

# 4) Wrap up
python $S index --root project-journal && python $S lint --root project-journal

# 5) Reviews / closeout / assetization
python $S review   --root project-journal --period weekly
python $S closeout --root project-journal --outcome success
python $S publish  --root project-journal        # redact -> 8 sellable asset files
```

## Command reference

| Command | Purpose |
|---|---|
| `init` | Create the record folder (idempotent) + inject the session anchor |
| `anchor` | Re-inject / refresh the anchor |
| `status` / `resume` | One-line check-in / "hydration pack" for new sessions |
| `add` / `update` | Append a record / update a record's status (e.g. problem solved) |
| `metric` / `ledger` | Metrics / income & cost |
| `stage` | Advance stages S0→S6 |
| `index` / `lint` | Rebuild index / health check (structure, IDs, secrets, staleness) |
| `review` / `closeout` | Weekly/monthly review skeleton / final archive & verdict |
| `publish` / `vault-index` | Redacted asset pack / cross-project overview |
| `upgrade` / `doctor` | Migrate existing projects / installation self-check |
| `evolve` / `evolve-list` / `evolve-apply` | Log the skill's own issues / view ledger / run the fix loop |

Record types: `task` `decision` `problem` `solution` `insight` `experiment` `metric` `risk` `lesson` `revenue` `cost` `milestone` `question`

## Design principles

- **Scripts handle structure, agents handle judgment** — the script does deterministic mechanical work (folders, IDs, indexing, pairing, redaction, health checks); the content is written by humans/agents
- **Append-only** — journals and records are never rewritten; corrections are new entries marked `[corrects <ID>]`. History is for learning
- **Facts vs. judgments** — subjective judgment is labeled explicitly; numbers carry unit/time/source/confidence
- **No fabrication** — unconfirmed stays "unconfirmed"; blank is better than wrong
- **Leak prevention** — `lint` scans for secrets and privacy; `publish` enforces redaction and emits an audit report
- **Pre-written verdict lines** — only the success/stop-loss lines in the CHARTER can judge the project

## Self-test

```bash
python scripts/selftest.py      # 38/38
python scripts/journal.py doctor
```

> `scripts/selftest.py` contains **fake secrets and emails** (e.g. `sk-abcdefghijklmnopqrstuvwx`) as redaction test fixtures — not real credentials.

## Version

**The latest version lives in [manifest.json](manifest.json); change history in [CHANGELOG.md](CHANGELOG.md); fix ledger in [evolution/LEDGER.md](evolution/LEDGER.md).**

## License

| Track | License | Price | Applies to |
|---|---|---|---|
| Free | [CC BY-NC 4.0](LICENSE) | $0 | Personal learning, research, teaching, non-profit internal use |
| Commercial | [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md) | ¥99 / ¥299 / ¥3k–10k | Company use, SaaS integration, white-label, training, paid services |

**CC BY-NC 4.0 identifier**

```
SPDX-License-Identifier: CC-BY-NC-4.0
```

> ℹ️ GitHub's license template library does not include CC BY-NC, so the sidebar shows "Other" — a platform limitation, not a configuration issue. The LICENSE + LICENSE-COMMERCIAL files are authoritative.
>
> Historical note: versions ≤ v1.2.2 were MIT (irrevocable for those who obtained them); v1.3.0+ are CC BY-NC 4.0 with a commercial track from v1.4.0.

---

*This is a readable summary, not legal advice; the full [LICENSE](LICENSE) text governs.*

📖 Full manual: [USAGE.md](USAGE.md) (Chinese).
