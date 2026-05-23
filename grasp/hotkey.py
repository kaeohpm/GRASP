"""Two global hotkeys via NSEvent monitors, configurable at runtime.

- toggle — show/hide the side panel
- grab   — grab the currently-highlighted text and ask Claude to explain it

Requires Accessibility permission for global key events.
"""

from AppKit import (
    NSEvent,
    NSEventMaskKeyDown,
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagDeviceIndependentFlagsMask,
    NSEventModifierFlagOption,
    NSEventModifierFlagShift,
)

from . import settings

KC_ESCAPE = 53

_MOD_MASK = (
    NSEventModifierFlagCommand
    | NSEventModifierFlagShift
    | NSEventModifierFlagOption
    | NSEventModifierFlagControl
)

_monitors = []
_routes = {}            # name -> callback
_bindings = {}          # name -> (modifiers, keycode)
_recording = None       # None, or {"callback": fn}


def _binding_for(event):
    flags = event.modifierFlags() & NSEventModifierFlagDeviceIndependentFlagsMask
    mods = flags & _MOD_MASK
    kc = event.keyCode()
    for name, (m, k) in _bindings.items():
        if m == mods and k == kc:
            return name
    return None


def _capture(event):
    """Build (modifiers, keycode, char) from a key-down event."""
    flags = event.modifierFlags() & NSEventModifierFlagDeviceIndependentFlagsMask
    mods = int(flags & _MOD_MASK)
    kc = int(event.keyCode())
    chars = event.charactersIgnoringModifiers() or ""
    if chars in ("", " "):
        char = "Space" if kc == 49 else f"#{kc}"
    else:
        char = chars.upper() if len(chars) == 1 and chars.isalpha() else chars
    return mods, kc, char


def start_hotkeys(on_toggle, on_grab):
    """Install global + local NSEvent monitors. Returns immediately."""
    _routes["toggle"] = on_toggle
    _routes["grab"] = on_grab

    for name in ("toggle", "grab"):
        mods, kc, _ = settings.get_hotkey(name)
        _bindings[name] = (int(mods), int(kc))

    def global_handler(event):
        if _recording is not None:
            return
        name = _binding_for(event)
        if name is not None:
            _routes[name]()

    def local_handler(event):
        if _recording is not None:
            if event.keyCode() == KC_ESCAPE:
                cb = _recording["callback"]
                cancel_recording()
                cb(None, None, None)
                return None
            mods, kc, char = _capture(event)
            # Require at least one modifier so plain letters don't bind by accident.
            if mods == 0:
                return None
            cb = _recording["callback"]
            cancel_recording()
            cb(mods, kc, char)
            return None
        name = _binding_for(event)
        if name is not None:
            _routes[name]()
            return None  # swallow inside our own app
        return event

    g = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
        NSEventMaskKeyDown, global_handler
    )
    l = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
        NSEventMaskKeyDown, local_handler
    )
    _monitors.append(g)
    _monitors.append(l)


def rebind(name: str, modifiers: int, keycode: int):
    _bindings[name] = (int(modifiers), int(keycode))


def start_recording(callback):
    """Capture the next modifier+key combo pressed inside the app.

    callback(modifiers, keycode, char) fires on capture.
    callback(None, None, None) fires on Escape (cancel).
    """
    global _recording
    _recording = {"callback": callback}


def cancel_recording():
    global _recording
    _recording = None
