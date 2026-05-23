"""Grasp menubar app — ties hotkey, selection, panel, and API together."""

import threading
import time
import traceback

import rumps
from PyObjCTools import AppHelper

from . import api, hotkey, keychain, onboarding, panel, selection


class GraspApp(rumps.App):
    def __init__(self):
        super().__init__("Grasp", title="◐", quit_button=None)
        self.menu = [
            "Show / Hide Panel",
            "Settings…",
            "Change API Key…",
            None,
            "Quit Grasp",
        ]
        self.panel = None
        self.client = None
        self.query_count = 0

    # ----------------------------------------------------------- menu actions

    @rumps.clicked("Show / Hide Panel")
    def _menu_toggle(self, _):
        if self.panel is not None:
            self.panel.toggle()

    @rumps.clicked("Settings…")
    def _menu_settings(self, _):
        if self.panel is not None:
            self.panel.show_settings()

    @rumps.clicked("Change API Key…")
    def _menu_change_key(self, _):
        self._show_onboarding()

    @rumps.clicked("Quit Grasp")
    def _menu_quit(self, _):
        rumps.quit_application()

    # ------------------------------------------------------------- lifecycle

    def run(self):
        AppHelper.callAfter(self._post_launch)
        super().run()

    def _post_launch(self):
        try:
            hotkey.start_hotkeys(
                on_toggle=self._on_toggle_hotkey,
                on_grab=self._on_grab_hotkey,
            )
        except Exception:
            traceback.print_exc()

        key = keychain.get_api_key()
        if key:
            self._setup_with_key(key)
        else:
            self._show_onboarding()

    def _setup_with_key(self, key: str):
        try:
            self.client = api.make_client(key)
        except Exception:
            traceback.print_exc()
            self.client = None
        if self.panel is None:
            self.panel = panel.GraspPanel.alloc().initWithController_(self)
            self.panel.show()

    def _show_onboarding(self):
        onboarding.show_onboarding(self._on_key_saved)

    def _on_key_saved(self, key: str):
        keychain.save_api_key(key)
        self._setup_with_key(key)

    # ------------------------------------------------------------- hotkeys

    def _on_toggle_hotkey(self):
        # ⌘⇧Space — toggle the panel. No selection capture; never explains.
        # Fires on the main thread from the NSEvent monitor, safe to do
        # UI work directly.
        if self.panel is not None:
            self.panel.toggle()

    def _on_grab_hotkey(self):
        # ⌘⇧G — grab the current selection and explain it. The clipboard
        # work has to happen off the main thread so the polling sleep
        # doesn't freeze the UI.
        threading.Thread(target=self._grab_worker, daemon=True).start()

    def _grab_worker(self):
        # Wait long enough for the user to physically release ⌘ and ⇧
        # before we synthesize ⌘C. If we fire too early, the receiving app
        # sees ⌘⇧C and ignores it.
        time.sleep(0.15)
        try:
            text = selection.get_selected_text()
        except Exception:
            traceback.print_exc()
            text = None
        AppHelper.callAfter(self._after_grab, text)

    def _after_grab(self, text):
        if self.panel is None or not text:
            return
        self.panel.show()
        self._explain(text)

    # ------------------------------------------------------------- explain

    def _explain(self, text: str):
        if self.client is None:
            if self.panel is not None:
                self.query_count += 1
                self.panel.set_query_count(self.query_count)
                entry = self.panel.add_loading_entry(text)
                self.panel.update_entry_error(entry, "No API key configured.")
            return

        context = self.panel.get_context()
        self.query_count += 1
        self.panel.set_query_count(self.query_count)
        entry = self.panel.add_loading_entry(text)

        client = self.client

        def worker():
            try:
                result = api.explain(client, text, context)
                if not result:
                    raise RuntimeError("Empty response from Claude")
                AppHelper.callAfter(self.panel.update_entry, entry, result)
            except Exception as ex:
                AppHelper.callAfter(self.panel.update_entry_error, entry, str(ex))

        threading.Thread(target=worker, daemon=True).start()

    def explain_more(self, entry):
        if self.panel is None or self.client is None:
            return
        text = entry["term"]
        prior = entry["explanation"]
        context = self.panel.get_context()
        self.panel.set_followup_loading(entry)

        client = self.client

        def worker():
            try:
                result = api.explain_more(client, text, prior, context)
                if not result:
                    raise RuntimeError("Empty response from Claude")
                AppHelper.callAfter(self.panel.set_followup, entry, result)
            except Exception as ex:
                AppHelper.callAfter(
                    self.panel.set_followup_error, entry, str(ex)
                )

        threading.Thread(target=worker, daemon=True).start()


def main():
    GraspApp().run()
