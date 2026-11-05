# Frontier backlog — prioritized for parallel Meta agents

Anna Medelvärde plans/analyzes/reviews; Meta implementation instances execute
in isolated worktrees; humans approve verification + deployment gates.
Claim a lane by record IDs; never edit another lane's records in parallel.

P0 (do first, blocks verification work)
1. Lane A (candidates cand-leju-robot, cand-kepler, cand-tesla-optimus,
   cand-sanctuary-ai, cand-fourier, cand-boston-dynamics): official-site
   discovery only; create src-* records (manual_browser_review, robots/ToS
   fields) or record not-found. No status promotion without reviewer.
2. Lane B (cand-x-humanoid, cand-unitree, cand-engineai, cand-robot-era,
   cand-pndbotics, cand-xpeng, cand-ubtech): same as Lane A.
3. Lane C (cand-deep-robotics, cand-physicalintelligence, cand-limx-dynamics,
   cand-tencent, cand-pudu-robotics, cand-booster-robotics, cand-romela):
   same; flag labs/brands/products vs legal entities as claims, not facts.
4. Lane D (cand-jaka-robotics, cand-agibot, cand-magiclab, cand-apptronik,
   cand-agility): same; duplicate/alias analysis (e.g. product vs company).

P1
5. Dedup & scope pass across all 25: duplicate/out_of_scope proposals with
   claim-* evidence for human decision. Candidate != verified company.
6. Compliance Lane 1: EU AI Act + Machinery Regulation primary-source cmp-*
   records (researching only; not legal advice; no conclusions).
7. Compliance Lane 2: GDPR + dataset licence/privacy cmp-* records; define
   the consent evidence bar for any future STOP dataset.
8. Compliance Lane 3: Cyber Resilience Act, product safety/liability,
   standards map, export controls, ToS/robots.txt cmp-* records.

P2
9. For verified-only entities: official docs/API/SDK source discovery;
   api-* records with endpoints ONLY from official docs (source_ids req.).
10. Dataset inventory for voice/gesture/STOP-relevant datasets: ds-* with
    licence + privacy evidenced or explicitly unknown; cards drafted.
11. Offline STOP evaluation harness design (replay, coverage cells, CI):
    code + tests, no new data collection, no deployment change.

P3
12. Consented local data-collection protocol (ethics/consent forms, deletion)
    — human + legal review before any recording.
13. Universe-methodology study: what a defensible humanoid-company census
    would require. Until then universe_size_claim stays null.
14. Nightly registry report: counts by status, contested claims, validator
    output — factual summary, no inflated totals.

Blocked / forbidden until explicit human approval: any scraping automation,
dataset downloads, model training runs, recognizer deployment changes,
physical robot work, legal conclusions.
