"""Indian astrology context server for the Model Context Protocol."""

from .calculations import calculate_sidereal_chart, calculate_vimshottari_dasha
from .context import calculate_person_context
from .geocoding import resolve_birth_location
from .profiles import (
    calculate_profile_context,
    list_birth_profiles,
    resolve_local_birth_timestamp,
    save_birth_profile,
)

__all__ = [
    "calculate_profile_context",
    "calculate_person_context",
    "calculate_sidereal_chart",
    "calculate_vimshottari_dasha",
    "list_birth_profiles",
    "resolve_local_birth_timestamp",
    "resolve_birth_location",
    "save_birth_profile",
]

__version__ = "0.1.0"
