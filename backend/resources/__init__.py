from .base import ResourceAdapter
from .thamizhimorph import ThamizhiMorphAdapter, parse_structured_morphology
from .akarathi import ThaniThamizhAkarathiAdapter
from .wordnet import TamilWordNetAdapter

__all__ = [
    "ResourceAdapter",
    "ThamizhiMorphAdapter",
    "parse_structured_morphology",
    "ThaniThamizhAkarathiAdapter",
    "TamilWordNetAdapter",
]
