---
status: backlog
priority: P2
agent_claimed: null
claimed_at: null
updated: 2026-08-20
---

# Search and Filter API

> **Repo:** theknot-scraper
> **Description:** Query scraped vendors by category, rating, price range, and availability

---

## Context

Make the scraped vendor data searchable with multi-dimensional filtering.

---

## Acceptance Criteria

- [ ] Vendor search by category, location, and name with full-text search
- [ ] Filter by rating range, price tier, and availability status
- [ ] Sort by relevance, rating, review count, or price
- [ ] Pagination with total count and result set metadata

---

## Technical Notes

- FastAPI + SQLAlchemy for query layer; FTS5 for full-text search; composite indexes for filter columns
