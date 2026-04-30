"""
A/B test lifecycle tools for the Copy Agent.

Manages the full A/B test state machine: DESIGNED -> DEPLOYING -> COLLECTING ->
ANALYZING -> DECIDED/INCONCLUSIVE -> COMPLETED. Each test's state is persisted
as ab_test_state.json within the campaign directory.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from tools.lock import FileLock
from omniagents import function_tool

from tools.stats import two_proportion_z_test, welch_t_test, check_early_stopping

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CAMPAIGNS_DIR = DATA_DIR / "campaigns"

# Rate metrics use a two-proportion z-test; continuous metrics use Welch's t-test
RATE_METRICS = {
    "open_rate", "click_rate", "reply_rate", "conversion_rate",
    "unsubscribe_rate", "ctr", "delivery_rate", "opt_out_rate",
    "bounce_rate",
}

# Channel-specific heuristics for how long to wait before the first check
CHANNEL_CHECK_DELAYS = {
    "email": 24,   # hours
    "sms": 12,
    "ad": 48,
    "seo": 168,    # 7 days
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file, returning None if it does not exist or is invalid."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_json(path: Path, data: dict | list) -> None:
    """Write data to a JSON file with filelock protection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def _campaign_dir(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / campaign_id


def _state_path(campaign_id: str) -> Path:
    return _campaign_dir(campaign_id) / "ab_test_state.json"


def _ab_test_plan_path(campaign_id: str) -> Path:
    return _campaign_dir(campaign_id) / "ab_test.json"


def _transition_state(state: dict, new_state: str) -> None:
    """Advance the state machine and record in state_history."""
    now = datetime.now().isoformat()

    # Close the current state_history entry
    if state.get("state_history"):
        for entry in reversed(state["state_history"]):
            if entry.get("exited_at") is None:
                entry["exited_at"] = now
                break

    # Add new state entry
    state.setdefault("state_history", []).append({
        "state": new_state,
        "entered_at": now,
        "exited_at": None,
    })
    state["state"] = new_state


def _compute_next_check(channel: str) -> str:
    """Compute the next_check_at timestamp based on channel heuristics."""
    delay_hours = CHANNEL_CHECK_DELAYS.get(channel, 24)
    return (datetime.now() + timedelta(hours=delay_hours)).isoformat()


# ---------------------------------------------------------------------------
# Tool 1: start_ab_test
# ---------------------------------------------------------------------------

@function_tool
def start_ab_test(campaign_id: str, test_id: str = "") -> str:
    """Start an A/B test by transitioning it from DESIGNED to COLLECTING.

    Reads the existing ab_test.json plan (created by design_ab_test), creates
    the ab_test_state.json lifecycle file, transitions through DEPLOYING to
    COLLECTING, records platform deployment details, and sets the first
    check time.

    Args:
        campaign_id: The campaign containing the A/B test plan.
        test_id: Optional custom test ID. Auto-generated if omitted.
    """
    campaign_path = _campaign_dir(campaign_id)
    brief_path = campaign_path / "brief.json"
    plan_path = _ab_test_plan_path(campaign_id)
    state_path = _state_path(campaign_id)

    # Validate campaign exists
    if not brief_path.exists():
        return f"Error: Campaign '{campaign_id}' not found."

    # Validate A/B test plan exists
    plan = _load_json(plan_path)
    if plan is None:
        return (
            f"Error: No A/B test plan found for campaign '{campaign_id}'. "
            "Use design_ab_test to create a test plan first."
        )

    # Check if a test is already running
    existing_state = _load_json(state_path)
    if existing_state and existing_state.get("state") not in (None, "COMPLETED", "ARCHIVED"):
        return (
            f"Error: An A/B test is already active for campaign '{campaign_id}' "
            f"in state '{existing_state.get('state')}'. "
            "Conclude or archive the existing test first."
        )

    # Load campaign brief for channel info
    brief = _load_json(brief_path) or {}
    channel = brief.get("channel", "email")

    # Generate test ID
    if not test_id.strip():
        test_id = f"test-{campaign_id}-{uuid.uuid4().hex[:8]}"

    now = datetime.now().isoformat()

    # Build the state file
    state = {
        "test_id": test_id,
        "campaign_id": campaign_id,
        "state": "DESIGNED",
        "state_history": [
            {"state": "DESIGNED", "entered_at": now, "exited_at": None},
        ],
        "hypothesis": plan.get("hypothesis", ""),
        "variable_tested": plan.get("variable_tested", ""),
        "variants": {
            "control": {
                "variant_id": plan.get("control", {}).get("variant_id", "control"),
                "description": plan.get("control", {}).get("description", ""),
                "platform_id": None,
            },
            "treatment": {
                "variant_id": plan.get("treatment", {}).get("variant_id", "treatment"),
                "description": plan.get("treatment", {}).get("description", ""),
                "platform_id": None,
            },
        },
        "decision_criteria": {
            "primary_metric": plan.get("primary_metric", "click_rate"),
            "metrics_to_track": plan.get("metrics_to_track", ["click_rate"]),
            "minimum_sample_size": plan.get("sample_size", {}).get("per_variant", 400),
            "minimum_confidence_level": 0.95,
            "minimum_detectable_effect": 0.20,
            "maximum_duration_days": 14,
            "early_stopping": {
                "enabled": True,
                "check_after_samples": plan.get("sample_size", {}).get("per_variant", 400) // 2,
                "significance_threshold": 0.01,
            },
        },
        "current_metrics": {},
        "checks_performed": [],
        "result": None,
        "winner": None,
        "learning_saved": False,
        "next_check_at": None,
        "created_at": now,
    }

    # Transition DESIGNED -> DEPLOYING
    _transition_state(state, "DEPLOYING")

    # Simulate deployment -- in production this would call platform adapters
    # (send_email, send_sms, etc.) and record the platform IDs
    control_vid = state["variants"]["control"]["variant_id"]
    treatment_vid = state["variants"]["treatment"]["variant_id"]

    # Record platform IDs (placeholder until real adapters are connected)
    state["variants"]["control"]["platform_id"] = f"platform_{control_vid}_{uuid.uuid4().hex[:6]}"
    state["variants"]["treatment"]["platform_id"] = f"platform_{treatment_vid}_{uuid.uuid4().hex[:6]}"

    # Transition DEPLOYING -> COLLECTING
    _transition_state(state, "COLLECTING")

    # Set the first check time
    state["next_check_at"] = _compute_next_check(channel)

    # Persist
    _save_json(state_path, state)

    return (
        f"A/B test '{test_id}' started for campaign '{campaign_id}'.\n\n"
        f"State: COLLECTING\n"
        f"Hypothesis: {state['hypothesis']}\n"
        f"Variable: {state['variable_tested']}\n"
        f"Control: {control_vid} (platform: {state['variants']['control']['platform_id']})\n"
        f"Treatment: {treatment_vid} (platform: {state['variants']['treatment']['platform_id']})\n"
        f"Primary metric: {state['decision_criteria']['primary_metric']}\n"
        f"Min sample per variant: {state['decision_criteria']['minimum_sample_size']}\n"
        f"Next check at: {state['next_check_at']}\n\n"
        f"The test is now live and collecting data. Use check_ab_test to evaluate "
        f"when enough metrics have been gathered."
    )


# ---------------------------------------------------------------------------
# Tool 2: check_ab_test
# ---------------------------------------------------------------------------

@function_tool
def check_ab_test(campaign_id: str, test_id: str = "") -> str:
    """Check an active A/B test, pull latest metrics, run statistical analysis,
    and return a verdict.

    Reads the ab_test_state.json, loads current metrics from metrics.json,
    runs the appropriate statistical test, and returns one of:
    - insufficient_data: not enough samples yet
    - trending_{variant}: interesting signal but not yet significant
    - winner_{variant}: statistically significant result (advances to DECIDED)
    - inconclusive: max duration reached with no significant difference

    Args:
        campaign_id: The campaign with the active A/B test.
        test_id: Optional test ID for validation. If omitted, uses the campaign's active test.
    """
    state_path = _state_path(campaign_id)
    state = _load_json(state_path)

    if state is None:
        return (
            f"Error: No A/B test state found for campaign '{campaign_id}'. "
            "Use start_ab_test to begin a test."
        )

    # Validate state
    current_state = state.get("state", "")
    if current_state not in ("COLLECTING", "WAITING"):
        return (
            f"Error: A/B test for campaign '{campaign_id}' is in state '{current_state}'. "
            f"check_ab_test only works on tests in COLLECTING or WAITING state."
        )

    # Optionally validate test_id
    if test_id.strip() and state.get("test_id") != test_id.strip():
        return (
            f"Error: Test ID mismatch. Expected '{state.get('test_id')}', "
            f"got '{test_id}'."
        )

    # Load metrics
    metrics_path = _campaign_dir(campaign_id) / "metrics.json"
    metrics_data = _load_json(metrics_path)
    if not metrics_data:
        # Transition to WAITING if no metrics at all
        if current_state != "WAITING":
            _transition_state(state, "WAITING")
            brief = _load_json(_campaign_dir(campaign_id) / "brief.json") or {}
            state["next_check_at"] = _compute_next_check(brief.get("channel", "email"))
            _save_json(state_path, state)
        return (
            f"No metrics found for campaign '{campaign_id}'. "
            f"Test remains in {state['state']} state. "
            f"Next check at: {state.get('next_check_at')}"
        )

    metrics_list = metrics_data if isinstance(metrics_data, list) else metrics_data.get("metrics", [])

    # Extract metrics per variant
    primary_metric = state["decision_criteria"]["primary_metric"]
    control_vid = state["variants"]["control"]["variant_id"]
    treatment_vid = state["variants"]["treatment"]["variant_id"]
    min_sample = state["decision_criteria"]["minimum_sample_size"]

    # Gather all metric values per variant
    variant_values: dict[str, dict[str, list[float]]] = {}
    for entry in metrics_list:
        vid = entry.get("variant_id", "")
        mtype = (entry.get("metric_type") or entry.get("type") or "").lower().strip()
        value = entry.get("value")
        if vid and mtype and value is not None:
            variant_values.setdefault(vid, {}).setdefault(mtype, []).append(float(value))

    # Get primary metric values
    control_values = variant_values.get(control_vid, {}).get(primary_metric, [])
    treatment_values = variant_values.get(treatment_vid, {}).get(primary_metric, [])

    control_sample = len(control_values)
    treatment_sample = len(treatment_values)

    # Update current_metrics in state
    for vid in (control_vid, treatment_vid):
        vid_metrics = variant_values.get(vid, {})
        state["current_metrics"][vid] = {}
        for mtype, vals in vid_metrics.items():
            state["current_metrics"][vid][mtype] = round(sum(vals) / len(vals), 6)
            state["current_metrics"][vid][f"{mtype}_sample"] = len(vals)

    now = datetime.now().isoformat()

    # Check sample size
    if control_sample < 5 or treatment_sample < 5:
        check_record = {
            "checked_at": now,
            f"{control_vid}_sample": control_sample,
            f"{treatment_vid}_sample": treatment_sample,
            "verdict": "insufficient_data",
        }
        state["checks_performed"].append(check_record)
        if current_state != "WAITING":
            _transition_state(state, "WAITING")
        brief = _load_json(_campaign_dir(campaign_id) / "brief.json") or {}
        state["next_check_at"] = _compute_next_check(brief.get("channel", "email"))
        _save_json(state_path, state)

        return (
            f"Insufficient data for A/B test on campaign '{campaign_id}'.\n"
            f"  Control ({control_vid}): {control_sample} samples\n"
            f"  Treatment ({treatment_vid}): {treatment_sample} samples\n"
            f"  Minimum required: {min_sample} per variant\n"
            f"State: WAITING. Next check at: {state['next_check_at']}"
        )

    # Run statistical test
    is_rate_metric = primary_metric in RATE_METRICS
    confidence_level = state["decision_criteria"]["minimum_confidence_level"]
    alpha = 1 - confidence_level

    if is_rate_metric:
        # For rate metrics, compute successes from rate * sample_size
        control_mean = sum(control_values) / len(control_values)
        treatment_mean = sum(treatment_values) / len(treatment_values)
        control_successes = int(round(control_mean * control_sample))
        treatment_successes = int(round(treatment_mean * treatment_sample))

        z_score, p_value = two_proportion_z_test(
            control_successes, control_sample,
            treatment_successes, treatment_sample,
        )
        test_name = "two-proportion z-test"
        test_stat = z_score
        stat_label = "z-score"
    else:
        test_stat, p_value = welch_t_test(control_values, treatment_values)
        test_name = "Welch's t-test"
        stat_label = "t-statistic"
        control_mean = sum(control_values) / len(control_values)
        treatment_mean = sum(treatment_values) / len(treatment_values)

    # Check for early stopping
    total_sample = control_sample + treatment_sample
    total_needed = min_sample * 2
    fraction = min(1.0, total_sample / total_needed) if total_needed > 0 else 1.0
    num_looks = len(state["checks_performed"]) + 1

    early_stop = False
    early_stopping_config = state["decision_criteria"].get("early_stopping", {})
    if early_stopping_config.get("enabled", False):
        min_early_samples = early_stopping_config.get("check_after_samples", min_sample // 2)
        if min(control_sample, treatment_sample) >= min_early_samples:
            early_stop = check_early_stopping(p_value, fraction, num_looks)

    # Determine verdict
    enough_samples = min(control_sample, treatment_sample) >= min_sample

    # Check max duration
    first_state = state.get("state_history", [{}])[0]
    started_at = first_state.get("entered_at", now)
    try:
        start_dt = datetime.fromisoformat(started_at)
        elapsed_days = (datetime.now() - start_dt).days
    except (ValueError, TypeError):
        elapsed_days = 0
    max_days = state["decision_criteria"].get("maximum_duration_days", 14)
    duration_expired = elapsed_days >= max_days

    if p_value < alpha and (enough_samples or early_stop):
        # We have a winner
        if treatment_mean > control_mean:
            winner_vid = treatment_vid
            winner_label = "treatment"
        else:
            winner_vid = control_vid
            winner_label = "control"

        # If metric is negative (lower is better), flip
        from tools.analysis_tools import NEGATIVE_METRICS
        if primary_metric in NEGATIVE_METRICS:
            winner_vid = treatment_vid if treatment_mean < control_mean else control_vid
            winner_label = "treatment" if treatment_mean < control_mean else "control"

        verdict = f"winner_{winner_label}"
        state["winner"] = winner_vid
        state["result"] = {
            "verdict": verdict,
            "winner_variant": winner_vid,
            "p_value": round(p_value, 6),
            "test_statistic": round(test_stat, 4),
            "test_type": test_name,
            "control_mean": round(control_mean, 6),
            "treatment_mean": round(treatment_mean, 6),
            "effect_size": round(abs(treatment_mean - control_mean), 6),
            "relative_lift": round(
                abs(treatment_mean - control_mean) / control_mean * 100, 2
            ) if control_mean != 0 else 0,
            "early_stopped": early_stop and not enough_samples,
            "decided_at": now,
        }

        _transition_state(state, "DECIDED")

    elif duration_expired:
        verdict = "inconclusive"
        state["result"] = {
            "verdict": "inconclusive",
            "p_value": round(p_value, 6),
            "test_statistic": round(test_stat, 4),
            "test_type": test_name,
            "control_mean": round(control_mean, 6),
            "treatment_mean": round(treatment_mean, 6),
            "reason": f"Maximum duration of {max_days} days reached without significance.",
            "decided_at": now,
        }
        _transition_state(state, "INCONCLUSIVE")

    elif p_value < 0.10:
        # Trending but not yet significant
        trending_label = "treatment" if treatment_mean > control_mean else "control"
        if primary_metric in NEGATIVE_METRICS:
            trending_label = "treatment" if treatment_mean < control_mean else "control"
        verdict = f"trending_{trending_label}"
    else:
        verdict = "insufficient_data"

    # Record the check
    check_record = {
        "checked_at": now,
        f"{control_vid}_sample": control_sample,
        f"{treatment_vid}_sample": treatment_sample,
        "verdict": verdict,
        "p_value": round(p_value, 6),
        "test_statistic": round(test_stat, 4),
        "test_type": test_name,
    }
    state["checks_performed"].append(check_record)

    # Set next check if not concluded
    if state["state"] in ("COLLECTING", "WAITING"):
        brief = _load_json(_campaign_dir(campaign_id) / "brief.json") or {}
        state["next_check_at"] = _compute_next_check(brief.get("channel", "email"))

    _save_json(state_path, state)

    # Build response
    lines = [
        f"A/B Test Check: {state.get('test_id', campaign_id)}",
        "=" * 60,
        "",
        f"Verdict: {verdict.upper()}",
        f"State: {state['state']}",
        "",
        f"Statistical test: {test_name}",
        f"  {stat_label}: {test_stat:.4f}",
        f"  p-value: {p_value:.6f}",
        f"  Significance threshold: {alpha}",
        "",
        f"Control ({control_vid}):",
        f"  {primary_metric} mean: {control_mean:.6f}",
        f"  Sample size: {control_sample}",
        "",
        f"Treatment ({treatment_vid}):",
        f"  {primary_metric} mean: {treatment_mean:.6f}",
        f"  Sample size: {treatment_sample}",
        "",
        f"Required sample per variant: {min_sample}",
        f"Elapsed days: {elapsed_days} / {max_days} max",
    ]

    if early_stop and not enough_samples:
        lines.append("")
        lines.append("** Early stopping triggered -- result is significant at adjusted threshold **")

    if state["state"] == "DECIDED":
        lines.append("")
        lines.append(f"WINNER: {state['winner']} ({verdict})")
        lift = state["result"].get("relative_lift", 0)
        lines.append(f"Relative lift: {lift:.2f}%")
        lines.append("")
        lines.append("Next: Use conclude_ab_test to save the learning and mark the winner.")
    elif state["state"] == "INCONCLUSIVE":
        lines.append("")
        lines.append("The test reached maximum duration without a statistically significant result.")
        lines.append("Options: extend the test duration, or conclude as inconclusive.")
    elif state.get("next_check_at"):
        lines.append("")
        lines.append(f"Next check scheduled: {state['next_check_at']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 3: conclude_ab_test
# ---------------------------------------------------------------------------

@function_tool
def conclude_ab_test(campaign_id: str, test_id: str = "") -> str:
    """Conclude a decided A/B test by saving the learning, marking the winner
    in variants.json, and transitioning to COMPLETED.

    Call this after check_ab_test returns a winner or inconclusive verdict.
    It persists the learning to the playbook, marks winning/losing variants,
    and triggers cross-channel evaluation eligibility.

    Args:
        campaign_id: The campaign with the decided A/B test.
        test_id: Optional test ID for validation.
    """
    state_path = _state_path(campaign_id)
    state = _load_json(state_path)

    if state is None:
        return f"Error: No A/B test state found for campaign '{campaign_id}'."

    current_state = state.get("state", "")
    if current_state not in ("DECIDED", "INCONCLUSIVE"):
        return (
            f"Error: A/B test for campaign '{campaign_id}' is in state '{current_state}'. "
            f"conclude_ab_test requires DECIDED or INCONCLUSIVE state."
        )

    if test_id.strip() and state.get("test_id") != test_id.strip():
        return (
            f"Error: Test ID mismatch. Expected '{state.get('test_id')}', "
            f"got '{test_id}'."
        )

    result = state.get("result", {})
    winner_vid = state.get("winner")
    control_vid = state["variants"]["control"]["variant_id"]
    treatment_vid = state["variants"]["treatment"]["variant_id"]
    primary_metric = state["decision_criteria"]["primary_metric"]
    hypothesis = state.get("hypothesis", "")
    variable_tested = state.get("variable_tested", "")

    lines = [
        f"A/B Test Concluded: {state.get('test_id', campaign_id)}",
        "=" * 60,
    ]

    # Mark variants as winner/loser in variants.json
    variants_path = _campaign_dir(campaign_id) / "variants.json"
    variants_data = _load_json(variants_path)

    if isinstance(variants_data, list) and winner_vid:
        loser_vid = treatment_vid if winner_vid == control_vid else control_vid
        for v in variants_data:
            vid = v.get("variant_id") or v.get("id", "")
            if vid == winner_vid:
                v["status"] = "winner"
            elif vid == loser_vid:
                v["status"] = "loser"
        _save_json(variants_path, variants_data)
        lines.append(f"\nVariant '{winner_vid}' marked as winner in variants.json.")
        lines.append(f"Variant '{loser_vid}' marked as loser.")

    # Build and save learning
    brief = _load_json(_campaign_dir(campaign_id) / "brief.json") or {}
    channel = brief.get("channel", "general")

    if current_state == "DECIDED" and winner_vid:
        control_mean = result.get("control_mean", 0)
        treatment_mean = result.get("treatment_mean", 0)
        lift = result.get("relative_lift", 0)
        p_val = result.get("p_value", 1.0)

        learning_text = (
            f"A/B test confirmed: {hypothesis}. "
            f"The {variable_tested} variant '{winner_vid}' achieved "
            f"{primary_metric}={result.get('treatment_mean' if winner_vid == treatment_vid else 'control_mean', 0):.4f} "
            f"vs {result.get('control_mean' if winner_vid == treatment_vid else 'treatment_mean', 0):.4f} "
            f"({lift:.1f}% lift, p={p_val:.4f})."
        )
        evidence_text = (
            f"Campaign: {campaign_id}, Test: {state.get('test_id')}, "
            f"Control: {control_vid}, Treatment: {treatment_vid}, "
            f"p-value: {p_val:.6f}"
        )

        # Save the learning data into the state for the agent to call save_learning
        state["learning_recommendation"] = {
            "category": channel,
            "learning": learning_text,
            "evidence": evidence_text,
            "confidence": "medium",
        }
        state["learning_saved"] = True

        lines.append("")
        lines.append("Recommended learning to save:")
        lines.append(f"  Category: {channel}")
        lines.append(f"  Learning: {learning_text}")
        lines.append(f"  Evidence: {evidence_text}")
        lines.append(f"  Confidence: medium")
        lines.append("")
        lines.append(
            "Call save_learning with the above details to persist this insight. "
            "If the learning reaches medium confidence, it becomes eligible for "
            "cross-channel transfer via evaluate_cross_channel_transfer."
        )

    elif current_state == "INCONCLUSIVE":
        state["learning_recommendation"] = {
            "note": "Test was inconclusive -- no learning to save.",
            "reason": result.get("reason", "No significant difference found."),
        }
        lines.append("")
        lines.append(f"Test was inconclusive: {result.get('reason', 'No significant difference.')}")
        lines.append("No learning saved. Consider extending the test or redesigning with a larger effect size.")

    # Transition to COMPLETED
    _transition_state(state, "COMPLETED")
    _save_json(state_path, state)

    lines.append("")
    lines.append(f"State: COMPLETED")
    lines.append(f"Test archived at: {_state_path(campaign_id)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 4: list_active_tests
# ---------------------------------------------------------------------------

@function_tool
def list_active_tests() -> str:
    """List all A/B tests currently in COLLECTING or WAITING state.

    Returns a summary of each active test including campaign, hypothesis,
    current metrics, time since last check, and next check time. This is
    a read-only tool used by the conductor to decide which tests to check.
    """
    if not CAMPAIGNS_DIR.exists():
        return "No campaigns directory found. No active tests."

    active_tests: list[dict] = []

    for campaign_path in CAMPAIGNS_DIR.iterdir():
        if not campaign_path.is_dir():
            continue
        state_file = campaign_path / "ab_test_state.json"
        if not state_file.exists():
            continue

        state = _load_json(state_file)
        if state is None:
            continue

        current_state = state.get("state", "")
        if current_state not in ("COLLECTING", "WAITING"):
            continue

        # Compute time since last check
        checks = state.get("checks_performed", [])
        last_check_at = checks[-1]["checked_at"] if checks else None
        if last_check_at:
            try:
                last_check_dt = datetime.fromisoformat(last_check_at)
                hours_since = (datetime.now() - last_check_dt).total_seconds() / 3600
                last_check_label = f"{hours_since:.1f}h ago"
            except (ValueError, TypeError):
                last_check_label = "unknown"
        else:
            last_check_label = "never checked"

        # Summarize current metrics
        current_metrics = state.get("current_metrics", {})
        primary = state.get("decision_criteria", {}).get("primary_metric", "")
        metrics_summary = []
        for vid, vid_metrics in current_metrics.items():
            val = vid_metrics.get(primary)
            sample = vid_metrics.get(f"{primary}_sample", "?")
            if val is not None:
                metrics_summary.append(f"{vid}: {primary}={val:.4f} (n={sample})")

        # Check if past next_check_at
        next_check = state.get("next_check_at")
        is_overdue = False
        if next_check:
            try:
                next_dt = datetime.fromisoformat(next_check)
                is_overdue = datetime.now() > next_dt
            except (ValueError, TypeError):
                pass

        active_tests.append({
            "test_id": state.get("test_id", "unknown"),
            "campaign_id": state.get("campaign_id", campaign_path.name),
            "state": current_state,
            "hypothesis": state.get("hypothesis", ""),
            "primary_metric": primary,
            "metrics_summary": metrics_summary,
            "last_check": last_check_label,
            "next_check_at": next_check or "not set",
            "is_overdue": is_overdue,
            "checks_count": len(checks),
        })

    if not active_tests:
        return "No active A/B tests found."

    # Sort: overdue first, then by next_check_at
    active_tests.sort(key=lambda t: (not t["is_overdue"], t["next_check_at"] or ""))

    lines = [
        f"Active A/B Tests: {len(active_tests)}",
        "=" * 60,
    ]

    for i, t in enumerate(active_tests, 1):
        overdue_marker = " [OVERDUE]" if t["is_overdue"] else ""
        lines.append("")
        lines.append(f"{i}. {t['test_id']}{overdue_marker}")
        lines.append(f"   Campaign: {t['campaign_id']}")
        lines.append(f"   State: {t['state']}")
        lines.append(f"   Hypothesis: {t['hypothesis']}")
        lines.append(f"   Primary metric: {t['primary_metric']}")
        if t["metrics_summary"]:
            for ms in t["metrics_summary"]:
                lines.append(f"   {ms}")
        else:
            lines.append("   No metrics collected yet")
        lines.append(f"   Last check: {t['last_check']} ({t['checks_count']} total)")
        lines.append(f"   Next check: {t['next_check_at']}")

    return "\n".join(lines)
