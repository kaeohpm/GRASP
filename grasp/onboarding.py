"""First-launch window for collecting the Anthropic API key."""

import objc
from AppKit import (
    NSApp,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSButton,
    NSColor,
    NSFont,
    NSScreen,
    NSSecureTextField,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSMakeRect, NSObject

# Keep delegate refs alive so they aren't garbage-collected.
_alive = []


class _OnboardingDelegate(NSObject):
    def initWithCallback_(self, callback):
        self = objc.super(_OnboardingDelegate, self).init()
        if self is None:
            return None
        self._callback = callback
        self.window = None
        self.text_field = None
        self.error_label = None
        return self

    def saveKey_(self, sender):
        raw = self.text_field.stringValue() or ""
        key = raw.strip()
        if not key:
            self.error_label.setStringValue_("Please paste an API key.")
            return
        if not key.startswith("sk-"):
            self.error_label.setStringValue_(
                "That doesn't look like an Anthropic key (should start with sk-)."
            )
            return
        self.error_label.setStringValue_("")
        try:
            self._callback(key)
        finally:
            if self.window is not None:
                self.window.close()
            try:
                _alive.remove(self)
            except ValueError:
                pass

    def windowWillClose_(self, notification):
        try:
            _alive.remove(self)
        except ValueError:
            pass


def show_onboarding(callback):
    """Show the API-key window. Calls callback(key) once the user saves."""

    width, height = 480, 260
    screen = NSScreen.mainScreen()
    if screen is not None:
        sf = screen.visibleFrame()
        x = sf.origin.x + (sf.size.width - width) / 2
        y = sf.origin.y + (sf.size.height - height) / 2 + 80
    else:
        x, y = 200, 400

    style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(x, y, width, height), style, NSBackingStoreBuffered, False
    )
    window.setTitle_("Welcome to Grasp")
    window.setReleasedWhenClosed_(False)

    content = window.contentView()

    title = NSTextField.alloc().initWithFrame_(NSMakeRect(24, height - 64, width - 48, 30))
    title.setStringValue_("Welcome to Grasp")
    title.setFont_(NSFont.boldSystemFontOfSize_(22))
    title.setBezeled_(False)
    title.setDrawsBackground_(False)
    title.setEditable_(False)
    title.setSelectable_(False)
    content.addSubview_(title)

    desc = NSTextField.alloc().initWithFrame_(NSMakeRect(24, height - 110, width - 48, 40))
    desc.setStringValue_(
        "Paste your Anthropic API key. It will be stored securely in the "
        "macOS Keychain — you'll only enter it once."
    )
    desc.setFont_(NSFont.systemFontOfSize_(12))
    desc.setTextColor_(NSColor.secondaryLabelColor())
    desc.setBezeled_(False)
    desc.setDrawsBackground_(False)
    desc.setEditable_(False)
    desc.setSelectable_(False)
    desc.cell().setWraps_(True)
    content.addSubview_(desc)

    text_field = NSSecureTextField.alloc().initWithFrame_(
        NSMakeRect(24, height - 160, width - 48, 28)
    )
    text_field.setPlaceholderString_("sk-ant-…")
    text_field.setFont_(NSFont.systemFontOfSize_(13))
    content.addSubview_(text_field)

    error_label = NSTextField.alloc().initWithFrame_(NSMakeRect(24, 70, width - 48, 20))
    error_label.setStringValue_("")
    error_label.setFont_(NSFont.systemFontOfSize_(11))
    error_label.setTextColor_(NSColor.systemRedColor())
    error_label.setBezeled_(False)
    error_label.setDrawsBackground_(False)
    error_label.setEditable_(False)
    error_label.setSelectable_(False)
    content.addSubview_(error_label)

    save_btn = NSButton.alloc().initWithFrame_(NSMakeRect(width - 24 - 110, 24, 110, 32))
    save_btn.setTitle_("Save & Continue")
    save_btn.setBezelStyle_(NSBezelStyleRounded)
    save_btn.setKeyEquivalent_("\r")
    content.addSubview_(save_btn)

    hint = NSTextField.alloc().initWithFrame_(NSMakeRect(24, 28, width - 160, 20))
    hint.setStringValue_("Get a key at console.anthropic.com")
    hint.setFont_(NSFont.systemFontOfSize_(11))
    hint.setTextColor_(NSColor.tertiaryLabelColor())
    hint.setBezeled_(False)
    hint.setDrawsBackground_(False)
    hint.setEditable_(False)
    hint.setSelectable_(True)
    content.addSubview_(hint)

    delegate = _OnboardingDelegate.alloc().initWithCallback_(callback)
    delegate.window = window
    delegate.text_field = text_field
    delegate.error_label = error_label
    save_btn.setTarget_(delegate)
    save_btn.setAction_(b"saveKey:")
    window.setDelegate_(delegate)
    _alive.append(delegate)

    NSApp.activateIgnoringOtherApps_(True)
    window.makeKeyAndOrderFront_(None)
    window.makeFirstResponder_(text_field)
    return window
