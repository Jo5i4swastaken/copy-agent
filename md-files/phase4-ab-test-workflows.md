# Phase 4: A/B Testing Workflow Specification

**Status:** Active
**Date:** 2026-04-03

---

## 1. Happy Path: Full A/B Test Lifecycle

### Trigger
User requests A/B testing on a campaign with 2+ variants.

### Flow

```
User: "A/B test the subject lines for spring-sale-email"
    │
    ▼
[1] design_ab_test(campaign_id, hypothesis, variable, control, treatment, metric)
    → Creates ab_test.json in campaign dir
    → State: DESIGNED
    │
    ▼
[2] start_ab_test(campaign_id)
    → Creates ab_test_state.json
    → Transitions: DESIGNED → DEPLOYING → COLLECTING
    → Sets next_check_at (channel-dependent: email=24h, sms=12h, ad=48h, seo=7d)
    │
    ▼
[3] check_ab_test(campaign_id) — called when next_check_at is reached
    → Fetches latest metrics from platform adapters
    → Runs statistical test (z-test for rates, t-test for continuous)
    → Checks early stopping (O'Brien-Fleming)
    → Returns verdict
    │
    ├─ insufficient_data → Stay in COLLECTING, set new next_check_at
    ├─ trending_{variant} → Stay in COLLECTING, log trend, set new next_check_at
    ├─ winner_{variant} → Transition to DECIDED
    └─ inconclusive (max duration) → Transition to INCONCLUSIVE
    │
    ▼
[4] conclude_ab_test(campaign_id)
    → Saves learning to playbook via save_learning
    → Marks winner in variants.json (status: "winner"/"loser")
    → Triggers evaluate_cross_channel_transfer if confidence >= 0.5
    → Transitions: DECIDED → COMPLETED
    │
    ▼
[5] Test archived. Learning available for future copy generation.
```

### Side Effects (files written per step)

| Step | Files Written |
|------|--------------|
| design_ab_test | `data/campaigns/{id}/ab_test.json` |
| start_ab_test | `data/campaigns/{id}/ab_test_state.json` |
| check_ab_test | Updates `ab_test_state.json` (metrics, checks_performed, state) |
| conclude_ab_test | Updates `ab_test_state.json`, `variants.json`, `data/playbook.json` |

---

## 2. Branch Conditions

### At check_ab_test Decision Point

| Condition | Criteria | Action |
|-----------|----------|--------|
| **insufficient_data** | sample_size < minimum_sample_size | Stay COLLECTING, next_check_at += channel delay |
| **trending_{variant}** | 0.05 < p_value < 0.10 | Stay COLLECTING, log trend, next_check_at += channel delay |
| **winner_{variant}** | p_value <= 0.05 (or early stopping triggered) | Transition to DECIDED |
| **inconclusive** | days_elapsed >= maximum_duration_days AND p_value > 0.05 | Transition to INCONCLUSIVE |

### At INCONCLUSIVE Decision Point

| Option | Action |
|--------|--------|
| Extend test | Increase maximum_duration_days, transition back to COLLECTING |
| Accept and stop | Transition to COMPLETED with learning "no significant difference" |
| Redesign | Archive test, create new test with different variable |

---

## 3. Failure Modes

### 3.1 Platform API Failure
- **Trigger:** fetch_campaign_metrics returns an error (SendGrid/Twilio/Google Ads API down)
- **Behavior:** check_ab_test logs the error in checks_performed with verdict "api_error"
- **State:** Stays in COLLECTING, next_check_at set to retry_delay (4 hours)
- **Recovery:** Next check will retry the API call

### 3.2 Missing Metrics
- **Trigger:** No metrics data returned for one or both variants
- **Behavior:** Verdict "insufficient_data" with note about missing variant data
- **State:** Stays in COLLECTING
- **Recovery:** User prompted to check platform integration status

### 3.3 Stale Test
- **Trigger:** Test has been in COLLECTING for > 2x maximum_duration_days
- **Behavior:** check_ab_test flags as "stale_test" in verdict
- **State:** Stays in COLLECTING but adds stale warning
- **Recovery:** User should either conclude with available data or archive

### 3.4 Concurrent Test Conflict
- **Trigger:** start_ab_test called when another test is active for the same campaign
- **Behavior:** Returns error: "An A/B test is already active"
- **State:** No change
- **Recovery:** Conclude or archive the existing test first

### 3.5 File Lock Contention
- **Trigger:** Two processes try to write ab_test_state.json simultaneously
- **Behavior:** filelock ensures serialized access; second process waits
- **State:** No corruption
- **Recovery:** Automatic — filelock handles it

---

## 4. Recovery Paths

| Failure State | Recovery Action |
|---------------|----------------|
| API error during check | Automatic retry on next check cycle |
| Missing metrics | Check platform integration with check_integrations, verify variant deployment |
| Stale test (> 2x duration) | conclude_ab_test with available data, or archive and redesign |
| Corrupt state file | Delete ab_test_state.json, re-run start_ab_test from ab_test.json plan |
| Test stuck in DEPLOYING | Manual transition: edit ab_test_state.json state to COLLECTING |

---

## 5. Dashboard Trigger Flow

```
Dashboard Page Load (/ab-tests)
    │
    ▼
useABTests hook
    → GET /api/ab-tests/active
    → Returns list of active tests with next_check_at
    │
    ▼
useABTestMonitor hook (runs on interval)
    → For each test where now > next_check_at:
    │   → Sends WebSocket message to conductor:
    │     "Check A/B test {test_id} for campaign {campaign_id}"
    │   → Conductor calls check_ab_test(campaign_id, test_id)
    │   → Result displayed in dashboard
    │
    ▼
Dashboard re-renders with updated test states
```

**Polling interval:** 60 seconds while dashboard is open.
**Trigger condition:** `Date.now() > new Date(test.next_check_at).getTime()`

---

## 6. Early Stopping Flow (O'Brien-Fleming)

```
check_ab_test runs statistical test
    │
    ▼
Sample size >= early_stopping.check_after_samples?
    │
    ├─ No → Return insufficient_data
    │
    ▼ Yes
Calculate p_value from z-test or t-test
    │
    ▼
Calculate current_fraction = current_sample / minimum_sample_size
    │
    ▼
check_early_stopping(p_value, current_fraction, num_looks)
    │
    ▼
O'Brien-Fleming boundary = 2 * (1 - Φ(z_{0.025} / √fraction))
    │
    ├─ At 25% of sample: boundary ≈ 0.00005 (very strict)
    ├─ At 50% of sample: boundary ≈ 0.0054
    ├─ At 75% of sample: boundary ≈ 0.0184
    └─ At 100% of sample: boundary ≈ 0.0431 (close to 0.05)
    │
    ▼
p_value <= boundary?
    │
    ├─ Yes → Early stop: declare winner, transition to DECIDED
    └─ No → Continue collecting, standard check at next interval
```

**Key property:** O'Brien-Fleming boundaries are very conservative early on, preventing false positives from small samples. They relax as more data arrives.

---

## 7. Post-Test Flow

### 7.1 Learning Extraction

```
conclude_ab_test(campaign_id)
    │
    ▼
Read ab_test_state.json for winner, effect size, p_value
    │
    ▼
Call save_learning with:
    - learning: "In {channel}, {variable_tested}: {winner description} outperformed
                 {loser description} by {effect_size}% ({metric})"
    - confidence: "medium" (single confirmed test)
    - category: campaign channel
    - evidence: {campaign_id, test_id, p_value, effect_size, sample_sizes}
    │
    ▼
Mark winning variant status="winner" in variants.json
Mark losing variant status="loser" in variants.json
```

### 7.2 Cross-Channel Transfer Trigger

```
Learning saved with confidence >= 0.5?
    │
    ├─ No → Stop
    │
    ▼ Yes
evaluate_cross_channel_transfer(learning_id)
    │
    ▼
Check transferability matrix for learning category
    │
    ▼
For each eligible target channel:
    │
    ▼
Create transfer hypothesis in data/orchestration/transfers/
    Status: "proposed"
    │
    ▼
Notify conductor: "New cross-channel transfer proposed: {hypothesis}"
```

### 7.3 Archival

```
After conclude_ab_test completes:
    │
    ▼
ab_test_state.json state = COMPLETED
    │
    ▼
State remains in campaign directory for historical reference
    │
    ▼
list_active_tests no longer returns this test
    │
    ▼
Dashboard moves test to "Completed" tab
```

---

## Appendix: JSON Schemas

### ab_test_state.json

```json
{
  "test_id": "string",
  "campaign_id": "string",
  "state": "DESIGNED|DEPLOYING|COLLECTING|WAITING|ANALYZING|DECIDED|INCONCLUSIVE|COMPLETED|ARCHIVED",
  "state_history": [{"state": "string", "entered_at": "ISO8601", "exited_at": "ISO8601|null"}],
  "hypothesis": "string",
  "variable_tested": "string",
  "variants": {
    "control": {"variant_id": "string", "platform_id": "string|null"},
    "treatment": {"variant_id": "string", "platform_id": "string|null"}
  },
  "decision_criteria": {
    "primary_metric": "string",
    "minimum_sample_size": "integer",
    "minimum_confidence_level": "float (0-1)",
    "minimum_detectable_effect": "float",
    "maximum_duration_days": "integer",
    "early_stopping": {"enabled": "boolean", "check_after_samples": "integer", "significance_threshold": "float"}
  },
  "current_metrics": {"variant_id": {"metric": "float", "sample_size": "integer"}},
  "checks_performed": [{"checked_at": "ISO8601", "verdict": "string", "p_value": "float|null"}],
  "result": {"winner": "string", "effect_size": "float", "p_value": "float", "confidence_interval": [0, 0]},
  "winner": "string|null",
  "learning_saved": "boolean",
  "next_check_at": "ISO8601"
}
```
