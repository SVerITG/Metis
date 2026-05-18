# Test Suite — Critical Gap Analysis (Opus Review)

**Reviewer:** Independent audit, Opus 4.7 (1M ctx)
**Date:** 2026-05-15
**Subject:** `metis/system/tests/` — unit/, integration/, e2e/, personas/, audit/

This review takes the perspective of a future maintainer who inherits a green
test suite and assumes the product works. The verdict in one line:

> **A fully green test run today proves the repository is structurally laid
> out as intended. It proves almost nothing about whether the dashboard
> behaves correctly when a real researcher uses it.**

The tests are heavy on file-existence and keyword-presence checks, and very
light on behaviour. Below is what fails on closer reading.

---

## Tests that are too weak

### 1. `test_partial_returns_200` accepts crashes as passes
**File:** `integration/test_dashboard_routes.py`
```python
assert resp.status_code in (200, 404, 500)
```
A test that accepts **500** as a valid status is not a regression test — it is
a marker that the route was visited. Five partials are exercised this way; any
of them can be broken in production and this suite will never tell you. The
`raise_server_exceptions=False` flag on the TestClient compounds the problem:
exceptions are swallowed into 500 responses, then the assertion happily
accepts them.

**Fix:** assert `resp.status_code == 200` for partials that are required to
work. Use `pytest.xfail` or a `known_gap` marker for the genuinely unfinished
ones — never blanket-accept 500.

### 2. `test_guardrails.py` duplicates the pattern list — drift is invisible
**File:** `unit/test_guardrails.py`
The test defines its own `_INJECTION_PATTERNS` list locally and tests that.
If `tools/guardrails.py` removes the `"jailbreak"` pattern, this test still
passes because it never imports from `guardrails.py`. The README claims the
hook and the server share a 13-pattern list; this test cannot detect when
that synchronisation breaks. The PRD even calls out keeping them in sync — but
nothing enforces it.

**Fix:** import the patterns from `tools/guardrails.py` directly (or read them
from a shared `injection_patterns.txt` file used by both server and hook). Add
a test that opens `.claude/hooks/pre-tool-use.mjs` and asserts the regex
strings match the Python source.

### 3. `test_flow_idea_capture_roundtrip` explicitly opts out of asserting
**File:** `e2e/test_critical_flows.py:50`
```python
_ = rows  # do not assert length; path may differ in test env
```
The single most important flow in Metis — capture an idea, see it land in the
database — is tested by an e2e test that fetches the rows then discards them.
The test passes whether the row was inserted or silently lost. It only checks
that the HTTP response didn't crash.

**Fix:** fix the DB path resolution in the fixture so the row can actually be
asserted. If the path resolution is genuinely broken, mark the test
`@pytest.mark.xfail(reason="DB path mismatch — see issue #N")` so the gap is
visible.

### 4. `test_no_tab_crashes_on_empty_db` doesn't check that tabs are *useful*
**File:** `personas/test_all_personas.py:751`
The test confirms each tab returns non-500. It does not check that the
"empty state" partial is actually rendered, that the morning brief container
appears, or that the user sees anything other than a blank panel. A tab can
return 200 with `<div></div>` and pass.

**Fix:** assert that key visible strings ("Morning Brief", "No tasks yet",
"Capture your first idea") are present in the response body for the empty
state.

### 5. `test_capture_modal_has_prefix_routing` passes on the letter "i"
**File:** `audit/test_ux_audit.py:204`
```python
assert "i:" in modal or "prefix" in modal.lower() or "idea" in modal.lower()
```
The word "idea" appears in any English description of a capture modal. This
assertion passes if the modal is empty placeholder text containing the word
"idea". It does not verify the chip is wired (`onclick="setPrefixMode('i:')"`),
that the parser handles `i:`, or that submitting `i: text` actually creates
an idea row.

**Fix:** parse the HTML and assert all five chips (`i: n: t: q: j:`) are
present and their `onclick` handlers call `setPrefixMode`. Cross-check against
`_parse_prefix()` in `capture.py` — the prefixes must be the same set.

### 6. `test_morning_brief_uses_ai` passes on a comment
**File:** `audit/test_ux_audit.py:734`
```python
assert "claude" in text.lower() or "anthropic" in text.lower() or
       "haiku" in text.lower() or "messages" in text.lower()
```
The substring "messages" appears in dozens of unrelated contexts. The word
"claude" in a comment satisfies the assertion. A morning brief that returns
hardcoded lorem ipsum would pass.

**Fix:** assert that the actual API call exists — find a call to
`requests.post("https://api.anthropic.com/v1/messages", ...)` with a
non-stubbed body, and that the model id resolves to a real Anthropic model
name (e.g. starts with `claude-`). Better: mock the endpoint, POST to
`/api/partial/today/morning-brief`, and assert the mocked LLM was called.

### 7. `test_morning_brief_under_600_tokens` skips silently when missing
**File:** `audit/test_ux_audit.py:753`
The test reads `max_tokens=` with a regex. If the file uses a constant
(`MAX_BRIEF_TOKENS`), the regex misses it, the variable is `None`, and the
test exits without assertion. The real `today.py` uses `"max_tokens": 800`
which the regex catches — but the limit is 800, and the assertion says
`<= 800`. Bump the budget to 1500 in the code and the test still passes. The
upper bound should be tighter (~400) given the persona spec says "< 3
paragraphs."

**Fix:** decide a real ceiling and assert against it.

### 8. `test_cross_pollination_triggered_after_capture` passes on the word "similar"
**File:** `audit/test_ux_audit.py:228`
```python
assert "cross_pollinate" in text or "brainstorm" in text or \
       "connections" in text or "similar" in text
```
"similar" appears in the docstring of any HTTP route. The test does not
actually invoke capture and observe a follow-up call.

**Fix:** monkey-patch `_cross_pollinate_core`, POST to `/api/capture` with an
idea prefix, assert the patch was called exactly once. Also assert it is NOT
called for a task prefix (the code path differentiates and the test should
too).

### 9. Persona tests assert `status_code not in (500,)` — anything else is fine
**File:** `personas/test_all_personas.py` (multiple lines, e.g. 109, 362, 669)
```python
assert r.status_code not in (500,), "Capture modal should not crash"
```
404, 422, 400 all pass. The test will go green on a Metis where `/api/capture`
was renamed to `/capture` and never wired in `main.py`. The persona
"workflow" is effectively never executed.

**Fix:** assert `r.status_code in (200, 201, 204, 302)` for routes that must
work. Reserve the looser check for cases where the failure mode is genuinely
non-binary.

### 10. `test_red_lines_enforced` checks for the word "BLOCK"
**File:** `personas/test_all_personas.py:452`
The clinical researcher persona (James Obi) is the most important user from a
liability standpoint — patient data must never leave the machine. The test
that "verifies" red-lines enforcement asserts that `red-lines.md` contains
the strings `"patient"`, `"individual"`, `"BLOCK"`, `"never"`. It does not
exercise the actual blocking pipeline.

**Fix:** write a runtime test that constructs a payload with a fake patient
ID (`patient_id: 12345`), passes it through `check_data_safety()`, and
asserts `classification == "SENSITIVE"` and the call is refused at the hook
boundary. The README's most important promise deserves a runtime check.

### 11. `test_metis_tab_agent_run_history_wired` is a tautology
**File:** `audit/test_ux_audit.py:597`
```python
assert "agent" in text.lower() and ("hx-get" in text or "hx-post" in text)
```
The word "agent" appears in every metis tab template since the tab is *about*
agents. The OR condition on `hx-get`/`hx-post` matches any HTMX element
anywhere on the page, including unrelated buttons. The test will pass even
if the agent-run history is rendered as a static placeholder.

**Fix:** assert that an element with `hx-get="/api/partial/metis/agent-runs"`
(or whatever the canonical endpoint is) exists in the template, and that the
endpoint returns rows when the DB has them.

### 12. The wizard test that the wizard ran is just `not file.exists()`
**File:** `audit/test_config_wizard.py:206`
```python
def test_first_run_marker_not_currently_present(self):
    marker = CONFIG_DIR / ".first-run"
    assert not marker.exists()
```
This test passes on any fresh install where the wizard was never run *and the
marker was never created*. It confirms the absence of a file, not the
presence of completed configuration. A genuinely fresh user where the wizard
silently failed would pass this test.

**Fix:** assert *both* that `.first-run` is absent **and** that
`user-config.yaml` contains a non-empty `user.name`. The two together prove a
wizard ran to completion.

---

## Missing test perspectives

### Nothing tests the "I just installed Metis on a friend's laptop" experience

The persona tests assume `agents/`, `system/`, and a populated SQLite
schema. There is no test that:

- Clones the repo with no `.env`, no `metis.sqlite`, no `user-config.yaml`,
  and confirms that `setup-mcp.sh` produces a working install.
- Starts the dashboard and confirms `/today` renders something more than a
  loading spinner before the user has done anything.
- Verifies that `bootstrap_python.ps1` actually finds or installs Python on a
  Windows VM (it asserts file existence, not script behaviour).

The README's #1 promise is "double-click install.bat and it works." Nothing
in the suite touches that path.

### Nothing tests cost or token consumption

The README sells "efficient token use" as a feature. The morning brief calls
Claude every day. There is no test asserting:

- The brief uses `prompt-caching` headers (the code does — the test should
  pin this).
- The brief is cached in `daily_insights` and a second hit on the same day
  does NOT re-call Anthropic.
- The handoff brief generator stays under its token budget.

Set up a mock for `https://api.anthropic.com/v1/messages` and count the
number of times it is called per page load. If it's more than 0 after the
cache is warm, fail the test.

### Nothing tests the cross-pollination *output* — only that the code runs

`_cross_pollinate_core("HAT surveillance in conflict zones")` should return
the seeded HAT paper from the persona fixture. No test seeds two ideas, two
papers, and one meeting, then asserts the right matches come back. The
feature is the centrepiece of the product per the README. It is not exercised.

### Nothing tests degraded modes

What happens when:
- The Anthropic API is down? (Tested? No.)
- The SQLite file is locked because another process has it open? (No.)
- The user's `user-config.yaml` is malformed YAML? (Wizard test asserts the
  loader creates an empty config; no test asserts the dashboard recovers.)
- `vec_episodic` is missing or sqlite-vec is not built? (No.)
- A new user types `aaaaaaa` as their idea and submits 1000 times? (Capture
  rate-limiting is not tested.)

### Nothing tests session boundaries

The CLAUDE.md promises Metis "remembers across sessions" via PLANNING.md and
session events. There is no test that:
- Creates a session, writes a reflexion, closes it, opens a new one, and
  verifies the previous reflexion is surfaced.
- Confirms the handoff brief generator includes a non-empty "where you left
  off" section after a real session.

### Nothing tests the README itself

A README is the single most important onboarding artefact. No test asserts:
- Every command in the Quick Start section is real and points to an actual
  file.
- The architecture diagram references files that exist.
- The agent table lists agents that have `skill.md` files (the persona test
  validates the subset listed in CLAUDE.md, not in the README — they drift).
- No `{your-github-username}` placeholders remain in tracked Markdown.

---

## Real-world scenarios not covered

| Scenario | Coverage |
|---|---|
| Fresh install, never opened Claude Code before | None |
| Install while VPN is on and proxy blocks GitHub | None |
| User clones the repo on a Mac with Python installed via pyenv | None |
| User runs Metis from a path containing a space ("OneDrive - ITG") | None — even though this is the maintainer's own path |
| User has Zotero installed but never configured the API key | None |
| User captures 5000 ideas — does the cross-pollination still complete in <1s? | None |
| User uploads a 50MB PDF to inbox/ | None |
| The morning brief job runs at 7am with no API key in `.env` | None |
| A second user is invited to the same Metis instance | None (single-user by design — but no test confirms multi-user fails *gracefully*) |
| User reinstalls Metis over an existing install | None — the wizard test checks merge logic on `_merge` keyword presence, not on real disk |
| A skill.md is hand-edited to reference an MCP tool that doesn't exist | None — agent prompts should be validated against the registered tool set |
| `metis.sqlite` is corrupted (truncated mid-write) | None |
| User's anti-virus quarantines `.exe` | None — Inno Setup script existence is checked, not behaviour |

---

## Security tests that are insufficient

### Injection probe duplication (see §2 above)

The 13-pattern list lives in two places: Python (`tools/guardrails.py`) and
the JS hook (`.claude/hooks/pre-tool-use.mjs`). The test compares against a
third copy in the test file. None of these three sources is the canonical
source. A typo in one drifts the others.

### `test_pii_detection_in_hook` is content-grep
```python
assert "pii" in content.lower() or "patient" in content.lower() or
       "personal" in content.lower()
```
The word "patient" can appear in a comment. The test passes if the hook file
has the docstring "this hook intentionally does NOT check for patient data."

### The Data Guardian's *blocking* behaviour is never tested
The persona test for James Obi (the clinical researcher) checks:
1. The skill.md file exists.
2. `red-lines.md` contains "BLOCK".
3. `anonymization.py` exists.

It does not test:
- That posting a CSV with `patient_id` header to any Metis endpoint is
  refused.
- That an MCP tool call carrying patient PII triggers the hook.
- That a tool output containing a 9-digit patient ID is scrubbed before
  reaching the LLM.

The README promises "SENSITIVE → BLOCKED — never reaches the API." This is
the strongest marketing claim. It is not tested as an outcome.

### No test for prompt injection via RSS feed content
The News Radar fetches RSS feeds. The injection probe is supposed to flag
hostile content. There is no test that:
- Constructs a malicious RSS feed XML.
- Runs the news scanner against it.
- Asserts the agent did not execute the injected instruction.

### Session-level injection counter is untested
The dashboard claims to maintain `/tmp/metis-injection-session.json` and
escalate after 3+ hits. There is no test asserting:
- The counter increments on each detection.
- The 4th call is refused (or whatever the policy is).
- The counter resets on session boundary.

---

## Specific test improvements recommended

Listed in rough priority order:

1. **Stop accepting 500 as success.** Replace
   `assert r.status_code in (200, 404, 500)` with `assert r.status_code == 200`
   anywhere the route is documented to work. If it sometimes 404s, that's a
   bug, not a test variant.

2. **Import what you test.** `test_guardrails.py` must import
   `_INJECTION_PATTERNS` from `tools/guardrails.py`, not redefine it. The
   hook must read from the same source.

3. **Test outcomes, not strings.** Anywhere a test says
   `assert "X" in text.lower()`, ask: would this still pass if the feature
   were stubbed? If yes, replace with a runtime invocation that asserts an
   observable side-effect (a DB row, a file on disk, an outbound HTTP call).

4. **Add a "fresh-clone smoke" test.** A test that uses a `tmp_path` repo
   copy with no SQLite, no `.env`, runs `setup-mcp.sh`, starts the dashboard,
   GETs `/today`, and asserts the response contains "Welcome" or "Set up
   Metis" (the empty-shell affordance).

5. **Mock the Anthropic endpoint.** A `pytest` fixture that intercepts
   `https://api.anthropic.com/*` and records calls. Then assert: the brief
   route hits it exactly once per day; the cross-pollination route hits it
   never (it's local); the handoff brief is under N tokens.

6. **Pin the README's promises.** A `test_readme_promises.py` that parses
   the README, extracts every feature claim (regex on bold headers in the
   Features section), and matches each to a runtime test. If a feature has
   no test, the README test fails.

7. **End-to-end the wizard.** Run the wizard via the `/setup` POST endpoints
   with persona-like inputs, then assert `user-config.yaml` contains the
   expected name, `user-preferences.json` contains the expected theme, and
   the `.first-run` marker is gone.

8. **Patient-data red-team test.** Construct 10 hostile payloads (patient
   IDs in CSV, GPS coordinates in JSON, Belgian national IDs in plain text,
   PII in column headers) and assert each is classified `SENSITIVE` and
   blocked at the tool boundary. This is the most important guarantee
   Metis makes.

9. **Schema parity test.** The persona fixture's `_SCHEMA` block differs
   subtly from the production schema in `db.py`. Add a test that compares
   the columns of every CREATE TABLE — drift will produce hard-to-debug
   "missing column" errors at runtime.

10. **Real keyboard shortcut test.** Replace `"ctrlKey" in text` with a
    Playwright/Selenium-style assertion that pressing Ctrl+K on a loaded
    page actually opens the capture modal. (Or at minimum: parse the JS,
    locate the keydown handler, assert it calls `openCapture()` and that
    `openCapture()` is defined.)

11. **Test the empty-state UX, not the keyword.** Render each tab against
    an empty DB and assert the response contains a known empty-state
    message ("No ideas yet — press Ctrl+K to capture one"). If it just
    shows `<div></div>`, fail.

12. **Add a "would this README convince me?" test.** A first-impression
    test that asserts the first 500 characters of the README contain (a) a
    plain-English sentence under 30 words, (b) at least one concrete verb
    the user can do, (c) the platform requirements, (d) no marketing
    superlatives ("powerful", "seamlessly", "revolutionary"). Bad readmes
    fail this in seconds; good ones don't notice.

---

## Closing note

The suite is unusually comprehensive in *scope* — wizard, personas, ux,
e2e — and unusually shallow in *depth*. Most assertions are "the file
mentions this word" rather than "the system does this thing." That style
catches structural regressions (file deletions, route un-registrations) but
not behavioural ones (the route still 200s but returns the wrong content,
the brief still loads but is now generated by a different model, the
Guardian still exists but stops blocking).

For a research tool whose entire pitch is *safety* (no PII out) and
*usefulness* (the right context surfaces at the right time), behavioural
tests are not optional. The good news is the structural tests give a stable
scaffold to add real assertions to — the named partials, routes, and
tools are reliable enough that a behaviour suite can be bolted on without
fighting the layout.

If only ten tests can be added before release, do these in this order:

1. Real cross-pollination output check (seed three sources, query, assert
   matches).
2. Real PII blocking (10 hostile payloads → all blocked at the tool
   boundary).
3. Real morning brief mock (Anthropic mocked → assert one call per day,
   model id correct, cache works).
4. Fresh-clone install (`setup-mcp.sh` in a tmp dir → dashboard starts).
5. Wizard end-to-end (POST `/setup` → config files contain inputs).
6. Drop accepting 500 on every existing route test.
7. Guardrails single-source-of-truth (import patterns, sync with hook).
8. Capture roundtrip with DB assertion (fix the path; assert the row).
9. README promises ↔ test mapping.
10. Empty-shell tab content (assert the actual empty-state strings).

Everything else is polish.
