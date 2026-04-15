# Findings & Architectural Decisions

## File-Based Memory vs Database Memory

**Decision (2026-04-03):** Stick with file-based JSON for now. Revisit at the inflection points listed below.

### Why File-Based Works Today

- **Single-user / single-agent** — no concurrent writes from different processes
- **Low data volume** — dozens to low hundreds of campaigns; full-file reads stay fast
- **Git-versioned data** — can track playbook evolution in commits
- **Simplicity** — no server to run, no migrations, no ORM
- **Append-only pattern** — new campaigns, new metrics entries; rarely updating existing records

### When a Database Becomes Worth It

| Trigger | Why |
|---------|-----|
| **Concurrent access** | Multiple agent instances or dashboard + agent writing simultaneously. `filelock` serializes but doesn't scale. A DB handles this natively. |
| **Query complexity** | "Show me all email campaigns where open rate > 25% in the last 30 days sorted by confidence" requires loading every JSON file and filtering in Python. SQL does this in one query. |
| **Data volume (~500+ campaigns)** | Reading/parsing full JSON files on every request gets slow. Database indexes solve this. |
| **Cross-entity joins** | "Which playbook learnings came from campaigns that targeted audience X?" is painful with flat files, trivial with relational data. |
| **Dashboard performance under load** | API routes currently read JSON files synchronously. Under multiple users or frequent polling, file I/O becomes a bottleneck. |
| **Scheduled agent runs** | Cron-based metric collection or multiple team members using the dashboard simultaneously. |

### Migration Path

1. **SQLite first** — single-file, zero-config, same deployment simplicity as JSON but with real queries and concurrency. Drop-in replacement.
2. **Postgres only if needed** — multi-user, remote access, full-text search on playbook learnings, or hosted deployment (e.g., Supabase/Neon).

### What Would Change

- API routes switch from `fs.readFileSync` → SQL queries (faster, paginated)
- Tool functions swap JSON read/write for DB calls (same interface, different backend)
- Context factory queries DB instead of scanning dirs
- Playbook search becomes full-text instead of linear scan
- Migration script converts existing JSON data → tables

### Schema Sketch (for when the time comes)

```sql
-- Core tables
campaigns (id, name, channel, status, brief, audience, created_at)
variants (id, campaign_id, channel, content, subject_line, cta, tone, status)
metrics (id, variant_id, metric_type, value, date, notes)

-- Intelligence
playbook_learnings (id, category, learning, evidence, confidence, times_confirmed, times_contradicted, tags, created_at, updated_at)
ab_tests (id, campaign_id, state, hypothesis, variant_a_id, variant_b_id, metric, created_at)
ab_test_checks (id, test_id, p_value, effect_size, verdict, checked_at)

-- Cross-channel
transfers (id, learning_id, source_channel, target_channel, hypothesis, status, validation_campaign_id)

-- Analytics
reports (id, report_type, parameters, content, generated_at)
```
