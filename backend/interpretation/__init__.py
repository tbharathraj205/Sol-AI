"""
SOL AI Contextual Interpretation Package.
"""

from backend.interpretation.schemas import (
    HighlightOffset,
    LiteraryContextItem,
    SOLResponse,
    EvidencePack,
)
from backend.interpretation.context_selector import SentamizhContextSelector
from backend.interpretation.evidence_pack import build_evidence_pack
from backend.interpretation.literary_processor import process_literary_evidence
from backend.interpretation.interpreter import (
    BaseLLMInterpreter,
    MockLLMInterpreter,
    GeminiLLMInterpreter,
    get_interpreter,
)

__all__ = [
    "HighlightOffset",
    "LiteraryContextItem",
    "SOLResponse",
    "EvidencePack",
    "SentamizhContextSelector",
    "build_evidence_pack",
    "process_literary_evidence",
    "BaseLLMInterpreter",
    "MockLLMInterpreter",
    "GeminiLLMInterpreter",
    "get_interpreter",
]
