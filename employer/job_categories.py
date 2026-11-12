"""Job categories used for demand ranking (9.2) and benchmarks (9.4).

Keep the keys stable: they are stored in the database.
"""
import re

CATEGORY_CHOICES = [
    ("sales_retail", "Sales & Retail"),
    ("food_service", "Food Service"),
    ("office_admin", "Office & Administrative"),
    ("driving_delivery", "Driving & Delivery"),
    ("construction_trades", "Construction & Skilled Trades"),
    ("hospitality_tourism", "Hospitality & Tourism"),
    ("agriculture_fishery", "Agriculture & Fishery"),
    ("health_care", "Health & Care"),
    ("education", "Education & Training"),
    ("it_technical", "IT & Technical"),
    ("manufacturing", "Production & Manufacturing"),
    ("security", "Security Services"),
    ("cleaning_household", "Cleaning & Household"),
    ("other", "Other"),
]
CATEGORY_KEYS = {key for key, _ in CATEGORY_CHOICES}
CATEGORY_LABELS = dict(CATEGORY_CHOICES)

# Title keywords used to suggest a category (first match wins, so the
# more specific groups come first).
KEYWORDS = [
    ("driving_delivery", ["driver", "delivery", "rider", "courier", "dispatcher", "logistics"]),
    ("food_service", ["cook", "chef", "kitchen", "food", "baker", "barista", "waiter", "waitress", "server", "crew", "dishwasher", "canteen", "restaurant"]),
    ("sales_retail", ["sales", "cashier", "store", "merchandiser", "promodiser", "retail", "shop", "minimart", "vendor", "agent", "refilling", "meat shop"]),
    ("office_admin", ["clerk", "admin", "secretary", "encoder", "bookkeeper", "accounting", "accountant", "office", "receptionist", "assistant", "data entry", "hr"]),
    ("construction_trades", ["carpenter", "mason", "welder", "electrician", "plumber", "construction", "laborer", "painter", "mechanic", "technician"]),
    ("hospitality_tourism", ["hotel", "resort", "housekeeper", "front desk", "tour", "bartender", "lifeguard"]),
    ("agriculture_fishery", ["farm", "fisher", "agri", "harvest", "planter", "livestock", "poultry"]),
    ("health_care", ["nurse", "caregiver", "midwife", "pharmacy", "health", "medical", "therapist"]),
    ("education", ["teacher", "tutor", "instructor", "trainer", "school"]),
    ("it_technical", ["programmer", "developer", "it ", "computer", "web", "software", "graphic"]),
    ("manufacturing", ["production", "factory", "machine operator", "packer", "assembler"]),
    ("security", ["security", "guard", "watchman"]),
    ("cleaning_household", ["cleaner", "janitor", "utility", "housemaid", "laundry", "household", "maintenance"]),
]


def guess_category(title):
    """Suggest a category from a job title; 'other' when nothing matches."""
    text = " " + re.sub(r"\s+", " ", (title or "").lower()) + " "
    for key, words in KEYWORDS:
        if any(re.search(r"(?<![a-z])" + re.escape(word.strip()) + r"(?![a-z])", text) for word in words):
            return key
    return "other"
