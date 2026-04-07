# -*- coding: utf-8 -*-

ATTR_PREFIX = "lm__"


def attr_name(group_name):
    safe = group_name.replace(" ", "_").replace(".", "_")
    return f"{ATTR_PREFIX}{safe}"


# --- Color palettes (RGBA 0-1) ---

_CYAN = (0.0, 0.85, 0.9, 1.0)
_MAGENTA = (0.9, 0.2, 0.7, 1.0)
_YELLOW = (0.95, 0.85, 0.1, 1.0)
_GREEN = (0.2, 0.9, 0.3, 1.0)
_ORANGE = (1.0, 0.55, 0.1, 1.0)
_BLUE = (0.2, 0.45, 1.0, 1.0)
_RED = (1.0, 0.25, 0.25, 1.0)
_PINK = (1.0, 0.5, 0.7, 1.0)
_LIME = (0.6, 1.0, 0.2, 1.0)
_PURPLE = (0.65, 0.3, 1.0, 1.0)
_TEAL = (0.0, 0.7, 0.65, 1.0)
_GOLD = (0.85, 0.7, 0.2, 1.0)
_SKY = (0.3, 0.75, 1.0, 1.0)
_CORAL = (1.0, 0.45, 0.4, 1.0)
_MINT = (0.4, 0.95, 0.7, 1.0)
_LAVENDER = (0.7, 0.5, 1.0, 1.0)
_WHITE = (0.9, 0.9, 0.9, 1.0)
_PEACH = (1.0, 0.7, 0.5, 1.0)

# --- Facial landmark definitions ---

FACIAL_LANDMARKS = [
    ("Eyebrow Line", _CYAN),
    ("Eyelid Line", _MAGENTA),
    ("EyelidOut Line", _PURPLE),
    ("Cheek Line", _PEACH),
    ("Nose", _ORANGE),
    ("Smile Lines", _PINK),
    ("Lip Outline", _RED),
    ("Lip InLine", _CORAL),
    ("Lip Corner", _GOLD),
    ("Jaw Line", _YELLOW),
    ("Ear Line", _TEAL),
    ("Hair Line", _GREEN),
]

# --- Body landmark definitions ---

BODY_LANDMARKS = [
    ("Pelvis Line", _BLUE),
    ("Spine Line", _SKY),
    ("Chest Line", _TEAL),
    ("Neck Line", _MINT),
    ("Head Line", _LAVENDER),
    ("Clavicle Line", _GOLD),
    ("Shoulder Line", _ORANGE),
    ("Elbow Line", _YELLOW),
    ("Wrist Line", _LIME),
    ("Thigh Line", _GREEN),
    ("Knee Line", _CYAN),
    ("Ankle Line", _MAGENTA),
    ("Ball Line", _PURPLE),
]

# Finger/Toe definitions: (display_name, range_start, range_end, default_color)
# Thumb uses 01-03, others use 00-03
FINGER_LANDMARKS = [
    ("Thumb", 1, 3, _RED),
    ("Index", 0, 3, _ORANGE),
    ("Middle", 0, 3, _YELLOW),
    ("Ring", 0, 3, _GREEN),
    ("Pinky", 0, 3, _CYAN),
]

DEFAULT_CUSTOM_COLOR = _WHITE
