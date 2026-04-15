"""
Shared pytest fixtures for the Copy Agent test suite.

The primary fixture is `tmp_data_dir` which creates a temporary data directory
structure and monkeypatches DATA_DIR / CAMPAIGNS_DIR in all tool modules so
tests never touch the real data/ folder.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest


def call_tool(tool_obj, *args, **kwargs):
    """Call a @function_tool-wrapped function by accessing its _original_func."""
    fn = getattr(tool_obj, "_original_func", tool_obj)
    return fn(*args, **kwargs)

# ---------------------------------------------------------------------------
# All modules that have a DATA_DIR or CAMPAIGNS_DIR we need to redirect
# ---------------------------------------------------------------------------
_TOOL_MODULES_WITH_DATA_DIR = [
    "tools.copy_tools",
    "tools.metrics_tools",
    "tools.analysis_tools",
    "tools.ab_test_tools",
    "tools.orchestration_tools",
    "tools.cross_channel_tools",
    "tools.knowledge_tools",
    "tools.analytics_tools",
    "tools.specialists.email_specialist",
    "tools.specialists.sms_specialist",
    "tools.specialists.ad_specialist",
    "tools.specialists.seo_specialist",
]

_MODULES_WITH_CAMPAIGNS_DIR = [
    "tools.copy_tools",
    "tools.ab_test_tools",
    "tools.analytics_tools",
    "tools.cross_channel_tools",
    "tools.orchestration_tools",
    "tools.specialists.email_specialist",
    "tools.specialists.sms_specialist",
    "tools.specialists.ad_specialist",
    "tools.specialists.seo_specialist",
]


# ---------------------------------------------------------------------------
# Core fixture: temporary data directory with monkeypatched paths
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_data_dir(tmp_path, monkeypatch):
    """Create a temp data directory structure and redirect all tool modules to it.

    Directory layout created:
        tmp_path/
        ├── campaigns/
        ├── orchestration/
        │   └── transfers/
        ├── reports/
        └── playbook.json   (empty learnings)
    """
    data_dir = tmp_path / "data"
    campaigns_dir = data_dir / "campaigns"
    campaigns_dir.mkdir(parents=True)
    (data_dir / "orchestration" / "transfers").mkdir(parents=True)
    (data_dir / "reports").mkdir(parents=True)

    # Seed empty playbook
    playbook = {"learnings": []}
    (data_dir / "playbook.json").write_text(json.dumps(playbook), encoding="utf-8")

    # Monkeypatch DATA_DIR in all tool modules
    for mod_name in _TOOL_MODULES_WITH_DATA_DIR:
        try:
            mod = __import__(mod_name, fromlist=["DATA_DIR"])
            monkeypatch.setattr(mod, "DATA_DIR", data_dir)
        except (ImportError, AttributeError):
            pass

    # Monkeypatch CAMPAIGNS_DIR in modules that have it
    for mod_name in _MODULES_WITH_CAMPAIGNS_DIR:
        try:
            mod = __import__(mod_name, fromlist=["CAMPAIGNS_DIR"])
            monkeypatch.setattr(mod, "CAMPAIGNS_DIR", campaigns_dir)
        except (ImportError, AttributeError):
            pass

    # Monkeypatch PLAYBOOK_PATH and REPORTS_DIR in analytics_tools
    try:
        import tools.analytics_tools as at
        monkeypatch.setattr(at, "PLAYBOOK_PATH", data_dir / "playbook.json")
        monkeypatch.setattr(at, "REPORTS_DIR", data_dir / "reports")
    except (ImportError, AttributeError):
        pass

    # Monkeypatch ORCHESTRATION_DIR in orchestration_tools
    try:
        import tools.orchestration_tools as ot
        monkeypatch.setattr(ot, "ORCHESTRATION_DIR", data_dir / "orchestration")
    except (ImportError, AttributeError):
        pass

    # Monkeypatch PLAYBOOK_PATH and TRANSFERS_DIR in cross_channel_tools
    try:
        import tools.cross_channel_tools as cct
        monkeypatch.setattr(cct, "PLAYBOOK_PATH", data_dir / "playbook.json")
        monkeypatch.setattr(cct, "TRANSFERS_DIR", data_dir / "orchestration" / "transfers")
    except (ImportError, AttributeError):
        pass

    return data_dir


# ---------------------------------------------------------------------------
# Seed fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_campaign(tmp_data_dir):
    """Create a complete test campaign with brief, 2 variants, and metrics.

    Returns the campaign_id ("test-campaign").
    """
    campaign_id = "test-campaign"
    campaign_dir = tmp_data_dir / "campaigns" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)

    brief = {
        "campaign_id": campaign_id,
        "campaign_name": "Test Campaign",
        "brief": "Write compelling email copy for our spring sale.",
        "channel": "email",
        "num_variants": 2,
        "created_at": "2026-03-28T10:00:00",
        "status": "active",
    }
    (campaign_dir / "brief.json").write_text(json.dumps(brief, indent=2), encoding="utf-8")

    variants = [
        {
            "variant_id": "v1",
            "channel": "email",
            "content": "Don't miss our biggest spring sale — 30% off everything!",
            "subject_line": "Spring Sale: 30% Off Everything",
            "cta": "Shop Now",
            "tone": "urgent",
            "notes": "",
            "created_at": "2026-03-28T10:05:00",
            "status": "draft",
        },
        {
            "variant_id": "v2",
            "channel": "email",
            "content": "Spring has sprung and so have our deals. Enjoy 30% off.",
            "subject_line": "Fresh Deals for a Fresh Season",
            "cta": "Browse Deals",
            "tone": "playful",
            "notes": "",
            "created_at": "2026-03-28T10:06:00",
            "status": "draft",
        },
    ]
    (campaign_dir / "variants.json").write_text(json.dumps(variants, indent=2), encoding="utf-8")

    metrics = [
        {"variant_id": "v1", "metric_type": "open_rate", "value": 0.22, "date": "2026-04-01", "notes": "", "logged_at": "2026-04-01T12:00:00"},
        {"variant_id": "v1", "metric_type": "click_rate", "value": 0.05, "date": "2026-04-01", "notes": "", "logged_at": "2026-04-01T12:00:00"},
        {"variant_id": "v2", "metric_type": "open_rate", "value": 0.31, "date": "2026-04-01", "notes": "", "logged_at": "2026-04-01T12:00:00"},
        {"variant_id": "v2", "metric_type": "click_rate", "value": 0.08, "date": "2026-04-01", "notes": "", "logged_at": "2026-04-01T12:00:00"},
    ]
    (campaign_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return campaign_id


@pytest.fixture()
def seed_playbook(tmp_data_dir):
    """Seed playbook.json with 3 test learnings across categories.

    Returns the path to playbook.json.
    """
    playbook = {
        "learnings": [
            {
                "id": "learn_001",
                "category": "email",
                "learning": "Subject lines with numbers get 15-20% higher open rates",
                "evidence": ["test-campaign/v2"],
                "confidence": 0.75,
                "times_confirmed": 2,
                "times_contradicted": 0,
                "first_observed": "2026-03-28",
                "last_confirmed": "2026-04-01",
                "tags": ["subject-line", "numbers", "open-rate"],
            },
            {
                "id": "learn_002",
                "category": "sms",
                "learning": "Action verbs in first 3 words boost click-through by 10%",
                "evidence": ["sms-promo-01/v1"],
                "confidence": 0.5,
                "times_confirmed": 1,
                "times_contradicted": 0,
                "first_observed": "2026-03-30",
                "last_confirmed": "2026-03-30",
                "tags": ["action-verbs", "ctr"],
            },
            {
                "id": "learn_003",
                "category": "general",
                "learning": "Urgency-based CTAs outperform curiosity-based CTAs",
                "evidence": ["test-campaign/v1"],
                "confidence": 0.4,
                "times_confirmed": 1,
                "times_contradicted": 1,
                "first_observed": "2026-03-29",
                "last_confirmed": "2026-03-29",
                "tags": ["cta", "urgency"],
            },
        ]
    }
    path = tmp_data_dir / "playbook.json"
    path.write_text(json.dumps(playbook, indent=2), encoding="utf-8")
    return path


@pytest.fixture()
def seed_ab_test(seed_campaign, tmp_data_dir):
    """Add an ab_test_state.json in COLLECTING state to the test campaign.

    Returns (campaign_id, test_id).
    """
    campaign_id = seed_campaign
    test_id = "ab-test-001"
    campaign_dir = tmp_data_dir / "campaigns" / campaign_id

    ab_test_state = {
        "test_id": test_id,
        "campaign_id": campaign_id,
        "state": "COLLECTING",
        "variant_a": "v1",
        "variant_b": "v2",
        "metric": "open_rate",
        "hypothesis": "Playful tone (v2) will have higher open rate than urgent tone (v1)",
        "created_at": "2026-04-01T10:00:00",
        "started_at": "2026-04-01T10:05:00",
        "next_check_at": "2026-04-02T10:05:00",
        "check_history": [],
        "state_history": [
            {"state": "DESIGNED", "at": "2026-04-01T10:00:00"},
            {"state": "COLLECTING", "at": "2026-04-01T10:05:00"},
        ],
    }
    (campaign_dir / "ab_test_state.json").write_text(
        json.dumps(ab_test_state, indent=2), encoding="utf-8"
    )

    return campaign_id, test_id
