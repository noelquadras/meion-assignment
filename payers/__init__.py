"""
Payer Adapters — one per TPA/insurer.

Each payer has a fundamentally different communication channel:

    Star Health   → REST API (programmatic, real-time)
    Medi Assist   → Portal + Email (async, needs polling/scraping)
    Paramount     → Email submission + Phone follow-up (partially automatable)
    CGHS          → Physical forms (cannot be automated)

The adapter pattern (BasePayer interface) normalises these into a uniform
submit/poll interface so the agent's state machine can treat all payers
the same way, while each adapter handles the channel-specific logic internally.
"""

from payers.mediassist import MediAssistPayer
from payers.starhealth import StarHealthPayer
from payers.paramount import ParamountPayer
from payers.cghs import CGHSPayer

__all__ = ["MediAssistPayer", "StarHealthPayer", "ParamountPayer", "CGHSPayer"]
