"""User-tunable preferences persisted to NSUserDefaults."""

from AppKit import (
    NSColor,
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagOption,
    NSEventModifierFlagShift,
    NSUserDefaults,
)

# Virtual keycodes
KC_SPACE = 49
KC_G = 5

DEFAULTS = {
    "grasp.toggle.modifiers": int(
        NSEventModifierFlagCommand | NSEventModifierFlagShift
    ),
    "grasp.toggle.keycode": KC_SPACE,
    "grasp.toggle.display": "⌘⇧Space",
    "grasp.grab.modifiers": int(
        NSEventModifierFlagCommand | NSEventModifierFlagShift
    ),
    "grasp.grab.keycode": KC_G,
    "grasp.grab.display": "⌘⇧G",
    "grasp.bg.r": 0.07,
    "grasp.bg.g": 0.08,
    "grasp.bg.b": 0.10,
    "grasp.opacity": 0.5,
    "grasp.font_size": 13.0,
    "grasp.text_color": "white",
}


def _d():
    return NSUserDefaults.standardUserDefaults()


def _get(key):
    d = _d()
    if d.objectForKey_(key) is None:
        return DEFAULTS[key]
    default = DEFAULTS[key]
    if isinstance(default, int):
        return int(d.integerForKey_(key))
    if isinstance(default, float):
        return float(d.doubleForKey_(key))
    return str(d.stringForKey_(key))


def _set(key, value):
    d = _d()
    default = DEFAULTS[key]
    if isinstance(default, int):
        d.setInteger_forKey_(int(value), key)
    elif isinstance(default, float):
        d.setDouble_forKey_(float(value), key)
    else:
        d.setObject_forKey_(str(value), key)


def get_hotkey(name: str):
    """Return (modifiers, keycode, display) for 'toggle' or 'grab'."""
    return (
        _get(f"grasp.{name}.modifiers"),
        _get(f"grasp.{name}.keycode"),
        _get(f"grasp.{name}.display"),
    )


def set_hotkey(name: str, modifiers: int, keycode: int, display: str):
    _set(f"grasp.{name}.modifiers", modifiers)
    _set(f"grasp.{name}.keycode", keycode)
    _set(f"grasp.{name}.display", display)


def get_background_color() -> NSColor:
    r = _get("grasp.bg.r")
    g = _get("grasp.bg.g")
    b = _get("grasp.bg.b")
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)


def set_background_color(color: NSColor):
    rgb = color.colorUsingColorSpaceName_("NSCalibratedRGBColorSpace") or color
    _set("grasp.bg.r", float(rgb.redComponent()))
    _set("grasp.bg.g", float(rgb.greenComponent()))
    _set("grasp.bg.b", float(rgb.blueComponent()))


def get_opacity() -> float:
    return float(_get("grasp.opacity"))


def set_opacity(value: float):
    _set("grasp.opacity", value)


def get_font_size() -> float:
    return float(_get("grasp.font_size"))


def set_font_size(value: float):
    _set("grasp.font_size", value)


def get_text_color() -> str:
    return _get("grasp.text_color")


def set_text_color(value: str):
    _set("grasp.text_color", value)


def text_ns_color() -> NSColor:
    return (
        NSColor.blackColor()
        if get_text_color() == "black"
        else NSColor.whiteColor()
    )


def muted_text_color(alpha: float) -> NSColor:
    base = 0.0 if get_text_color() == "black" else 1.0
    return NSColor.colorWithWhite_alpha_(base, alpha)


def format_hotkey(modifiers: int, key_char: str) -> str:
    parts = []
    if modifiers & NSEventModifierFlagControl:
        parts.append("⌃")
    if modifiers & NSEventModifierFlagOption:
        parts.append("⌥")
    if modifiers & NSEventModifierFlagShift:
        parts.append("⇧")
    if modifiers & NSEventModifierFlagCommand:
        parts.append("⌘")
    parts.append(key_char)
    return "".join(parts)
