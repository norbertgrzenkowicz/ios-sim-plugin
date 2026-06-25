# ios-sim — iOS Simulator Plugin for AI Coding Agents

Control the iOS Simulator from any AI coding tool. Boot devices, install & launch apps,
take screenshots, interact with UI (tap, type, swipe), query accessibility trees,
simulate locations, send push notifications, manage permissions — all through natural
language commands.

**Works with:** OpenCode, Claude Code, Codex, Cursor, Windsurf, or any MCP-compatible client.  
**Backed by:** XcodeBuildMCP (72+ tools) + native macOS Accessibility API bridge.  
**Feature parity with:** Codex "Build iOS Apps" plugin — but model-agnostic.

## Features

| Capability | Status |
|-----------|--------|
| Device management (list, boot, shutdown, erase) | ✅ |
| App management (install, launch, terminate, list) | ✅ |
| Xcode project build, test, run on simulator | ✅ |
| Screenshots + video recording | ✅ |
| UI interaction: tap, type, swipe, long-press, drag | ✅ |
| Accessibility tree dump + element search | ✅ |
| OCR text detection (Vision fallback for Flutter apps) | ✅ |
| Hardware buttons (home, volume, lock, Siri) | ✅ |
| Gesture presets (shake, rotate) | ✅ |
| Deep links | ✅ |
| Push notifications | ✅ |
| Location simulation | ✅ |
| Media addition (photos/videos to simulator library) | ✅ |
| Privacy permissions grant/revoke | ✅ |
| Pasteboard read/write | ✅ |
| Status bar overrides | ✅ |
| Light/dark appearance toggle | ✅ |
| Hardware/software keyboard toggle | ✅ |
| LLDB debugging (breakpoints, stack, variables) | ✅ |
| Code coverage reports | ✅ |
| Physical device build/test | ✅ |
| macOS app build/test | ✅ |
| Swift Package Manager integration | ✅ |
| Project scaffolding (iOS/macOS) | ✅ |

## Requirements

- **macOS 14.5+** with **Xcode 16+** installed
- **Accessibility permission** for your terminal app
  (System Settings → Privacy & Security → Accessibility)
- **Python 3** (for the CLI wrapper)
- **Node.js 18+** (optional, for XcodeBuildMCP)

## Quick Install

```bash
# 1. Clone the repo
git clone https://github.com/<your-org>/ios-sim-plugin.git
cd ios-sim-plugin

# 2. Install the skill and CLI
./install.sh

# 3. Verify
ios-sim status
```

Or install just the skill manually:

```bash
# OpenCode
cp SKILL.md ~/.agents/skills/ios-sim/SKILL.md

# Claude Code
cp SKILL.md ~/.claude/skills/ios-sim/SKILL.md
```

### Optional: Install XcodeBuildMCP (for build/test/debug features)

```bash
npm install -g xcodebuildmcp@latest
```

## Quick Start

```bash
# Check if everything is ready
ios-sim status

# List available simulators
ios-sim device list

# Boot a device (use UDID from the list)
ios-sim device boot <udid>

# Install and launch an app
ios-sim app install /path/to/YourApp.app
ios-sim app launch com.example.app

# See what's on screen
ios-sim screenshot screenshot.png
ios-sim ui tree

# Interact with the UI
ios-sim ui tap 200 400
ios-sim ui type "hello@example.com"
ios-sim ui swipe 100 500 100 200

# Build and run from Xcode project
ios-sim build-run --scheme MyApp --project ./MyApp.xcodeproj
```

## Command Reference

Full documentation is in [SKILL.md](SKILL.md) — the file that AI agents read to learn
how to use the tool. Here are the main command groups:

```
ios-sim device <list|boot|shutdown|erase|info>
ios-sim app   <install|launch|terminate|list|bundle-id>
ios-sim build [--scheme] [--project|--workspace]
ios-sim build-run [--scheme] [--project] [--sim]
ios-sim test  [--scheme] [--project]
ios-sim screenshot [file.png]
ios-sim video [file.mp4]
ios-sim ui    <snapshot|tap|type|swipe|tree|find|wait|button|gesture>
ios-sim sim   <location|appearance|statusbar|keyboard-*>
ios-sim open <url>
ios-sim notification <payload.json> [--bundle-id]
ios-sim media add <photo-or-video>
ios-sim privacy <grant|revoke|reset> <service> <bundle-id>
ios-sim pasteboard <copy|paste>
ios-sim xcode <workflow> <tool> [args]
```

## How It Works

```
┌──────────────────────────────────────────────────┐
│  ios-sim (Python CLI) — unified command surface   │
├──────────────────────────────────────────────────┤
│  XcodeBuildMCP (72 tools)                        │
│  • Build/test/run for sim, device, macOS         │
│  • UI automation (snapshot/ref-based)            │
│  • LLDB debugging, code coverage, SPM, projects  │
├──────────────────────────────────────────────────┤
│  ax-helper (Swift binary) — macOS Accessibility  │
│  • AX tree dump, CGEvent tap/type/swipe          │
│  • Element find/wait by label                    │
├──────────────────────────────────────────────────┤
│  simctl (Xcode CLI) — low-level device ops       │
│  • Device lifecycle, notifications, media        │
│  • Privacy, pasteboard, location, status bar     │
└──────────────────────────────────────────────────┘
```

## Project Structure

```
ios-sim-plugin/
├── SKILL.md                # AI agent instructions (loaded by skill tool)
├── install.sh              # One-command installer
├── opencode.json           # Permission config for OpenCode
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── .github/                # Issue/PR templates
├── bin/
│   ├── ios-sim.py          # Main CLI
│   └── ax-helper*          # Compiled Swift AX bridge
├── ax-helper-src/
│   └── main.swift          # Swift source for AX bridge
└── installer/
    └── mcp-config.json     # MCP server config templates
```

## Agent Skill Discovery

When an AI agent needs to control the iOS Simulator, it calls the `skill` tool
to load instructions:

```
skill("ios-sim")
```

The agent then reads [SKILL.md](SKILL.md) and learns all available commands and workflows.

## License

MIT — see [LICENSE](LICENSE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). **PRs only — no direct commits to main.**
