---
name: demo-builder
description: Personal — set up / tear down the full demo environment for filming GIFs. Spins up the demo dashboard AND links Codex Desktop to the SAME demo data (Dr. Amélie Fontaine), so brainstorm/OODA hand-offs answer from coherent fake data. Triggers — demo builder, film demo, demo gif, record demo, set up demo, build the demo, demo environment, link desktop to demo, teardown demo, revert demo.
---

# Demo Builder (personal)

**This skill is personal/local — keep it out of the public Metis_PH repo.** It builds a self-contained, fully-coherent demo so the dashboard *and* Codex Desktop both answer from the same invented researcher (Dr. Amélie Fontaine, health economist · global health policy). For recording the README / Reddit demo GIFs.

It exists because Metis reads from both the **database** and the **filesystem** (project folders, `user-config.yaml`, library). A demo that only swaps the DB leaks the real workspace. So this builds a parallel **demo root** in `~/.local/share/metis-demo-root/` (Amélie identity + project folders + the demo DB; agents/.Codex symlinked from real; library deliberately empty) and points both surfaces at it.

## Moving parts (all already built)
- `system/install/seed_mockup_demo.py` — seeds the demo data (Amélie: 7 projects, 20 tasks, 4 meetings, ideas+links, notes, journal, contacts, library+literature, in-field news, a daily **and** weekly brief, agent runs, courses, reflexions).
- `system/install/setup_demo_root.py` — builds the isolated demo root from that DB.
- `system/install/demo_setup.sh up|down|status` — the orchestrator. `up` does everything and links Desktop + dashboard to ONE demo DB; `down` reverts.
- `run.sh` override (`# >>> METIS DEMO OVERRIDE <<<`) points Desktop's Metis at the demo root. Backup at `run.sh.bak`.

## What to do when invoked

**Default / `up` / "set up the demo":**
1. Run: `bash system/install/demo_setup.sh up`
2. Then tell the user, clearly:
   - **Dashboard** is live at http://127.0.0.1:8081 (demo data, API-key + scan banners suppressed, brief served from cache — no API calls).
   - **Fully quit + reopen Codex Desktop** (tray → Quit, *not* just close the window; Task Manager → End any `Codex` if needed). It re-reads `run.sh` only on a fresh launch.
   - **Confirm** in Desktop: ask *"Metis, what are my current projects?"* → must list Amélie's (UHC financing brief, NTD cost-effectiveness paper, financing dashboard…). If it still shows real projects, Desktop didn't fully restart — quit harder.
3. Offer the shot-list (below).

**`down` / "revert" / "teardown":**
1. Run: `bash system/install/demo_setup.sh down`
2. Tell the user to **fully restart Codex Desktop** once more to return to their real workspace. Remind them: until they do, Desktop is on demo data — don't do real work in it.

**`status`:** run `bash system/install/demo_setup.sh status` and relay (wired? dashboard up? which root each server uses).

## The filming shot-list (3 clips, every beat is real)
Tool: **ScreenToGif**. ~1280px window, 15 fps, slow deliberate cursor, pause ~1.5s on key moments, keep total <20s, loop. Edit out dead frames; save GIF under ~5 MB for the GitHub README; embed `![Metis demo](docs/demo.gif)`.

- **Clip 1 — Today:** the cross-pollination brief → flip **DAILY · WEEKLY** → click **✦ BRAINSTORM THIS** → Codex Desktop opens pre-filled and answers from Amélie's work.
- **Clip 2 — Reflection:** the **Idea Mindmap** (theme branches + dashed idea-links) → the **creativity dial** (Grounded/Balanced/Bold) → a scoped **Brainstorm** button (This work / A topic / Mindmap / Cluster) → Desktop surfaces a library source + an old idea.
- **Clip 3 — Metis tab:** the saved **reflexions** → **✦ IMPROVE METIS (OODA)** → Codex/Desktop opens primed to run the OODA loop in plan mode.

## Guardrails
- **Never** run `up` against the real DB or real config — the scripts only touch the demo DB and `~/.local/share/metis-demo-root/`; the real `run.sh` is backed up to `run.sh.bak` before any edit.
- Don't restart the dashboard mid-take (it's fine to leave running).
- Always offer `down` + the Desktop restart afterwards so the user doesn't accidentally keep working in demo mode.
- This skill and its scripts are **personal** — do not ship them to Metis_PH.
