# Phase 4 Architecture: Multi-Agent Orchestration, Automated A/B Testing, Cross-Channel Learning, and Advanced Analytics

**Status:** Proposed
**Author:** Software Architect Agent
**Date:** 2026-04-02
**Target codebase:** `/Users/josias/Desktop/CODE/Copy Agent/omniagents-skill-Jo5i4swastaken/`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Constraints](#2-architectural-constraints)
3. [Multi-Agent Topology](#3-multi-agent-topology)
4. [Agent Coordination Protocol](#4-agent-coordination-protocol)
5. [Automated A/B Testing Loop](#5-automated-ab-testing-loop)
6. [Cross-Channel Learning Transfer](#6-cross-channel-learning-transfer)
7. [Advanced Analytics and Reporting](#7-advanced-analytics-and-reporting)
8. [Data Model Changes](#8-data-model-changes)
9. [File Manifest](#9-file-manifest)
10. [Dashboard Changes](#10-dashboard-changes)
11. [Migration and Rollout Strategy](#11-migration-and-rollout-strategy)
12. [Trade-Off Analysis](#12-trade-off-analysis)
13. [ADRs](#13-adrs)

---

## 1. Executive Summary

Phase 4 transforms the Copy Agent from a single conversational agent into a coordinated system of specialized agents that autonomously generate copy, run A/B tests, transfer learnings across channels, and produce analytics reports. The design operates within the constraints of the OmniAgents framework (YAML config, `@function_tool` decorators, file-based state) by using a **conductor pattern** -- a single orchestrator agent that delegates work to channel specialists through a shared file-based message bus.

The key architectural decision is to avoid replacing the existing single-agent architecture. Instead, Phase 4 wraps it: the current agent becomes the "conductor," and channel specialists are implemented as tool-invocable sub-agents that the conductor dispatches work to. This preserves backward compatibility -- existing users and the dashboard continue to interact with one `agent.yml` entry point.

---

## 2. Architectural Constraints

These constraints are non-negotiable. The design must work within them.

| Constraint | Source | Implication |
|---|---|---|
| Single `agent.yml` entry point per agent | OmniAgents framework | Cannot run multiple independent agents from one config. Specialists must be invoked as tools or sub-processes. |
| `@function_tool` decorator for tools | OmniAgents framework | All agent capabilities must be exposed as Python functions with this decorator. |
| File-based state (`data/` directory) | Phases 1-3 design | No database. All coordination, state machines, and message passing must use JSON files with filelock. |
| `context_factory` for prompt injection | OmniAgents framework | Dynamic context comes from `context.py`. Cannot inject state mid-conversation except through tool returns. |
| WebSocket JSON-RPC protocol | Dashboard integration | The dashboard communicates via `start_run`, `tool_called`, `tool_result`, `message_output` events. New agents must not break this protocol. |
| gpt-5.2 via custom endpoint | Model config | All agents share the same model endpoint. Temperature and max_tokens can vary per YAML config if we use separate configs. |
| `use_safe_agent` with safe tool patterns | Security model | Read-only tools are auto-approved. Write tools require user approval (unless dashboard is configured to auto-approve). |

---

## 3. Multi-Agent Topology

### 3.1 Architecture Pattern: Conductor with Tool-Based Specialists

```
                          +-------------------+
                          |   User / Dashboard |
                          +--------+----------+
                                   |
                          WebSocket JSON-RPC
                                   |
                          +--------v----------+
                          |    Conductor Agent |  <-- agent.yml (existing, extended)
                          |                    |
                          |  Orchestrates all  |
                          |  channel work,     |
                          |  A/B loops, and    |
                          |  cross-channel     |
                          |  transfers         |
                          +----+----+----+----+
                               |    |    |    |
               +---------------+    |    |    +----------------+
               |                    |    |                     |
        +------v------+    +-------v---v-------+    +---------v--------+
        | Email        |    | SMS    | Ad       |    | SEO              |
        | Specialist   |    | Spec.  | Spec.    |    | Specialist       |
        | (tool)       |    | (tool) | (tool)   |    | (tool)           |
        +--------------+    +-------+-+---------+    +------------------+

        Each specialist is a @function_tool that:
        1. Loads its channel skill (SKILL.md)
        2. Reads playbook for channel-specific learnings
        3. Generates copy per its channel constraints
        4. Returns structured output to the conductor
```

### 3.2 Agent Roles

#### Conductor Agent (extended `agent.yml`)

**Role:** Orchestrator. Receives user requests, decomposes them into channel-specific tasks, dispatches to specialists, manages the A/B testing lifecycle, triggers cross-channel learning transfers, and generates analytics reports.

**Changes to existing agent:** The conductor is the current Copy Agent with additional tools and expanded system instructions. It gains the ability to:
- Dispatch channel-specific copy generation to specialist tools
- Manage the automated A/B test state machine
- Trigger cross-channel learning analysis
- Generate and schedule reports

**Why not a separate agent:** OmniAgents' single `agent.yml` entry point means the conductor IS the primary agent. Splitting into a separate orchestrator would require either (a) a meta-framework on top of OmniAgents, or (b) running multiple OmniAgents processes. Both add operational complexity that is not justified at this stage. The conductor-as-extended-primary-agent approach keeps one process, one WebSocket, one dashboard integration.

#### Channel Specialists (tool functions, not separate agents)

Each specialist is implemented as a `@function_tool` in a new `tools/specialists/` directory. The specialist:

1. Accepts a structured brief (channel, objective, constraints, playbook context)
2. Loads the relevant skill file for channel-specific formulas and templates
3. Makes a model call using `omniagents.core.llm` to generate copy (specialist-quality generation within a tool)
4. Returns structured copy variants back to the conductor

**Why tools instead of separate agent.yml configs:**
- The OmniAgents framework dispatches to exactly one agent per WebSocket connection. Running specialists as separate agents would require multiple processes, a message broker, and a custom routing layer.
- Tools can still make LLM calls internally (they are Python functions -- they can use the model API directly).
- The conductor retains full visibility and control over specialist output, which is required for A/B test coordination.

**Trade-off acknowledged:** Specialist tools making their own LLM calls means those calls happen inside a tool execution, which the OmniAgents framework treats as synchronous. If a specialist generation takes 15+ seconds, the WebSocket connection will appear to hang. Mitigation: specialists operate on pre-structured briefs and generate at most 3-5 variants per call, keeping latency manageable.

| Specialist | Tool Name | Channel | Primary Skill |
|---|---|---|---|
| Email Specialist | `specialist_email` | email | `skills/email-copy/SKILL.md` |
| SMS Specialist | `specialist_sms` | sms | `skills/sms-copy/SKILL.md` |
| Ad Specialist | `specialist_ad` | ad | `skills/ad-copy/SKILL.md` |
| SEO Specialist | `specialist_seo` | seo | `skills/seo-copy/SKILL.md` |

#### Analytics Agent (tool function)

A `report_generator` tool that reads campaign data, metrics, and playbook entries to produce formatted performance reports. It runs as a tool rather than a separate agent because it needs no ongoing state -- it reads files and returns a report string.

---

## 4. Agent Coordination Protocol

### 4.1 Message Bus: File-Based Task Queue

Agents coordinate through a shared file-based task queue at `data/orchestration/`. This replaces direct function calls between agents with a durable, inspectable, and resumable task system.

#### Directory Structure

```
data/orchestration/
  tasks/
    task-{uuid}.json           # Individual task files
  completed/
    task-{uuid}.json           # Moved here after completion
  schedules/
    ab-tests.json              # Active A/B test schedules
    reports.json               # Scheduled report runs
```

#### Task Schema

```json
{
  "task_id": "task-550e8400-e29b-41d4-a716-446655440000",
  "type": "generate_variants|check_metrics|declare_winner|transfer_learning|generate_report",
  "status": "pending|in_progress|completed|failed",
  "channel": "email",
  "campaign_id": "spring-sale-2026",
  "created_at": "2026-04-02T10:00:00Z",
  "updated_at": "2026-04-02T10:05:00Z",
  "created_by": "conductor",
  "assigned_to": "specialist_email",
  "priority": 1,
  "payload": { },
  "result": null,
  "error": null,
  "depends_on": []
}
```

### 4.2 Coordination Flow: Multi-Channel Campaign

When the conductor receives a multi-channel brief (e.g., "Create a spring sale campaign across email and SMS"):

```
1. Conductor receives user prompt
2. Conductor calls `plan_multi_channel_campaign` tool
   - Parses the brief into per-channel sub-briefs
   - Creates a campaign directory for each channel
   - Creates orchestration tasks for each specialist
   - Returns a summary to the user
3. Conductor calls `specialist_email` with the email sub-brief
   - Specialist loads email-copy skill
   - Specialist reads playbook for email learnings
   - Specialist generates variants
   - Specialist saves variants via existing `save_copy_variant`
   - Returns structured result to conductor
4. Conductor calls `specialist_sms` with the SMS sub-brief
   - Same pattern as email
5. Conductor consolidates results and presents to user
6. If A/B testing is requested, conductor calls `start_ab_test_loop`
```

### 4.3 Why Not Event-Driven / Pub-Sub

An event-driven architecture with a message broker (Redis, RabbitMQ) would be cleaner for multi-agent coordination. We chose the file-based task queue because:

1. **Constraint alignment:** The project uses file-based state exclusively. Introducing a message broker adds an operational dependency and contradicts the existing architecture.
2. **Inspectability:** JSON task files can be read by the dashboard, debugged by humans, and versioned by git.
3. **Resumability:** If the agent process restarts, pending tasks are still on disk.
4. **Simplicity:** At the current scale (single-user, single-instance), file-based queues are adequate.

**What we give up:** No real-time push notifications between agents. The conductor must poll or be explicitly triggered. This is acceptable because the A/B test loop operates on timescales of hours-to-days, not milliseconds.

---

## 5. Automated A/B Testing Loop

### 5.1 State Machine

The A/B test lifecycle is a state machine persisted as `ab_test_state.json` within each campaign directory. The conductor advances the state machine on each evaluation cycle.

```
                    +-----------+
                    |  DESIGNED |  (existing state from design_ab_test)
                    +-----+-----+
                          |
                    User approves / auto-start
                          |
                    +-----v-----+
                    |  DEPLOYING |  Variants sent to platforms
                    +-----+-----+
                          |
                    Send confirmations received
                          |
                    +-----v-----+
                    | COLLECTING |  Waiting for metrics
                    +-----+-----+
                          |
              +-----------+-----------+
              |                       |
        Enough data             Not enough data
        (sample size met)       (keep waiting)
              |                       |
              |                  +----v----+
              |                  |  WAITING |  (check again later)
              |                  +----+----+
              |                       |
              +-----------+-----------+
                          |
                    +-----v-----+
                    | ANALYZING |  Statistical comparison
                    +-----+-----+
                          |
              +-----------+-----------+
              |                       |
        Clear winner            No clear winner
              |                       |
        +-----v-----+          +------v------+
        | DECIDED    |          | INCONCLUSIVE |
        +-----+-----+          +------+------+
              |                        |
         Save learning            Extend test or
         Apply winner             recommend more data
              |                        |
        +-----v-----+          +------v------+
        | COMPLETED  |          | EXTENDED    |
        +-----+-----+          +------+------+
              |                        |
              +----------+-------------+
                         |
                   +-----v-----+
                   |  ARCHIVED  |
                   +-----------+
```

### 5.2 A/B Test State File: `ab_test_state.json`

Extends the existing `ab_test.json` (from `design_ab_test`) with lifecycle state.

```json
{
  "test_id": "test-spring-email-subject",
  "campaign_id": "spring-sale-2026",
  "state": "COLLECTING",
  "state_history": [
    { "state": "DESIGNED", "entered_at": "2026-04-02T10:00:00Z", "exited_at": "2026-04-02T10:05:00Z" },
    { "state": "DEPLOYING", "entered_at": "2026-04-02T10:05:00Z", "exited_at": "2026-04-02T10:06:00Z" },
    { "state": "COLLECTING", "entered_at": "2026-04-02T10:06:00Z", "exited_at": null }
  ],
  "hypothesis": "Subject lines with numbers will have higher open rates",
  "variable_tested": "subject_line_format",
  "variants": {
    "control": { "variant_id": "v1", "platform_id": "sg_msg_abc123" },
    "treatment": { "variant_id": "v2", "platform_id": "sg_msg_def456" }
  },
  "decision_criteria": {
    "primary_metric": "open_rate",
    "minimum_sample_size": 400,
    "minimum_confidence_level": 0.95,
    "minimum_detectable_effect": 0.20,
    "maximum_duration_days": 14,
    "early_stopping": {
      "enabled": true,
      "check_after_samples": 200,
      "significance_threshold": 0.01
    }
  },
  "current_metrics": {
    "v1": { "open_rate": 0.22, "sample_size": 350 },
    "v2": { "open_rate": 0.27, "sample_size": 348 }
  },
  "checks_performed": [
    {
      "checked_at": "2026-04-03T08:00:00Z",
      "v1_sample": 150,
      "v2_sample": 148,
      "verdict": "insufficient_data"
    },
    {
      "checked_at": "2026-04-04T08:00:00Z",
      "v1_sample": 350,
      "v2_sample": 348,
      "verdict": "trending_treatment",
      "p_value": 0.032
    }
  ],
  "result": null,
  "winner": null,
  "learning_saved": false,
  "next_check_at": "2026-04-05T08:00:00Z"
}
```

### 5.3 A/B Test Tools

These tools implement the state machine transitions. The conductor calls them in sequence.

#### `start_ab_test` (new tool)

Transitions DESIGNED -> DEPLOYING -> COLLECTING.

1. Reads the `ab_test.json` plan (existing from `design_ab_test`)
2. Creates `ab_test_state.json` with DEPLOYING state
3. Uses `send_email` / `send_sms` / platform adapters to deploy variants
4. Records platform IDs in the state file
5. Transitions to COLLECTING
6. Sets `next_check_at` based on channel heuristics

#### `check_ab_test` (new tool)

Called by the conductor on a schedule or on-demand. This is the core evaluation function.

1. Reads `ab_test_state.json` for current state
2. Calls `fetch_campaign_metrics` to pull latest data from platforms
3. Updates `current_metrics` in state file
4. Checks if sample size thresholds are met
5. If sufficient data: runs statistical test (two-proportion z-test for rate metrics, t-test for continuous metrics)
6. Returns one of:
   - `insufficient_data` -- keep waiting, set next check
   - `trending_{variant}` -- interesting signal but not yet significant
   - `winner_{variant}` -- statistically significant result
   - `inconclusive` -- max duration reached, no significant difference
7. On `winner`: transitions to DECIDED, generates a learning recommendation
8. On `inconclusive`: transitions to INCONCLUSIVE, recommends extending or stopping

#### `conclude_ab_test` (new tool)

Transitions DECIDED -> COMPLETED.

1. Calls `save_learning` with the test result
2. Marks the winning variant in the campaign's `variants.json` (sets status to "winner")
3. Optionally triggers cross-channel learning transfer
4. Archives the test state

#### `list_active_tests` (new tool, safe/read-only)

Returns all campaigns with A/B tests in COLLECTING or WAITING state, with time since last check and current metrics summary.

### 5.4 Autonomous Loop Mechanism

The A/B testing loop runs autonomously through the conductor's prompt-triggered evaluation cycle. Here is how it works without requiring a persistent background process:

**Option A: Dashboard-Triggered Polling (Recommended)**

The Next.js dashboard includes a `useABTestMonitor` hook that:
1. On page load, calls a new API route `/api/ab-tests/active` to list active tests
2. For any test past its `next_check_at`, sends a prompt to the conductor: "Check active A/B tests and advance any that have sufficient data."
3. The conductor calls `check_ab_test` for each active test
4. Results are displayed in a new "A/B Tests" dashboard panel

This approach is simple and requires no new infrastructure (no cron, no background workers). The loop advances whenever someone views the dashboard, which is the natural cadence for marketing teams.

**Option B: Scheduled Agent Trigger (Advanced)**

For fully hands-off operation, a cron job or OmniAgents scheduled trigger can send the check prompt at intervals (every 6-12 hours). This is a future enhancement that can be added without any architecture changes -- it just requires a cron entry that sends a WebSocket message.

### 5.5 Statistical Methods

The `check_ab_test` tool uses the following statistical methods, implemented in a new `tools/stats.py` module:

```python
# Two-proportion z-test (for rate metrics like open_rate, click_rate)
def two_proportion_z_test(
    successes_a: int, total_a: int,
    successes_b: int, total_b: int,
) -> tuple[float, float]:
    """Returns (z_score, p_value)."""

# Welch's t-test (for continuous metrics like time_on_page, cost_per_click)
def welch_t_test(
    values_a: list[float],
    values_b: list[float],
) -> tuple[float, float]:
    """Returns (t_statistic, p_value)."""

# Sequential testing / early stopping (O'Brien-Fleming boundaries)
def check_early_stopping(
    p_value: float,
    current_fraction_of_total_sample: float,
    num_looks: int,
) -> bool:
    """Returns True if the result is significant enough to stop early."""
```

---

## 6. Cross-Channel Learning Transfer

### 6.1 Concept

When a learning is confirmed in one channel, the system evaluates whether it could apply to other channels and, if so, generates a transfer hypothesis for testing.

Example: "Question-format subject lines increase email open rate by 23%" could transfer to "Question-format ad headlines may increase ad CTR."

### 6.2 Transfer Eligibility

Not all learnings transfer. The system uses a **transferability matrix** to determine which learning types are candidates:

| Learning Attribute | Transfers To | Transfer Type |
|---|---|---|
| Tone (casual, urgent, professional) | All channels | Direct -- same tone, different format |
| CTA style (action verb, benefit-driven) | All channels | Direct -- same pattern, different context |
| Subject line format (question, number, how-to) | Ad headlines, SMS opening | Adapted -- structural pattern, different length constraints |
| Content length preferences | Same channel only | No transfer -- channel constraints differ too much |
| Personalization effectiveness | Email, SMS | Partial -- only channels with 1:1 delivery |
| Urgency/scarcity tactics | All channels | Direct -- psychological principle is channel-agnostic |
| Send timing | Same channel only | No transfer -- channel consumption patterns differ |

### 6.3 Transfer Mechanism

#### `evaluate_cross_channel_transfer` (new tool)

Triggered by the conductor after a learning reaches `medium` or `high` confidence (confirmed 2+ times).

1. Reads the confirmed learning from `playbook.json`
2. Checks the transferability matrix for eligible target channels
3. For each eligible target channel:
   a. Checks if a similar learning already exists for that channel
   b. If not, creates a **transfer hypothesis** in `data/cross_channel/transfers.json`
4. Returns a summary of proposed transfers for the conductor to act on

#### Transfer Hypothesis Schema

```json
{
  "transfer_id": "xfer-001",
  "source_learning_id": "learn_005",
  "source_channel": "email",
  "source_learning": "Question-format subject lines increase open rate by 23%",
  "source_confidence": 0.9,
  "target_channel": "ad",
  "transfer_hypothesis": "Question-format ad headlines may increase CTR",
  "adapted_tactic": "Use question format in Google Ads headline 1",
  "status": "proposed|testing|confirmed|rejected",
  "test_campaign_id": null,
  "test_result": null,
  "created_at": "2026-04-02T10:00:00Z"
}
```

#### `apply_cross_channel_transfer` (new tool)

Creates a new campaign in the target channel to test the transfer hypothesis:

1. Reads the transfer hypothesis
2. Generates a brief for the target channel incorporating the transferred tactic
3. Dispatches to the appropriate specialist tool
4. Sets up an A/B test with control (channel's current best practice) vs treatment (transferred tactic)
5. Links the A/B test back to the transfer record

#### `review_transfer_results` (new tool, safe/read-only)

After the A/B test completes:

1. Reads the transfer record and linked A/B test result
2. If the transfer hypothesis was confirmed:
   - Creates a new playbook learning for the target channel (confidence: medium)
   - Updates the transfer status to "confirmed"
   - Logs the cross-channel evidence on the source learning
3. If rejected:
   - Updates the transfer status to "rejected"
   - Records why it did not transfer (different audience behavior, format constraints, etc.)

### 6.4 Cross-Channel Data Directory

```
data/cross_channel/
  transfers.json               # Array of transfer hypothesis records
  transfer_log.json            # Audit trail of all transfer evaluations
```

---

## 7. Advanced Analytics and Reporting

### 7.1 Report Types

| Report | Trigger | Contents |
|---|---|---|
| **Campaign Performance Report** | On-demand or after A/B test completion | Variant comparison, winner analysis, recommended next steps |
| **Channel Trend Report** | On-demand or weekly schedule | Performance trends per channel over time, metric moving averages |
| **Cross-Channel Insights Report** | On-demand or after learning transfer | Which learnings transferred, which did not, overall cross-pollination effectiveness |
| **Playbook Health Report** | On-demand or monthly schedule | Learning confidence distribution, stale learnings, decay candidates, coverage gaps per channel |
| **Anomaly Alert** | Triggered by metric check | Sudden drops or spikes in key metrics compared to rolling average |

### 7.2 Analytics Pipeline Architecture

```
Platform Adapters (SendGrid, Twilio, GSC, Google Ads)
         |
         | fetch_campaign_metrics (existing tool)
         |
    +----v----+
    | Metrics  |  data/campaigns/{id}/metrics.json
    | Storage  |  (existing)
    +----+----+
         |
    +----v----+
    | Trend    |  data/analytics/trends.json
    | Engine   |  (new: rolling averages, period comparisons)
    +----+----+
         |
    +----v---------+
    | Anomaly      |  data/analytics/anomalies.json
    | Detection    |  (new: z-score based threshold alerts)
    +----+---------+
         |
    +----v---------+
    | Report       |  data/reports/{report-id}.json
    | Generator    |  (new: structured report output)
    +----+---------+
         |
    +----v---------+
    | Dashboard    |  API routes serve report data
    | Rendering    |  New report pages and components
    +--------------+
```

### 7.3 Analytics Tools

#### `compute_trends` (new tool, safe/read-only)

Scans all campaigns for a given channel, computes:
- Rolling averages (7-day, 30-day) for each metric type
- Period-over-period comparisons (this week vs last week, this month vs last month)
- Best/worst performing campaigns per period
- Persists results to `data/analytics/trends.json`

#### `detect_anomalies` (new tool, safe/read-only)

Runs on metric data to find statistical outliers:
- Computes a rolling mean and standard deviation per metric per channel
- Flags any new data point more than 2 standard deviations from the rolling mean
- Persists anomalies to `data/analytics/anomalies.json`
- Returns a formatted alert for the conductor to surface

#### `generate_report` (new tool)

Accepts a report type and parameters, assembles data from multiple sources, and produces a structured report:
- Reads campaign data, metrics, playbook, trends, anomalies, and cross-channel transfers
- Formats into a structured JSON report with sections
- Persists the report to `data/reports/{report-id}.json`
- Returns a human-readable summary to the conductor

#### `list_reports` (new tool, safe/read-only)

Lists generated reports with metadata (type, date, summary).

#### `get_report` (new tool, safe/read-only)

Retrieves the full content of a previously generated report.

### 7.4 Anomaly Detection Method

The anomaly detector uses a simple z-score approach on a rolling window, which is appropriate for the volume of data this system handles (dozens to hundreds of campaigns, not millions of events):

```python
def detect_anomaly(
    new_value: float,
    historical_values: list[float],
    threshold_sigma: float = 2.0,
) -> dict | None:
    """
    Returns anomaly details if the new value is more than threshold_sigma
    standard deviations from the mean of historical values.
    Returns None if the value is within normal range.
    """
    if len(historical_values) < 5:
        return None  # Not enough history

    mean = sum(historical_values) / len(historical_values)
    variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
    std_dev = variance ** 0.5

    if std_dev == 0:
        return None  # No variance

    z_score = (new_value - mean) / std_dev

    if abs(z_score) > threshold_sigma:
        direction = "spike" if z_score > 0 else "drop"
        return {
            "z_score": z_score,
            "direction": direction,
            "value": new_value,
            "expected_range": (mean - threshold_sigma * std_dev, mean + threshold_sigma * std_dev),
            "historical_mean": mean,
            "historical_std": std_dev,
        }
    return None
```

---

## 8. Data Model Changes

### 8.1 New Data Directories

```
data/
  orchestration/
    tasks/                     # Active task queue
    completed/                 # Completed tasks (archived)
    schedules/
      ab-tests.json            # A/B test check schedule
      reports.json             # Report generation schedule
  cross_channel/
    transfers.json             # Cross-channel transfer hypotheses
    transfer_log.json          # Audit trail
  analytics/
    trends.json                # Computed trend data
    anomalies.json             # Detected anomalies
  reports/
    {report-id}.json           # Generated reports
```

### 8.2 Modified Campaign Directory Structure

```
data/campaigns/{campaign_id}/
  brief.json                   # (existing, unchanged)
  variants.json                # (existing, add "winner" status value)
  metrics.json                 # (existing, unchanged)
  sends.json                   # (existing, unchanged)
  ab_test.json                 # (existing, unchanged -- design plan)
  ab_test_state.json           # (NEW -- lifecycle state machine)
  specialist_log.json          # (NEW -- log of specialist invocations and results)
```

### 8.3 Variant Status Extension

The `variants.json` schema gains a new status value:

```
Existing:  "draft" | "active" | "complete"
Phase 4:   "draft" | "active" | "complete" | "winner" | "loser"
```

This requires updating the `CampaignStatus` type in `dashboard/src/lib/types.ts`.

### 8.4 Playbook Extension

Each playbook entry gains an optional `cross_channel_evidence` field:

```json
{
  "id": "learn_005",
  "category": "email",
  "learning": "Question-format subject lines increase open rate by 23%",
  "cross_channel_evidence": [
    {
      "target_channel": "ad",
      "transfer_id": "xfer-001",
      "result": "confirmed",
      "target_metric_lift": "18% CTR increase",
      "campaign_id": "spring-ads-question-test"
    }
  ]
}
```

---

## 9. File Manifest

### 9.1 New Files to Create

#### Python Tools

| File | Purpose |
|---|---|
| `tools/specialists/__init__.py` | Package init |
| `tools/specialists/base_specialist.py` | Shared specialist logic: skill loading, playbook reading, LLM call wrapper, variant structuring |
| `tools/specialists/email_specialist.py` | `@function_tool specialist_email` -- generates email copy variants with email-copy skill loaded |
| `tools/specialists/sms_specialist.py` | `@function_tool specialist_sms` -- generates SMS copy with sms-copy skill loaded |
| `tools/specialists/ad_specialist.py` | `@function_tool specialist_ad` -- generates ad copy with ad-copy skill loaded |
| `tools/specialists/seo_specialist.py` | `@function_tool specialist_seo` -- generates SEO copy with seo-copy skill loaded |
| `tools/orchestration_tools.py` | `plan_multi_channel_campaign`, `dispatch_to_specialist`, `list_active_tests` tools |
| `tools/ab_test_tools.py` | `start_ab_test`, `check_ab_test`, `conclude_ab_test` tools |
| `tools/cross_channel_tools.py` | `evaluate_cross_channel_transfer`, `apply_cross_channel_transfer`, `review_transfer_results` tools |
| `tools/analytics_tools.py` | `compute_trends`, `detect_anomalies`, `generate_report`, `list_reports`, `get_report` tools |
| `tools/stats.py` | Statistical functions: z-test, t-test, early stopping, anomaly detection (no `@function_tool` -- internal module) |

#### Dashboard (Next.js)

| File | Purpose |
|---|---|
| `dashboard/src/app/ab-tests/page.tsx` | A/B Tests list page -- shows all active and completed tests with state, metrics, winner |
| `dashboard/src/app/ab-tests/[testId]/page.tsx` | A/B Test detail page -- state machine visualization, metric time series, verdict |
| `dashboard/src/app/reports/page.tsx` | Reports list page -- shows generated reports with type, date, summary |
| `dashboard/src/app/reports/[reportId]/page.tsx` | Report detail page -- renders full report content |
| `dashboard/src/app/cross-channel/page.tsx` | Cross-channel transfers page -- shows transfer hypotheses, their status, linked tests |
| `dashboard/src/components/ab-test/TestStateTimeline.tsx` | Visual state machine showing the A/B test progression |
| `dashboard/src/components/ab-test/MetricComparison.tsx` | Side-by-side metric comparison between control and treatment |
| `dashboard/src/components/ab-test/StatisticalResult.tsx` | P-value, confidence interval, and effect size display |
| `dashboard/src/components/analytics/TrendChart.tsx` | Line chart component for metric trends over time |
| `dashboard/src/components/analytics/AnomalyBadge.tsx` | Alert badge for anomalous metrics |
| `dashboard/src/components/cross-channel/TransferCard.tsx` | Card showing a cross-channel transfer hypothesis and its status |
| `dashboard/src/hooks/useABTests.ts` | Hook for fetching active A/B test data from the data directory |
| `dashboard/src/hooks/useABTestMonitor.ts` | Hook that triggers conductor check when tests are past their `next_check_at` |
| `dashboard/src/hooks/useReports.ts` | Hook for fetching report list and individual reports |
| `dashboard/src/hooks/useTrends.ts` | Hook for fetching trend data |
| `dashboard/src/lib/ab-test-reader.ts` | Server-side reader for A/B test state files |
| `dashboard/src/lib/analytics-reader.ts` | Server-side reader for trends, anomalies, and reports |
| `dashboard/src/lib/cross-channel-reader.ts` | Server-side reader for cross-channel transfer data |

### 9.2 Existing Files to Modify

| File | Changes |
|---|---|
| `agent.yml` | Add new tools to the tools list: `specialist_email`, `specialist_sms`, `specialist_ad`, `specialist_seo`, `plan_multi_channel_campaign`, `dispatch_to_specialist`, `start_ab_test`, `check_ab_test`, `conclude_ab_test`, `list_active_tests`, `evaluate_cross_channel_transfer`, `apply_cross_channel_transfer`, `review_transfer_results`, `compute_trends`, `detect_anomalies`, `generate_report`, `list_reports`, `get_report`. Add safe tool names/patterns for read-only tools. |
| `instructions.md` | Add Phase 4 sections: Multi-Channel Orchestration workflow, Automated A/B Testing Loop instructions, Cross-Channel Learning Transfer protocol, Analytics and Reporting guidelines. Update the Core Workflow section to include autonomous loop behavior. |
| `context.py` | Add `active_ab_tests_summary` template variable (inject active test states into context). Add `pending_transfers_summary` for cross-channel transfer status. Add `recent_anomalies` for anomaly alerts. |
| `tools/analysis_tools.py` | Modify `save_learning` to trigger cross-channel transfer evaluation when a learning reaches medium confidence. Add `cross_channel_evidence` field support. |
| `tools/copy_tools.py` | Add `"winner"` and `"loser"` to the valid status values for variants. Add `specialist_log.json` writing. |
| `tools/metrics_tools.py` | Add `VALID_METRIC_TYPES` entries if new metrics are needed for analytics. No structural changes required. |
| `dashboard/src/lib/types.ts` | Add types: `ABTestState`, `ABTestCheck`, `TransferHypothesis`, `TrendData`, `AnomalyAlert`, `Report`, `ReportSummary`. Extend `CampaignStatus` with `"winner"` and `"loser"`. |
| `dashboard/src/lib/data-reader.ts` | Add functions: `listABTests`, `getABTest`, `listReports`, `getReport`. |
| `dashboard/src/app/layout.tsx` | Add navigation links for A/B Tests, Reports, and Cross-Channel pages. |
| `dashboard/src/app/page.tsx` | Add an "Active A/B Tests" card to the dashboard overview showing tests in COLLECTING state. Add an "Anomaly Alerts" card if any anomalies exist. |
| `requirements.txt` | Add `scipy>=1.11.0` for statistical functions (z-test, t-test). |

---

## 10. Dashboard Changes

### 10.1 Navigation Update

Add to the sidebar/nav in `layout.tsx`:

```
Dashboard       (existing)
Campaigns       (existing)
A/B Tests       (NEW) -- /ab-tests
Cross-Channel   (NEW) -- /cross-channel
Reports         (NEW) -- /reports
Playbook        (existing)
Connectors      (existing)
```

### 10.2 Dashboard Overview Additions

The main page (`page.tsx`) gains two new cards in the KPI row:

- **Active A/B Tests** -- count of tests in COLLECTING/WAITING state, with "oldest test" age
- **Anomaly Alerts** -- count of recent anomalies (last 7 days), with severity indicator

### 10.3 A/B Test Detail Page

The A/B test detail page (`/ab-tests/[testId]`) includes:

1. **State timeline** -- horizontal stepper showing DESIGNED -> DEPLOYING -> COLLECTING -> DECIDED -> COMPLETED with timestamps
2. **Metric comparison table** -- control vs treatment, with confidence intervals
3. **Statistical result panel** -- p-value, effect size, recommendation
4. **Check history** -- table of all checks performed with verdicts
5. **Action buttons** -- "Check Now" (triggers `check_ab_test`), "Conclude" (triggers `conclude_ab_test`), "Extend" (extends max duration)

### 10.4 Cross-Channel Page

The cross-channel page (`/cross-channel`) shows:

1. **Transfer board** -- Kanban-style columns: Proposed | Testing | Confirmed | Rejected
2. **Transfer cards** -- source learning, target channel, hypothesis, linked test status
3. **Transfer success rate** -- overall percentage of confirmed transfers

### 10.5 Reports Page

The reports page (`/reports`) provides:

1. **Report list** -- table with type, date, summary, link to detail
2. **Report detail** -- rendered markdown or structured JSON with sections

---

## 11. Migration and Rollout Strategy

### 11.1 Phase 4 can be rolled out incrementally

Phase 4 does not require a "big bang" deployment. The features are additive:

**Wave 1: Specialists and Multi-Channel (Week 1-2)**
- Create specialist tools
- Update `agent.yml` and `instructions.md`
- Test: single-channel specialist generates same quality as direct agent
- Test: multi-channel campaign dispatches correctly

**Wave 2: Automated A/B Testing (Week 3-4)**
- Create A/B test state machine tools
- Create stats module
- Create dashboard A/B test pages
- Test: full A/B lifecycle from design through winner declaration
- Test: statistical correctness with known test data

**Wave 3: Cross-Channel Learning (Week 5-6)**
- Create cross-channel transfer tools
- Update `save_learning` to trigger evaluation
- Create dashboard cross-channel page
- Test: learning transfer proposal generation
- Test: transfer test creation and result evaluation

**Wave 4: Analytics and Reporting (Week 7-8)**
- Create analytics tools (trends, anomalies, reports)
- Create dashboard analytics pages
- Update dashboard overview with new cards
- Test: trend computation accuracy
- Test: anomaly detection on synthetic data

### 11.2 Backward Compatibility

All Phase 4 additions are backward-compatible:
- The conductor IS the existing agent with more tools
- Existing campaigns, playbook, and knowledge files are unchanged
- The dashboard reads new data directories only when they exist (graceful fallback to empty arrays)
- Users can continue to use the agent in its Phase 1-3 mode without invoking any Phase 4 tools

### 11.3 Data Migration

No migration required. Phase 4 creates new directories and files. Existing data is read but not modified (except for the `cross_channel_evidence` field added to playbook entries, which is backward-compatible as an optional field).

---

## 12. Trade-Off Analysis

### 12.1 Specialists as Tools vs. Separate Agent Processes

| Factor | Tools (chosen) | Separate Processes |
|---|---|---|
| Complexity | Low -- Python functions | High -- process management, IPC |
| Latency | Medium -- LLM call inside tool | Low -- parallel execution |
| Framework compatibility | Full -- uses `@function_tool` | Partial -- needs custom launcher |
| Dashboard integration | Seamless -- same WebSocket | Complex -- needs routing proxy |
| Independent scaling | Not possible | Possible but premature |
| Failure isolation | Shared -- tool error fails the run | Isolated -- process crash does not kill others |

**Decision:** Tools. The added complexity of separate processes is not justified until the system handles 50+ concurrent campaigns requiring parallel generation.

### 12.2 File-Based Task Queue vs. Message Broker

| Factor | File-based (chosen) | Redis/RabbitMQ |
|---|---|---|
| Operational overhead | Zero -- just files | Must run and maintain a broker |
| Throughput | Low (fine for this use case) | High |
| Inspectability | Excellent -- read JSON files | Requires monitoring tools |
| Reliability | Good with filelock | Excellent with acknowledgment |
| Real-time push | Not supported | Supported |

**Decision:** File-based. The system processes A/B test checks on hour-to-day timescales. A message broker is unnecessary overhead.

### 12.3 Dashboard-Triggered Polling vs. Background Worker

| Factor | Dashboard polling (chosen) | Background worker |
|---|---|---|
| Infrastructure | Zero -- dashboard already exists | Needs separate process or cron |
| Reliability | Best-effort -- only runs when dashboard is viewed | Reliable -- runs on schedule |
| User experience | Natural -- checks happen when user is looking | Autonomous -- checks happen regardless |
| Implementation cost | Low -- one React hook | Medium -- new process + health monitoring |

**Decision:** Dashboard polling as default. Document the cron alternative for teams that want fully autonomous operation. Both approaches call the same `check_ab_test` tool, so switching is trivial.

### 12.4 Scipy Dependency for Statistics

| Factor | Scipy | Pure Python |
|---|---|---|
| Accuracy | High -- validated implementations | Medium -- must implement and validate ourselves |
| Bundle size | Large (~30MB) | Zero |
| Maintenance | Community-maintained | Must maintain ourselves |
| p-value correctness | CDF functions exact | Would need numerical approximation |

**Decision:** Scipy. Statistical correctness is critical for A/B testing. Implementing z-tests and t-tests from scratch risks subtle bugs that lead to wrong decisions. The 30MB dependency is acceptable.

---

## 13. ADRs

### ADR-001: Specialists Implemented as Tool Functions, Not Separate Agents

**Status:** Proposed

**Context:**
Phase 4 requires channel-specific specialist agents (email, SMS, ad, SEO) that generate copy with deep channel expertise. The OmniAgents framework uses a single `agent.yml` per agent process, and the existing dashboard connects to one agent via WebSocket. Running specialists as separate agents would require multiple processes, a routing layer, and changes to the dashboard connection model.

**Decision:**
Implement specialists as `@function_tool`-decorated Python functions that internally call the LLM. Each specialist loads its channel skill, reads the playbook, and constructs a specialized prompt before making a model API call. The conductor agent invokes specialists as regular tools.

**Consequences:**
- Easier: deployment remains single-process. Dashboard integration unchanged. Debugging is simpler (one log stream). No IPC protocol to design.
- Harder: specialists cannot run in parallel (tools execute sequentially within an agent run). If a specialist call is slow, the user sees a longer "tool executing" state. No independent scaling of specialists.

### ADR-002: A/B Test Lifecycle as File-Based State Machine

**Status:** Proposed

**Context:**
Automated A/B testing requires persistent state that survives process restarts and allows human inspection. The test lifecycle has multiple states with specific transition rules, and the decision criteria involve statistical computation.

**Decision:**
Implement the A/B test lifecycle as a state machine persisted in `ab_test_state.json` per campaign directory. State transitions are enacted by tool functions (`start_ab_test`, `check_ab_test`, `conclude_ab_test`). The conductor agent drives the state machine forward by calling these tools, either on user prompt, dashboard poll trigger, or scheduled check.

**Consequences:**
- Easier: state is inspectable (JSON files). Resumable after restart. Testable (create test state files and validate transitions). Dashboard can read state directly.
- Harder: no automatic state transitions -- requires external trigger. State corruption possible if a tool fails mid-transition (mitigated by filelock and atomic writes). No built-in timeout enforcement -- relies on the conductor checking `next_check_at`.

### ADR-003: Cross-Channel Transfers as Explicit Hypotheses

**Status:** Proposed

**Context:**
Cross-channel learning transfer could be implicit (automatically apply learnings to all channels) or explicit (propose a transfer hypothesis and test it). Implicit transfer risks applying a learning that does not generalize, potentially harming performance in the target channel.

**Decision:**
Use explicit transfer hypotheses. When a learning reaches medium confidence in one channel, the system proposes a transfer hypothesis with a specific adaptation for the target channel. The hypothesis must be tested via A/B test before the learning is accepted for the target channel. The transferability matrix defines which learning types are candidates for transfer.

**Consequences:**
- Easier: no risk of blindly applying a non-transferable learning. Every cross-channel application is validated by data. The transferability matrix is explicit and auditable.
- Harder: slower knowledge propagation -- each transfer requires a new A/B test. More campaigns to manage. Overhead of tracking transfer state. Some obviously-transferable learnings (like "urgency works") still require validation.

### ADR-004: Dashboard Polling for A/B Test Monitoring

**Status:** Proposed

**Context:**
The automated A/B test loop needs a mechanism to periodically check test progress and advance the state machine. Options: (a) dashboard-triggered polling when users view the page, (b) a background worker process, (c) a cron job that sends a WebSocket prompt.

**Decision:**
Dashboard-triggered polling as the default mechanism, with documentation for cron-based scheduling as an advanced option. The `useABTestMonitor` hook checks active tests on page load and triggers conductor evaluation for any tests past their scheduled check time.

**Consequences:**
- Easier: zero additional infrastructure. Natural user workflow -- tests advance when the marketer checks the dashboard. Simple to implement (one React hook + one prompt to conductor).
- Harder: tests do not advance unless someone opens the dashboard. For teams that want fully autonomous operation, they need to set up the cron alternative. Risk of stale tests if the dashboard is not visited for days.

---

## Appendix A: Updated `agent.yml` Structure

```yaml
name: Copy Agent
model: gpt-5.2
welcome_text: "Welcome. I'm your marketing copy agent..."
instructions_file: instructions.md
context: build_copy_context
tools:
  # Copy generation and campaign management (existing)
  - generate_copy
  - save_copy_variant
  - list_campaigns
  - get_campaign

  # Metrics (existing)
  - log_metrics
  - get_variant_metrics

  # Analysis and optimization (existing)
  - analyze_campaign
  - read_playbook
  - save_learning
  - design_ab_test
  - identify_patterns
  - get_recommendations

  # Knowledge management (existing)
  - save_audience_insight
  - save_competitor_note
  - search_knowledge

  # Platform integrations (existing)
  - send_email
  - send_sms
  - fetch_campaign_metrics
  - check_integrations

  # Research (existing)
  - web_fetch

  # Builtin tools (existing)
  - read_file
  - write_file
  - edit_file
  - glob_files
  - grep_files
  - web_search
  - display_artifact

  # --- Phase 4: Specialists ---
  - specialist_email
  - specialist_sms
  - specialist_ad
  - specialist_seo

  # --- Phase 4: Orchestration ---
  - plan_multi_channel_campaign
  - dispatch_to_specialist

  # --- Phase 4: Automated A/B Testing ---
  - start_ab_test
  - check_ab_test
  - conclude_ab_test
  - list_active_tests

  # --- Phase 4: Cross-Channel Learning ---
  - evaluate_cross_channel_transfer
  - apply_cross_channel_transfer
  - review_transfer_results

  # --- Phase 4: Analytics & Reporting ---
  - compute_trends
  - detect_anomalies
  - generate_report
  - list_reports
  - get_report

model_settings:
  temperature: 0.8
  max_tokens: 4096
use_safe_agent: true
safe_agent_options:
  safe_tool_names:
    # Existing safe tools
    - read_playbook
    - list_campaigns
    - get_campaign
    - get_variant_metrics
    - analyze_campaign
    - identify_patterns
    - get_recommendations
    - search_knowledge
    - check_integrations
    - fetch_campaign_metrics
    - read_file
    - glob_files
    - grep_files
    # Phase 4 safe tools (read-only)
    - list_active_tests
    - review_transfer_results
    - compute_trends
    - detect_anomalies
    - list_reports
    - get_report
  safe_tool_patterns:
    - "^read_.*"
    - "^get_.*"
    - "^list_.*"
    - "^search_.*"
    - "^identify_.*"
    - "^check_.*"
    - "^fetch_.*"
    - "^compute_.*"
    - "^detect_.*"
    - "^review_.*"
```

## Appendix B: Updated `instructions.md` Additions

The following sections should be appended to `instructions.md` after the existing content:

```markdown
---

## Phase 4: Multi-Agent Orchestration

### Multi-Channel Campaigns

When asked to create copy for multiple channels at once:

1. Call `plan_multi_channel_campaign` to decompose the brief into per-channel sub-briefs.
2. For each channel, call the appropriate specialist tool:
   - `specialist_email` for email
   - `specialist_sms` for SMS
   - `specialist_ad` for ads
   - `specialist_seo` for SEO
3. Each specialist generates variants using channel-specific skills and playbook learnings.
4. Present all variants grouped by channel.
5. If the user requests A/B testing, set up tests for each channel independently.

### Single-Channel Generation

For single-channel briefs, you MAY either:
- Use the existing generate/save workflow (backward compatible)
- Delegate to the specialist tool for deeper channel expertise

Prefer the specialist for complex briefs, new audiences, or when the playbook has relevant learnings to apply.

---

## Phase 4: Automated A/B Testing

### Starting a Test

After `design_ab_test` creates the test plan:
1. Call `start_ab_test` to deploy variants to platforms and begin collection.
2. The test enters COLLECTING state automatically.
3. Inform the user: "A/B test started. I'll check metrics at [next_check_at]."

### Monitoring

When asked to check A/B tests, or when `list_active_tests` shows tests past their check time:
1. Call `check_ab_test` for each active test.
2. Report the current state: sample sizes, metric values, statistical significance.
3. If a winner is declared, call `conclude_ab_test` to save the learning and mark the winner.

### Decision Criteria

- Do not declare a winner before the minimum sample size is reached.
- Require p < 0.05 for statistical significance (two-tailed test).
- If the maximum duration is reached without significance, report the test as inconclusive.
- Early stopping is allowed only when p < 0.01 and at least 50% of the sample has been collected.

---

## Phase 4: Cross-Channel Learning Transfer

After saving a learning with `save_learning`:
1. If the learning reaches medium confidence (confirmed 2+ times), call `evaluate_cross_channel_transfer`.
2. Review proposed transfers. For each viable transfer, call `apply_cross_channel_transfer` to create a test.
3. After the test completes, call `review_transfer_results` to confirm or reject the transfer.

Do NOT automatically apply learnings across channels without testing. Cross-channel transfer MUST be validated.

---

## Phase 4: Analytics & Reporting

### On-Demand Reports
When the user asks for a report, performance summary, or trend analysis:
1. Call `compute_trends` for the relevant channel(s) first.
2. Call `detect_anomalies` to check for any unusual metrics.
3. Call `generate_report` with the appropriate report type and parameters.
4. Present the report summary and offer the full report.

### Anomaly Handling
When `detect_anomalies` returns alerts:
1. Surface the anomaly to the user immediately.
2. Suggest possible causes (new variant deployed, external event, platform issue).
3. Recommend action (pause campaign, investigate metrics, increase monitoring).
```

## Appendix C: Updated `context.py` Additions

Add three new template variables alongside the existing three:

```python
# In build_copy_context(), add after step 3:

# 4. Load active A/B test summary
try:
    active_tests_summary = _build_active_tests_summary()
except Exception:
    active_tests_summary = "No active A/B tests."

# 5. Load pending cross-channel transfers
try:
    pending_transfers = _build_pending_transfers_summary()
except Exception:
    pending_transfers = "No pending cross-channel transfers."

# 6. Load recent anomalies
try:
    recent_anomalies = _build_recent_anomalies_summary()
except Exception:
    recent_anomalies = "No recent anomalies."
```

And add the corresponding template variables in `instructions.md`:

```markdown
## Active A/B Tests

{{ active_tests_summary }}

## Pending Cross-Channel Transfers

{{ pending_transfers }}

## Recent Anomalies

{{ recent_anomalies }}
```

---

*End of Phase 4 Architecture Document*
