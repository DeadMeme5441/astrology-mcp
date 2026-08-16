"""Canonical tables used by the Lahiri sidereal calculation engine."""

from __future__ import annotations

RASHIS = (
    {"name": "Mesha", "english": "Aries", "lord": "Mars", "element": "Fire", "modality": "Movable"},
    {"name": "Vrishabha", "english": "Taurus", "lord": "Venus", "element": "Earth", "modality": "Fixed"},
    {"name": "Mithuna", "english": "Gemini", "lord": "Mercury", "element": "Air", "modality": "Dual"},
    {"name": "Karka", "english": "Cancer", "lord": "Moon", "element": "Water", "modality": "Movable"},
    {"name": "Simha", "english": "Leo", "lord": "Sun", "element": "Fire", "modality": "Fixed"},
    {"name": "Kanya", "english": "Virgo", "lord": "Mercury", "element": "Earth", "modality": "Dual"},
    {"name": "Tula", "english": "Libra", "lord": "Venus", "element": "Air", "modality": "Movable"},
    {"name": "Vrishchika", "english": "Scorpio", "lord": "Mars", "element": "Water", "modality": "Fixed"},
    {"name": "Dhanu", "english": "Sagittarius", "lord": "Jupiter", "element": "Fire", "modality": "Dual"},
    {"name": "Makara", "english": "Capricorn", "lord": "Saturn", "element": "Earth", "modality": "Movable"},
    {"name": "Kumbha", "english": "Aquarius", "lord": "Saturn", "element": "Air", "modality": "Fixed"},
    {"name": "Meena", "english": "Pisces", "lord": "Jupiter", "element": "Water", "modality": "Dual"},
)

NAKSHATRAS = (
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
)

DASHA_SEQUENCE = (
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
)

DASHA_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

YOGA_NAMES = (
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shula",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
)

TITHI_NAMES = (
    "Pratipada",
    "Dvitiya",
    "Tritiya",
    "Chaturthi",
    "Panchami",
    "Shashthi",
    "Saptami",
    "Ashtami",
    "Navami",
    "Dashami",
    "Ekadashi",
    "Dvadashi",
    "Trayodashi",
    "Chaturdashi",
    "Purnima",
)

WEEKDAYS = (
    ("Somavara", "Moon"),
    ("Mangalavara", "Mars"),
    ("Budhavara", "Mercury"),
    ("Guruvara", "Jupiter"),
    ("Shukravara", "Venus"),
    ("Shanivara", "Saturn"),
    ("Ravivara", "Sun"),
)

OWN_SIGNS = {
    "Sun": {4},
    "Moon": {3},
    "Mars": {0, 7},
    "Mercury": {2, 5},
    "Jupiter": {8, 11},
    "Venus": {1, 6},
    "Saturn": {9, 10},
}

EXALTATION_SIGNS = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 9,
    "Mercury": 5,
    "Jupiter": 3,
    "Venus": 11,
    "Saturn": 6,
}

QUESTION_DOMAINS = {
    "career": {
        "keywords": ("career", "job", "work", "business", "promotion", "profession", "office"),
        "houses": (2, 6, 10, 11),
        "grahas": ("Sun", "Mercury", "Jupiter", "Saturn"),
    },
    "relationships": {
        "keywords": ("relationship", "love", "marriage", "partner", "spouse", "dating", "romance"),
        "houses": (2, 5, 7, 8, 12),
        "grahas": ("Venus", "Jupiter", "Mars"),
    },
    "finance": {
        "keywords": ("money", "finance", "wealth", "income", "investment", "debt", "property"),
        "houses": (2, 5, 9, 11),
        "grahas": ("Mercury", "Jupiter", "Venus"),
    },
    "health": {
        "keywords": ("health", "illness", "disease", "surgery", "recovery", "wellbeing"),
        "houses": (1, 6, 8, 12),
        "grahas": ("Sun", "Moon", "Mars", "Saturn"),
    },
    "education": {
        "keywords": ("education", "study", "exam", "school", "college", "learn", "degree"),
        "houses": (2, 4, 5, 9),
        "grahas": ("Mercury", "Jupiter", "Moon"),
    },
    "home_and_family": {
        "keywords": ("home", "family", "mother", "father", "relocate", "house", "children"),
        "houses": (2, 4, 5, 9),
        "grahas": ("Moon", "Sun", "Jupiter", "Venus"),
    },
    "spirituality": {
        "keywords": ("spiritual", "purpose", "dharma", "meditation", "moksha", "religion"),
        "houses": (5, 8, 9, 12),
        "grahas": ("Jupiter", "Saturn", "Ketu"),
    },
}
