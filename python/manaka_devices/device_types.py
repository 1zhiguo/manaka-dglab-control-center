"""V4 APP hardware roles; hardware generation is not a Socket version."""

COYOTE_TYPES = frozenset({"COYOTE_020", "COYOTE_030"})
OVC_TYPES = frozenset({"OVC_1"})
SUPPORTED_V4_TYPES = COYOTE_TYPES | OVC_TYPES
DEVICE_NAMES = {
    "COYOTE_020": "郊狼 2.0",
    "COYOTE_030": "郊狼 3.0",
    "OVC_1": "负鼠",
}
