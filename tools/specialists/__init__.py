"""
Channel specialist tools for the Copy Agent.

Each specialist is a @function_tool that generates copy variants for a
specific channel by loading the relevant skill file, reading playbook
learnings, and making an LLM call to produce structured output.

Exports:
    specialist_email  -- Email copy generation
    specialist_sms    -- SMS copy generation
    specialist_ad     -- Advertising copy generation
    specialist_seo    -- SEO copy generation
"""

from tools.specialists.email_specialist import specialist_email
from tools.specialists.sms_specialist import specialist_sms
from tools.specialists.ad_specialist import specialist_ad
from tools.specialists.seo_specialist import specialist_seo

__all__ = [
    "specialist_email",
    "specialist_sms",
    "specialist_ad",
    "specialist_seo",
]
