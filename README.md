# Grasp

A floating menubar Mac app that explains whatever you've highlighted.
Highlight text anywhere, press a hotkey, and a tight explanation appears
in a side panel on the right of your screen. Powered by Claude.

## What it does

- **Grab hotkey** (default ⌘⇧G): grabs your selected text via the
  clipboard and asks Claude for a short, confident explanation. Works for
  single words, sentences, or short paragraphs.
- **Panel hotkey** (default ⌘⇧Space): shows / hides the side panel.
- **Side panel**: keeps a scrollable history of every explanation from
  your session, with per-entry **Copy**, **Pin**, and **Tell me more**
  buttons. Has an optional **context** field (e.g. "DJ", "legal",
  "Rust") to bias explanations toward your domain.
- **Settings panel** (gear icon in the panel header, or *Settings…* in
  the menubar): rebind hotkeys, pick from preset background colors or
  open the full color wheel, choose white or black text, tune opacity
  and font size, clear history. All preferences persist via
  `NSUserDefaults`.
- **Tell me more**: per-entry button that fetches a longer, more
  detailed explanation and tucks it below the original. Toggle with
  **Show less** / **Show more**.
- **First-launch onboarding**: prompts once for your Anthropic API key
  and stores it in the macOS **Keychain**. Never asks again.

## Install

### Build the .app

```bash
git clone <your-fork-url> Grasp
cd Grasp
./build.sh
```

The script creates a virtualenv, installs dependencies, builds
`dist/Grasp.app` with py2app, and optionally moves it into
`/Applications`. Launch it like any Mac app — it lives in the menubar
as `◐`.

### Or run from source

```bash
./run.sh
```

Same dependencies, no bundle build.

## Get an Anthropic API key

1. Sign in at <https://console.anthropic.com>.
2. Go to **API Keys** → **Create Key**.
3. Copy the key (starts with `sk-ant-…`) and paste it into the Grasp
   onboarding window on first launch.

The key is written to the macOS Keychain (`service: com.grasp.app`,
`account: anthropic_api_key`) and is never stored in plaintext on disk.

## First launch

macOS will prompt for **Accessibility** permission — required for the
global hotkeys and for synthesizing ⌘C to read your selection. Grant it
under **System Settings → Privacy & Security → Accessibility**, then
quit and relaunch Grasp.

## Menubar menu

- **Show / Hide Panel** — toggle visibility without using the hotkey
- **Settings…** — open the inline settings view
- **Change API Key…** — re-run the onboarding window
- **Quit Grasp**

## Project layout

```
Grasp/
├── grasp/
│   ├── app.py          # rumps menubar app + orchestration
│   ├── api.py          # anthropic SDK wrapper (brief + detailed)
│   ├── hotkey.py       # NSEvent global hotkey + rebinding
│   ├── keychain.py     # Security framework wrapper
│   ├── onboarding.py   # first-launch API-key window
│   ├── panel.py        # floating panel UI + inline settings
│   ├── selection.py    # synthesize ⌘C and read clipboard
│   └── settings.py     # NSUserDefaults preferences
├── grasp_main.py       # entry point
├── requirements.txt
├── setup.py            # py2app config
├── build.sh
├── run.sh
└── README.md
```

## Troubleshooting

- **Hotkeys do nothing.** macOS hasn't granted Accessibility yet.
  Toggle Grasp on under System Settings → Privacy & Security →
  Accessibility (you may need to remove and re-add it after rebuilding),
  then relaunch.
- **"Could not connect."** Use *Change API Key…* in the menubar to
  re-enter the key, or check network access to `api.anthropic.com`.
- **Selection isn't picked up in some apps.** A few apps block
  synthesized ⌘C (some terminal multiplexers, certain games). Grasp
  silently does nothing in that case.

## Uninstall

```bash
rm -rf /Applications/Grasp.app
security delete-generic-password -s com.grasp.app -a anthropic_api_key
```
