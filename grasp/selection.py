"""Capture the user's currently-selected text by synthesizing ⌘C.

Uses NSPasteboard.changeCount() rather than pyperclip — pyperclip shells out
to pbcopy/pbpaste which is far too slow for this polling loop and was the
reason selection capture appeared to silently fail.
"""

import time

from AppKit import NSPasteboard, NSPasteboardTypeString
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
)

CMD_C_KEYCODE = 8  # kVK_ANSI_C

# How long we'll wait for the synthesized ⌘C to actually update the
# pasteboard. Sluggish apps (heavy Electron windows, remote desktops) can
# take a surprising amount of time before the clipboard reflects the copy.
COPY_WAIT_TIMEOUT_S = 0.6
COPY_POLL_INTERVAL_S = 0.012


def _send_cmd_c() -> None:
    down = CGEventCreateKeyboardEvent(None, CMD_C_KEYCODE, True)
    up = CGEventCreateKeyboardEvent(None, CMD_C_KEYCODE, False)
    # Force ONLY Command — explicitly override any other modifier flags the
    # system thinks are held (e.g. Shift, if the user hasn't fully released
    # the ⌘⇧Space hotkey yet). Without this, some receiving apps see
    # ⌘⇧C and ignore it.
    CGEventSetFlags(down, kCGEventFlagMaskCommand)
    CGEventSetFlags(up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def get_selected_text():
    """Return the currently-highlighted text, or None if nothing is selected.

    Works for words, sentences, and full paragraphs — whatever ⌘C would copy.
    Restores the prior pasteboard string when done so we don't clobber the
    user's clipboard.
    """
    pb = NSPasteboard.generalPasteboard()
    initial_change_count = pb.changeCount()
    prior_text = pb.stringForType_(NSPasteboardTypeString)

    _send_cmd_c()

    # Wait for ⌘C to actually bump the pasteboard.
    deadline = time.monotonic() + COPY_WAIT_TIMEOUT_S
    while time.monotonic() < deadline:
        if pb.changeCount() != initial_change_count:
            break
        time.sleep(COPY_POLL_INTERVAL_S)

    if pb.changeCount() == initial_change_count:
        # Nothing was copied — either nothing was selected, or the focused
        # app refused ⌘C (password fields, some sandboxed apps).
        return None

    captured = pb.stringForType_(NSPasteboardTypeString)

    # Restore previous clipboard contents so we don't trample on the user.
    if prior_text is not None:
        pb.clearContents()
        pb.setString_forType_(prior_text, NSPasteboardTypeString)

    if captured is None:
        return None
    text = str(captured).strip()
    return text or None
