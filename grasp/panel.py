"""The Grasp floating side panel — history view + inline settings view."""

import objc
from AppKit import (
    NSAttributedString,
    NSBackingStoreBuffered,
    NSBezelStyleInline,
    NSBezelStyleRounded,
    NSButton,
    NSColor,
    NSColorPanel,
    NSColorPanelModeWheel,
    NSFocusRingTypeNone,
    NSFont,
    NSFontAttributeName,
    NSFontWeightUltraLight,
    NSForegroundColorAttributeName,
    NSKernAttributeName,
    NSLineBreakByWordWrapping,
    NSNoBorder,
    NSPanel,
    NSPasteboard,
    NSPasteboardTypeString,
    NSScreen,
    NSScrollView,
    NSSegmentedControl,
    NSSegmentStyleRounded,
    NSSlider,
    NSStringDrawingUsesFontLeading,
    NSStringDrawingUsesLineFragmentOrigin,
    NSTextAlignmentCenter,
    NSTextAlignmentRight,
    NSTextField,
    NSTextFieldRoundedBezel,
    NSView,
    NSViewHeightSizable,
    NSViewMaxYMargin,
    NSViewMinYMargin,
    NSViewWidthSizable,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
    NSWindowStyleMaskResizable,
    NSFloatingWindowLevel,
)
from Foundation import (
    NSMakePoint,
    NSMakeRect,
    NSMakeSize,
    NSObject,
    NSString,
)

from . import hotkey, settings

PANEL_WIDTH = 380
MIN_FONT_SIZE = 10.0
MAX_FONT_SIZE = 20.0
HEADER_HEIGHT = 56  # GRASP + breathing room

PRESETS = [
    ("White",      1.00, 1.00, 1.00),
    ("Light gray", 0.85, 0.85, 0.85),
    ("Beige",      0.95, 0.90, 0.80),
    ("Dark navy",  0.05, 0.10, 0.25),
    ("Black",      0.02, 0.02, 0.02),
    ("Slate",      0.25, 0.30, 0.35),
    ("Sage",       0.55, 0.65, 0.55),
    ("Terracotta", 0.75, 0.40, 0.30),
]


class _FlippedView(NSView):
    def isFlipped(self):
        return True


class _PresetSwatch(NSView):
    def initWithFrame_color_index_panel_(self, frame, color, index, panel):
        self = objc.super(_PresetSwatch, self).initWithFrame_(frame)
        if self is None:
            return None
        self._idx = index
        self._panel = panel
        self.setWantsLayer_(True)
        self.layer().setBackgroundColor_(color.CGColor())
        self.layer().setCornerRadius_(frame.size.height / 2.0)
        self.layer().setBorderWidth_(1.0)
        self.layer().setBorderColor_(settings.muted_text_color(0.30).CGColor())
        return self

    def mouseDown_(self, _event):
        self._panel._apply_preset(self._idx)


class _GraspNSPanel(NSPanel):
    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False


def _measure_text_height(text: str, font, width: float) -> float:
    if not text:
        return 18.0
    ns = NSString.stringWithString_(text)
    rect = ns.boundingRectWithSize_options_attributes_(
        NSMakeSize(width, 100000),
        NSStringDrawingUsesLineFragmentOrigin | NSStringDrawingUsesFontLeading,
        {NSFontAttributeName: font},
    )
    return float(rect.size.height) + 2.0


def _section_label(text: str, frame) -> NSTextField:
    f = NSTextField.alloc().initWithFrame_(frame)
    f.setStringValue_(text.upper())
    font = NSFont.systemFontOfSize_weight_(9.5, NSFontWeightUltraLight)
    attrs = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: settings.muted_text_color(0.50),
        NSKernAttributeName: 2.0,
    }
    f.setAttributedStringValue_(
        NSAttributedString.alloc().initWithString_attributes_(text.upper(), attrs)
    )
    f.setBezeled_(False)
    f.setDrawsBackground_(False)
    f.setEditable_(False)
    f.setSelectable_(False)
    return f


def _plain_label(text: str, frame, *, size=12.0, alpha=0.85) -> NSTextField:
    f = NSTextField.alloc().initWithFrame_(frame)
    f.setStringValue_(text)
    f.setFont_(NSFont.systemFontOfSize_(size))
    f.setTextColor_(settings.muted_text_color(alpha))
    f.setBezeled_(False)
    f.setDrawsBackground_(False)
    f.setEditable_(False)
    f.setSelectable_(False)
    return f


class GraspPanel(NSObject):
    def initWithController_(self, controller):
        self = objc.super(GraspPanel, self).init()
        if self is None:
            return None
        self.controller = controller
        self.entries = []
        self.font_size = settings.get_font_size()
        self.mode = "history"
        self._next_id = 0
        self._button_map = {}
        self._hotkey_buttons = {}  # name -> NSButton
        self._build_window()
        return self

    # ------------------------------------------------------------------ build

    def _build_window(self):
        screen = NSScreen.mainScreen()
        if screen is None:
            sf_origin = NSMakePoint(0, 0)
            sf_w, sf_h = 1440.0, 900.0
        else:
            sf = screen.visibleFrame()
            sf_origin = sf.origin
            sf_w = sf.size.width
            sf_h = sf.size.height

        height = sf_h - 40
        x = sf_origin.x + sf_w - PANEL_WIDTH - 16
        y = sf_origin.y + 20
        rect = NSMakeRect(x, y, PANEL_WIDTH, height)

        style = (
            NSWindowStyleMaskBorderless
            | NSWindowStyleMaskNonactivatingPanel
            | NSWindowStyleMaskResizable
        )
        window = _GraspNSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, NSBackingStoreBuffered, False
        )
        window.setLevel_(NSFloatingWindowLevel)
        window.setOpaque_(False)
        window.setBackgroundColor_(NSColor.clearColor())
        window.setHasShadow_(True)
        window.setMovableByWindowBackground_(True)
        window.setHidesOnDeactivate_(False)
        window.setReleasedWhenClosed_(False)
        window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
        )

        content = window.contentView()
        content.setWantsLayer_(True)
        content.layer().setCornerRadius_(14.0)
        content.layer().setMasksToBounds_(True)
        content.setAutoresizesSubviews_(True)

        self.window = window
        self.content_view = content
        self._apply_background()
        self._build_content_subviews()

    def _build_content_subviews(self):
        for sv in list(self.content_view.subviews()):
            sv.removeFromSuperview()

        self._build_header(self.content_view)

        ch = self.content_view.frame().size.height
        body_rect = NSMakeRect(0, 0, PANEL_WIDTH, ch - HEADER_HEIGHT)

        self.history_view = _FlippedView.alloc().initWithFrame_(body_rect)
        self.history_view.setAutoresizingMask_(
            NSViewWidthSizable | NSViewHeightSizable
        )
        self._build_history_view(self.history_view)
        self.content_view.addSubview_(self.history_view)

        self.settings_view = _FlippedView.alloc().initWithFrame_(body_rect)
        self.settings_view.setAutoresizingMask_(
            NSViewWidthSizable | NSViewHeightSizable
        )
        self._build_settings_view(self.settings_view)
        self.content_view.addSubview_(self.settings_view)

        self._update_mode()
        if getattr(self, "doc_view", None) is not None:
            self._rebuild()

    def _build_header(self, container):
        ch = container.frame().size.height
        header_y = ch - HEADER_HEIGHT
        header_frame = NSMakeRect(0, header_y, PANEL_WIDTH, HEADER_HEIGHT)
        header_bg = NSView.alloc().initWithFrame_(header_frame)
        header_bg.setAutoresizingMask_(NSViewMinYMargin | NSViewWidthSizable)

        # GRASP wordmark
        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, 12, PANEL_WIDTH - 80, 32)
        )
        title_font = NSFont.systemFontOfSize_weight_(28, NSFontWeightUltraLight)
        attrs = {
            NSFontAttributeName: title_font,
            NSForegroundColorAttributeName: settings.text_ns_color(),
            NSKernAttributeName: 6.0,
        }
        title.setAttributedStringValue_(
            NSAttributedString.alloc().initWithString_attributes_("GRASP", attrs)
        )
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setEditable_(False)
        title.setSelectable_(False)
        title.setAutoresizingMask_(NSViewWidthSizable)
        header_bg.addSubview_(title)

        # Gear button (top-right)
        gear = NSButton.alloc().initWithFrame_(
            NSMakeRect(PANEL_WIDTH - 44, 16, 28, 24)
        )
        gear.setTitle_("⚙")
        gear.setFont_(NSFont.systemFontOfSize_(16))
        gear.setBezelStyle_(NSBezelStyleInline)
        gear.setBordered_(False)
        gear.setTarget_(self)
        gear.setAction_(b"toggleMode:")
        gear.setToolTip_("Settings")
        gear.setAutoresizingMask_(NSViewMinYMargin)
        header_bg.addSubview_(gear)
        self.gear_button = gear

        container.addSubview_(header_bg)

    # ------------------------------------------------------------ history view

    def _build_history_view(self, container):
        w = PANEL_WIDTH
        h = container.frame().size.height

        ctx_h = 26
        ctx_y = 12
        self.context_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(16, ctx_y, w - 32, ctx_h)
        )
        self.context_field.setPlaceholderString_(
            "Context (e.g. DJ, legal, coding) — optional"
        )
        self.context_field.setFont_(NSFont.systemFontOfSize_(12))
        self.context_field.setBezelStyle_(NSTextFieldRoundedBezel)
        self.context_field.setFocusRingType_(NSFocusRingTypeNone)
        self.context_field.setTextColor_(settings.text_ns_color())
        self.context_field.setAutoresizingMask_(NSViewWidthSizable)
        container.addSubview_(self.context_field)

        counter_h = 22
        self.counter_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(16, h - counter_h - 8, w - 32, counter_h)
        )
        self.counter_label.setStringValue_("0 lookups this session")
        self.counter_label.setFont_(NSFont.systemFontOfSize_(10))
        self.counter_label.setTextColor_(settings.muted_text_color(0.45))
        self.counter_label.setAlignment_(NSTextAlignmentCenter)
        self.counter_label.setBezeled_(False)
        self.counter_label.setDrawsBackground_(False)
        self.counter_label.setEditable_(False)
        self.counter_label.setSelectable_(False)
        self.counter_label.setAutoresizingMask_(
            NSViewMinYMargin | NSViewWidthSizable
        )
        container.addSubview_(self.counter_label)

        scroll_top = ctx_y + ctx_h + 10
        scroll_bottom = counter_h + 14
        scroll_h = h - scroll_top - scroll_bottom
        self.scroll_view = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(8, scroll_top, w - 16, scroll_h)
        )
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setHasHorizontalScroller_(False)
        self.scroll_view.setBorderType_(NSNoBorder)
        self.scroll_view.setDrawsBackground_(False)
        self.scroll_view.setAutoresizingMask_(
            NSViewWidthSizable | NSViewHeightSizable
        )

        content_size = self.scroll_view.contentSize()
        self.doc_view = _FlippedView.alloc().initWithFrame_(
            NSMakeRect(0, 0, content_size.width, content_size.height)
        )
        self.doc_view.setAutoresizesSubviews_(False)
        self.scroll_view.setDocumentView_(self.doc_view)
        container.addSubview_(self.scroll_view)

        self.empty_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, 20, content_size.width - 40, 40)
        )
        self.empty_label.setFont_(NSFont.systemFontOfSize_(11))
        self.empty_label.setTextColor_(settings.muted_text_color(0.5))
        self.empty_label.setBezeled_(False)
        self.empty_label.setDrawsBackground_(False)
        self.empty_label.setEditable_(False)
        self.empty_label.setSelectable_(False)
        self.empty_label.cell().setWraps_(True)
        self._refresh_empty_label()
        self.doc_view.addSubview_(self.empty_label)

    def _refresh_empty_label(self):
        toggle = settings.get_hotkey("toggle")[2]
        grab = settings.get_hotkey("grab")[2]
        self.empty_label.setStringValue_(
            f"Highlight text anywhere and press {grab} to explain it.\n"
            f"{toggle} toggles this panel."
        )

    # ----------------------------------------------------------- settings view

    def _build_settings_view(self, container):
        w = PANEL_WIDTH
        x = 20
        col_w = w - 40
        y = 14

        # Hotkeys
        container.addSubview_(_section_label("Hotkeys", NSMakeRect(x, y, col_w, 14)))
        y += 22

        y = self._add_hotkey_row(container, "toggle", "Toggle panel", x, y, col_w)
        y = self._add_hotkey_row(container, "grab", "Grab selection", x, y, col_w)
        y += 8

        # Appearance
        container.addSubview_(_section_label("Appearance", NSMakeRect(x, y, col_w, 14)))
        y += 22

        # Preset swatches
        container.addSubview_(
            _plain_label("Presets", NSMakeRect(x, y + 2, 70, 18))
        )
        sw_size = 22
        sw_gap = 6
        preset_origin_x = x + 80
        for i, (name, r, g, b) in enumerate(PRESETS):
            color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)
            sw = _PresetSwatch.alloc().initWithFrame_color_index_panel_(
                NSMakeRect(
                    preset_origin_x + i * (sw_size + sw_gap), y, sw_size, sw_size
                ),
                color,
                i,
                self,
            )
            sw.setToolTip_(name)
            container.addSubview_(sw)
        y += 34

        # Background color
        container.addSubview_(
            _plain_label("Background", NSMakeRect(x, y + 6, 110, 18))
        )
        swatch = NSView.alloc().initWithFrame_(
            NSMakeRect(x + col_w - 122, y + 2, 26, 22)
        )
        swatch.setWantsLayer_(True)
        swatch.layer().setCornerRadius_(4.0)
        swatch.layer().setBorderWidth_(1.0)
        swatch.layer().setBorderColor_(settings.muted_text_color(0.30).CGColor())
        container.addSubview_(swatch)
        self.color_swatch = swatch
        self._refresh_color_swatch()

        choose_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(x + col_w - 88, y, 88, 26)
        )
        choose_btn.setTitle_("Choose…")
        choose_btn.setBezelStyle_(NSBezelStyleRounded)
        choose_btn.setFont_(NSFont.systemFontOfSize_(12))
        choose_btn.setTarget_(self)
        choose_btn.setAction_(b"chooseColor:")
        container.addSubview_(choose_btn)
        y += 36

        # Text color
        container.addSubview_(
            _plain_label("Text color", NSMakeRect(x, y + 4, 110, 18))
        )
        text_seg = NSSegmentedControl.alloc().initWithFrame_(
            NSMakeRect(x + col_w - 140, y, 140, 24)
        )
        text_seg.setSegmentCount_(2)
        text_seg.setLabel_forSegment_("White", 0)
        text_seg.setLabel_forSegment_("Black", 1)
        text_seg.setSegmentStyle_(NSSegmentStyleRounded)
        text_seg.setSelectedSegment_(
            0 if settings.get_text_color() == "white" else 1
        )
        text_seg.setTarget_(self)
        text_seg.setAction_(b"textColorChanged:")
        container.addSubview_(text_seg)
        y += 32

        # Opacity slider
        container.addSubview_(
            _plain_label("Opacity", NSMakeRect(x, y, 80, 18))
        )
        self.opacity_slider = NSSlider.alloc().initWithFrame_(
            NSMakeRect(x + 90, y - 2, col_w - 90, 22)
        )
        self.opacity_slider.setMinValue_(0.15)
        self.opacity_slider.setMaxValue_(1.0)
        self.opacity_slider.setDoubleValue_(settings.get_opacity())
        self.opacity_slider.setContinuous_(True)
        self.opacity_slider.setTarget_(self)
        self.opacity_slider.setAction_(b"opacityChanged:")
        container.addSubview_(self.opacity_slider)
        y += 30

        # Font size slider
        container.addSubview_(_plain_label("Font size", NSMakeRect(x, y, 80, 18)))
        self.font_slider = NSSlider.alloc().initWithFrame_(
            NSMakeRect(x + 90, y - 2, col_w - 90, 22)
        )
        self.font_slider.setMinValue_(MIN_FONT_SIZE)
        self.font_slider.setMaxValue_(MAX_FONT_SIZE)
        self.font_slider.setDoubleValue_(self.font_size)
        self.font_slider.setContinuous_(True)
        self.font_slider.setTarget_(self)
        self.font_slider.setAction_(b"fontChanged:")
        container.addSubview_(self.font_slider)
        y += 36

        # History
        container.addSubview_(_section_label("History", NSMakeRect(x, y, col_w, 14)))
        y += 22

        clear_btn = NSButton.alloc().initWithFrame_(NSMakeRect(x, y, 130, 28))
        clear_btn.setTitle_("Clear history")
        clear_btn.setBezelStyle_(NSBezelStyleRounded)
        clear_btn.setTarget_(self)
        clear_btn.setAction_(b"clearHistory:")
        container.addSubview_(clear_btn)

    def _add_hotkey_row(self, container, name, label_text, x, y, col_w):
        container.addSubview_(
            _plain_label(label_text, NSMakeRect(x, y + 4, 160, 20))
        )
        _, _, display = settings.get_hotkey(name)
        btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(x + col_w - 120, y, 120, 26)
        )
        btn.setTitle_(display)
        btn.setBezelStyle_(NSBezelStyleRounded)
        btn.setFont_(NSFont.systemFontOfSize_(12))
        btn.setTarget_(self)
        btn.setAction_(b"recordHotkey:")
        btn.setTag_(0 if name == "toggle" else 1)
        container.addSubview_(btn)
        self._hotkey_buttons[name] = btn
        return y + 34

    # --------------------------------------------------------------- visibility

    def show(self):
        self.window.orderFront_(None)
        self.window.makeKeyWindow()

    def hide(self):
        self.window.orderOut_(None)

    def toggle(self):
        if self.window.isVisible():
            self.hide()
        else:
            self.show()

    def show_settings(self):
        self.mode = "settings"
        self._update_mode()
        self.show()

    def toggleMode_(self, _sender):
        self.mode = "settings" if self.mode == "history" else "history"
        self._update_mode()

    def _update_mode(self):
        in_settings = self.mode == "settings"
        self.history_view.setHidden_(in_settings)
        self.settings_view.setHidden_(not in_settings)
        self.gear_button.setToolTip_("Back" if in_settings else "Settings")

    # -------------------------------------------------------------------- API

    def get_context(self) -> str:
        return str(self.context_field.stringValue() or "").strip()

    def set_query_count(self, n: int):
        suffix = "lookup" if n == 1 else "lookups"
        self.counter_label.setStringValue_(f"{n} {suffix} this session")

    def add_loading_entry(self, term: str):
        self._next_id += 1
        entry = {
            "id": self._next_id,
            "term": term,
            "explanation": "Thinking…",
            "pinned": False,
            "loading": True,
            "error": False,
            "followup": None,        # None | "loading" | "error" | "shown" | "hidden"
            "followup_text": None,
        }
        self.entries.append(entry)
        self._rebuild()
        return entry

    def update_entry(self, entry, explanation: str):
        entry["explanation"] = explanation
        entry["loading"] = False
        entry["error"] = False
        self._rebuild()

    def update_entry_error(self, entry, _err_msg: str):
        entry["explanation"] = (
            "Could not connect — check your API key or internet connection."
        )
        entry["loading"] = False
        entry["error"] = True
        self._rebuild()

    def set_followup_loading(self, entry):
        entry["followup"] = "loading"
        self._rebuild()

    def set_followup(self, entry, text: str):
        entry["followup"] = "shown"
        entry["followup_text"] = text
        self._rebuild()

    def set_followup_error(self, entry, _err_msg: str):
        entry["followup"] = "error"
        self._rebuild()

    # --------------------------------------------------------- settings actions

    def fontChanged_(self, sender):
        self.font_size = float(sender.doubleValue())
        settings.set_font_size(self.font_size)
        self._rebuild()

    def opacityChanged_(self, sender):
        settings.set_opacity(float(sender.doubleValue()))
        self._apply_background()

    def chooseColor_(self, _sender):
        p = NSColorPanel.sharedColorPanel()
        p.setMode_(NSColorPanelModeWheel)
        p.setShowsAlpha_(False)
        p.setColor_(settings.get_background_color())
        p.setTarget_(self)
        p.setAction_(b"backgroundColorChanged:")
        p.makeKeyAndOrderFront_(None)

    def backgroundColorChanged_(self, sender):
        settings.set_background_color(sender.color())
        self._refresh_color_swatch()
        self._apply_background()

    def _refresh_color_swatch(self):
        if getattr(self, "color_swatch", None) is None:
            return
        self.color_swatch.layer().setBackgroundColor_(
            settings.get_background_color().CGColor()
        )

    def _apply_preset(self, idx: int):
        _name, r, g, b = PRESETS[idx]
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)
        settings.set_background_color(color)
        self._refresh_color_swatch()
        self._apply_background()

    def textColorChanged_(self, sender):
        idx = int(sender.selectedSegment())
        settings.set_text_color("white" if idx == 0 else "black")
        self._build_content_subviews()

    def clearHistory_(self, _sender):
        self.entries = []
        self._rebuild()

    def recordHotkey_(self, sender):
        name = "toggle" if int(sender.tag()) == 0 else "grab"
        original_title = sender.title()
        sender.setTitle_("Press keys…  (Esc to cancel)")

        def on_captured(mods, kc, char):
            if mods is None:
                sender.setTitle_(original_title)
                return
            display = settings.format_hotkey(mods, char)
            settings.set_hotkey(name, mods, kc, display)
            hotkey.rebind(name, mods, kc)
            sender.setTitle_(display)
            self._refresh_empty_label()

        hotkey.start_recording(on_captured)

    def _apply_background(self):
        color = settings.get_background_color()
        alpha = settings.get_opacity()
        rgba = NSColor.colorWithCalibratedRed_green_blue_alpha_(
            float(color.redComponent()),
            float(color.greenComponent()),
            float(color.blueComponent()),
            float(alpha),
        )
        self.content_view.layer().setBackgroundColor_(rgba.CGColor())

    # ------------------------------------------------------------- rendering

    def copyEntry_(self, sender):
        entry = self._button_map.get(int(sender.tag()))
        if not entry:
            return
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(entry["explanation"], NSPasteboardTypeString)
        sender.setTitle_("✓")
        sender.performSelector_withObject_afterDelay_(b"setTitle:", "Copy", 1.0)

    def pinEntry_(self, sender):
        entry = self._button_map.get(int(sender.tag()))
        if not entry:
            return
        entry["pinned"] = not entry.get("pinned", False)
        self._rebuild()

    def tellMore_(self, sender):
        entry = self._button_map.get(int(sender.tag()))
        if not entry:
            return
        state = entry.get("followup")
        if state in (None, "error"):
            self.controller.explain_more(entry)
        elif state == "shown":
            entry["followup"] = "hidden"
            self._rebuild()
        elif state == "hidden":
            entry["followup"] = "shown"
            self._rebuild()
        # "loading": ignore clicks

    def _rebuild(self):
        for sv in list(self.doc_view.subviews()):
            sv.removeFromSuperview()
        self._button_map.clear()

        content_size = self.scroll_view.contentSize()
        doc_w = content_size.width

        if not self.entries:
            self._refresh_empty_label()
            self.empty_label.setFrame_(NSMakeRect(20, 20, doc_w - 40, 50))
            self.doc_view.addSubview_(self.empty_label)
            self.doc_view.setFrame_(NSMakeRect(0, 0, doc_w, content_size.height))
            return

        pinned = [e for e in self.entries if e.get("pinned")]
        unpinned = [e for e in self.entries if not e.get("pinned")]
        ordered = list(reversed(pinned)) + list(reversed(unpinned))

        y = 8.0
        for entry in ordered:
            card = self._build_entry_card(entry, doc_w - 16)
            card_h = card.frame().size.height
            card.setFrame_(NSMakeRect(8, y, doc_w - 16, card_h))
            self.doc_view.addSubview_(card)
            y += card_h + 8

        total_h = max(y + 4, content_size.height)
        self.doc_view.setFrame_(NSMakeRect(0, 0, doc_w, total_h))
        clip = self.scroll_view.contentView()
        clip.scrollToPoint_(NSMakePoint(0, 0))
        self.scroll_view.reflectScrolledClipView_(clip)

    def _build_entry_card(self, entry, width: float):
        term = entry["term"]
        explanation = entry["explanation"]
        state = entry.get("followup")

        body_font = NSFont.systemFontOfSize_(self.font_size)
        term_font = NSFont.boldSystemFontOfSize_(self.font_size + 1)
        followup_font = NSFont.systemFontOfSize_(self.font_size)

        inner_w = width - 24

        display_term = term if len(term) < 120 else term[:117] + "…"

        term_height = max(
            22.0,
            _measure_text_height(display_term, term_font, inner_w - 76),
        )
        exp_height = _measure_text_height(explanation, body_font, inner_w)

        # Decide what the bottom of the card shows based on followup state.
        main_ready = not entry.get("loading") and not entry.get("error")
        followup_visible = False
        followup_text = ""
        followup_text_h = 0.0
        followup_is_dim = False
        btn_label = None
        if main_ready:
            if state is None:
                btn_label = "Tell me more"
            elif state == "loading":
                followup_visible = True
                followup_text = "Thinking…"
                followup_text_h = 18
                followup_is_dim = True
            elif state == "error":
                followup_visible = True
                followup_text = "Couldn't fetch more."
                followup_text_h = 18
                followup_is_dim = True
                btn_label = "Try again"
            elif state == "shown":
                followup_visible = True
                followup_text = entry.get("followup_text") or ""
                followup_text_h = _measure_text_height(
                    followup_text, followup_font, inner_w
                )
                btn_label = "Show less"
            elif state == "hidden":
                btn_label = "Show more"
        show_action_btn = btn_label is not None
        btn_h = 18 if show_action_btn else 0

        total_h = (
            10
            + term_height
            + 6
            + exp_height
            + (12 + followup_text_h if followup_visible else 0)
            + (6 + btn_h if show_action_btn else 0)
            + 12
        )

        card = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, total_h))
        card.setWantsLayer_(True)

        if entry.get("error"):
            bg = NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.42, 0.16, 0.18, 0.50
            )
        elif entry.get("pinned"):
            bg = NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.22, 0.30, 0.46, 0.55
            )
        else:
            bg = settings.muted_text_color(0.08)
        card.layer().setBackgroundColor_(bg.CGColor())
        card.layer().setCornerRadius_(10.0)

        term_y = total_h - 10 - term_height
        term_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(12, term_y, inner_w - 76, term_height)
        )
        term_field.setStringValue_(display_term)
        term_field.setFont_(term_font)
        term_field.setTextColor_(settings.text_ns_color())
        term_field.setBezeled_(False)
        term_field.setDrawsBackground_(False)
        term_field.setEditable_(False)
        term_field.setSelectable_(True)
        term_field.cell().setWraps_(True)
        term_field.cell().setLineBreakMode_(NSLineBreakByWordWrapping)
        card.addSubview_(term_field)

        btn_y = total_h - 10 - 20
        copy_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(width - 12 - 64, btn_y, 32, 20)
        )
        copy_btn.setTitle_("Copy")
        copy_btn.setBezelStyle_(NSBezelStyleInline)
        copy_btn.setFont_(NSFont.systemFontOfSize_(9))
        copy_btn.setTag_(entry["id"])
        copy_btn.setTarget_(self)
        copy_btn.setAction_(b"copyEntry:")
        copy_btn.setToolTip_("Copy explanation")
        card.addSubview_(copy_btn)

        pin_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(width - 12 - 30, btn_y, 28, 20)
        )
        pin_btn.setTitle_("Unpin" if entry.get("pinned") else "Pin")
        pin_btn.setBezelStyle_(NSBezelStyleInline)
        pin_btn.setFont_(NSFont.systemFontOfSize_(9))
        pin_btn.setTag_(entry["id"])
        pin_btn.setTarget_(self)
        pin_btn.setAction_(b"pinEntry:")
        pin_btn.setToolTip_("Keep this entry at the top")
        card.addSubview_(pin_btn)

        self._button_map[entry["id"]] = entry

        # Non-flipped card coords (Y grows upward). Place from the bottom up.
        y_cursor = 12  # bottom pad

        if show_action_btn:
            btn_y = y_cursor
            y_cursor += btn_h + 6

        if followup_visible:
            followup_y = y_cursor
            y_cursor += followup_text_h + 12

        y_exp = y_cursor

        exp_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(12, y_exp, inner_w, exp_height)
        )
        exp_field.setStringValue_(explanation)
        exp_field.setFont_(body_font)
        if entry.get("loading"):
            exp_field.setTextColor_(settings.muted_text_color(0.55))
        else:
            exp_field.setTextColor_(settings.muted_text_color(0.92))
        exp_field.setBezeled_(False)
        exp_field.setDrawsBackground_(False)
        exp_field.setEditable_(False)
        exp_field.setSelectable_(True)
        exp_field.cell().setWraps_(True)
        exp_field.cell().setScrollable_(False)
        exp_field.cell().setLineBreakMode_(NSLineBreakByWordWrapping)
        card.addSubview_(exp_field)

        if followup_visible:
            divider = NSView.alloc().initWithFrame_(
                NSMakeRect(12, y_exp - 6, inner_w, 1)
            )
            divider.setWantsLayer_(True)
            divider.layer().setBackgroundColor_(
                settings.muted_text_color(0.18).CGColor()
            )
            card.addSubview_(divider)

            followup_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(12, followup_y, inner_w, followup_text_h)
            )
            followup_field.setStringValue_(followup_text)
            followup_field.setFont_(followup_font)
            followup_field.setTextColor_(
                settings.muted_text_color(0.55 if followup_is_dim else 0.88)
            )
            followup_field.setBezeled_(False)
            followup_field.setDrawsBackground_(False)
            followup_field.setEditable_(False)
            followup_field.setSelectable_(True)
            followup_field.cell().setWraps_(True)
            followup_field.cell().setScrollable_(False)
            followup_field.cell().setLineBreakMode_(NSLineBreakByWordWrapping)
            card.addSubview_(followup_field)

        if show_action_btn:
            action_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(width - 12 - 90, btn_y, 90, 18)
            )
            action_btn.setTitle_(btn_label)
            action_btn.setBezelStyle_(NSBezelStyleInline)
            action_btn.setBordered_(False)
            action_btn.setFont_(NSFont.systemFontOfSize_(10))
            action_btn.setTag_(entry["id"])
            action_btn.setTarget_(self)
            action_btn.setAction_(b"tellMore:")
            tip = {
                "Tell me more": "Get a longer explanation",
                "Show less": "Collapse the longer explanation",
                "Show more": "Show the longer explanation again",
                "Try again": "Retry the longer explanation",
            }.get(btn_label, "")
            if tip:
                action_btn.setToolTip_(tip)
            card.addSubview_(action_btn)

        return card
