DEFAULT_CURRENCY = "UGX"

SUPPORTED_CURRENCIES = (
    "UGX",
    "KES",
    "TZS",
    "RWF",
    "SSP",
    "USD",
    "GBP",
    "EUR",
)

SUPPORTED_ID_DOCUMENT_TYPES = (
    "national_id",
    "passport",
    "refugee_id",
    "other",
)

SUPPORTED_PROPERTY_TYPES = (
    "apartment",
    "hostel",
    "shops",
    "residential",
    "commercial",
    "office",
    "warehouse",
    "mixed_use",
    "student_housing",
)


def sql_allowed_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)
