---
status: backlog
priority: P2
agent_claimed: null
claimed_at: null
updated: 2026-08-20
---

# Bot Detection Bypass Maintenance

> **Repo:** theknot-scraper
> **Description:** Monitor and adapt to TheKnot's anti-bot countermeasures

---

## Context

TheKnot actively evolves anti-bot measures. Need ongoing maintenance to keep scraper working.

---

## Acceptance Criteria

- [ ] Monthly bypass health check with automated test suite
- [ ] Browser fingerprint diversity (viewport, user-agent, WebGL, canvas)
- [ ] CAPTCHA detection with human-in-the-loop fallback
- [ ] Change detection alert when page structure shifts significantly

---

## Technical Notes

- Playwright stealth patches; browser pool with diverse fingerprints; difflib for HTML structure comparison
