---
name: ios-sim
description: >
  Full iOS Simulator control for AI agents. Build, test, run, debug iOS/macOS apps
  on simulator, control UI via accessibility, manage devices, send notifications,
  simulate location, manage permissions. Equivalent to Codex "Build iOS Apps" plugin.
  Backed by XcodeBuildMCP (72+ tools) + custom Swift AX bridge.
compatibility: opencode
---

# ios-sim — iOS Simulator Control (v2)

Complete iOS Simulator plugin — **1:1 feature parity with Codex "Build iOS Apps"**.

## Prerequisites

- **Xcode** installed (`xcode-select -p` must work)
- **Accessibility permission**: grant your shell in System Settings > Privacy & Security > Accessibility
- **XcodeBuildMCP** (optional but recommended for build/test/debug):
  ```
  npm install -g xcodebuildmcp@latest
  ```
- **Simulator** must be running (auto-launched when booting)

## Install `ios-sim` Command

```bash
# Quick install
./install.sh

# Or manually add to PATH
export PATH="/path/to/ios-sim-plugin/bin:$PATH"
```

If `ios-sim` is not found after install, add to your shell profile:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

## How Agents Should Use This

Call `skill("ios-sim")` when you need to control the iOS Simulator.
The following workflows describe how to accomplish common tasks.

### Workflow: Test iOS App

1. **Prep**: `ios-sim status` — verify simulator is accessible
2. **Boot**: `ios-sim device boot <udid>` if no device running
3. **Install**: `ios-sim app install build/ios/iphonesimulator/Runner.app`
4. **Launch**: `ios-sim app launch com.example.app`
5. **Observe the screen** (choose based on your capability):

   **If you have vision** (GPT-4o, Claude 3.5+):
   ```
   ios-sim screenshot
   read <path_from_output>  ← view the image inline like Codex does
   ```

    **If you don't have vision** (DeepSeek, etc.):
    ```
    ios-sim ui tree     ← get text-based accessibility hierarchy with coordinates
    ios-sim ui find "Login"  ← find specific elements by label
    ```
    The AX tree is often MORE useful than a screenshot because it gives exact
    coordinates for tapping.

    **⚠️ Flutter apps**: Flutter doesn't expose its widget tree to the iOS
    Accessibility API unless `SemanticsBinding.instance.ensureSemantics()` is
    called in the Dart code. For Flutter apps, `ui tree` and `ui find`
    **automatically fall back to OCR** (Vision text recognition) when the AX
    tree is empty. OCR returns text regions with coordinates you can tap on.
    If you know the app is Flutter, you can also force OCR mode:
    ```
    ios-sim ui tree --ocr     ← force OCR mode (skip AX)
    ios-sim ui tree --ax-only ← see the raw (empty) AX tree for debugging
    ios-sim ui find "Login" --ocr  ← force OCR-based text search
    ```

6. **Interact** using coordinates from the tree:
   ```
   ios-sim ui tap 200 400
   ios-sim ui type "hello@example.com"
   ios-sim ui swipe 100 500 100 200
   ```
7. **Verify**: Take another screenshot or re-read the AX tree

### Workflow: Build & Run Xcode Project

```bash
# One-shot build, install, launch (requires XcodeBuildMCP)
ios-sim build-run --scheme MyApp --workspace MyApp.xcworkspace
```

### Workflow: Debug Running App

```bash
# Attach LLDB debugger
ios-sim xcode debugging attach com.example.app
ios-sim xcode debugging add-breakpoint ViewController.swift:42
ios-sim xcode debugging continue
# When breakpoint hits:
ios-sim xcode debugging variables
ios-sim xcode debugging stack
```

## Quick Start

```bash
# Everything readiness check
ios-sim status

# List devices & boot one
ios-sim device list
ios-sim device boot <udid>

# Install & launch an app
ios-sim app install /path/to/App.app
ios-sim app launch com.example.app

# See what's on screen & interact
ios-sim screenshot screen.png
ios-sim ui tree                       # accessibility hierarchy
ios-sim ui tap 200 400                # tap coordinate
ios-sim ui type "hello"               # type text
ios-sim ui swipe 100 500 100 200      # swipe gesture
ios-sim ui find "Login"               # find element by text

# Build & run (requires XcodeBuildMCP)
ios-sim build --scheme MyApp --project ./MyApp.xcodeproj
ios-sim build-run --scheme MyApp      # one-shot build+install+launch
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `AX helper not found` | Run `./install.sh` or `swiftc -o bin/ax-helper ax-helper-src/main.swift` |
| `Accessibility permissions required` | Grant terminal access in System Settings > Privacy & Security > Accessibility |
| `Xcode not found` | Run `xcode-select --install` or install Xcode from App Store |
| `XcodeBuildMCP not found` | `npm install -g xcodebuildmcp@latest` |
| `No booted device` | `ios-sim device list` then `ios-sim device boot <udid>` |
| `Command not found: ios-sim` | Add `~/.local/bin` to PATH or run `./install.sh` |

## Full Command Reference (1:1 with Codex Plugin)

### Device Management
| Command | Codex Equivalent | Description |
|---------|-----------------|-------------|
| `ios-sim device list` | ✅ | List all simulators |
| `ios-sim device boot <id>` | ✅ | Boot a device |
| `ios-sim device shutdown <id>` | ✅ | Shutdown |
| `ios-sim device erase <id>` | ✅ | Erase & reset |
| `ios-sim device info` | ✅ | Show booted device details |

### App Management
| Command | Codex Eq | Description |
|---------|---------|-------------|
| `ios-sim app install <path>` | ✅ | Install .app bundle |
| `ios-sim app launch <bundle>` | ✅ | Launch by bundle ID |
| `ios-sim app terminate <bundle>` | ✅ | Terminate |
| `ios-sim app list` | ✅ | List installed apps |
| `ios-sim app bundle-id <path>` | ✅ | Extract bundle ID from .app |

### Build & Test (XcodeBuildMCP)
| Command | Codex Eq | Description |
|---------|---------|-------------|
| `ios-sim build --scheme X` | ✅ | Build for simulator |
| `ios-sim build-run --scheme X` | ✅ | Build + install + launch |
| `ios-sim test --scheme X` | ✅ | Run tests on simulator |
| `ios-sim discover-projects [dir]` | ✅ | Find Xcode projects |

### Screenshots & Video
| Command | Codex Eq | Description |
|---------|---------|-------------|
| `ios-sim screenshot [file.png]` | ✅ | Capture screenshot (returns path + base64) |
| `ios-sim video [file.mp4]` | ✅ | Record video (Ctrl+C to stop) |

**IMPORTANT — Understanding the screen** (choose the right approach for your model):

**If you have vision capabilities** (GPT-4o, Claude 3.5+): After `ios-sim screenshot`, use `read <path>` to view the image inline — works exactly like Codex's native screenshot tool.

**If you don't have vision** (DeepSeek, etc.): Use `ios-sim ui tree` instead — this returns the full accessibility hierarchy as text with exact element positions, labels, and roles. It's often MORE useful than a screenshot because you get exact coordinates for tapping.

```bash
# Agent workflow with vision:
ios-sim screenshot
read /path/from/output/screenshot.png   ← See the image like Codex does

# Agent workflow without vision:
ios-sim ui tree   ← Get text-based UI description with coordinates
ios-sim ui find "Login"   ← Find specific elements
```

### UI Interaction
| Command | Codex Eq | Description |
|---------|---------|-------------|
| `ios-sim ui snapshot` | ✅ | Take UI snapshot (accessibility) |
| `ios-sim ui tree [--ocr\|--ax-only]` | ✅+ | Dump accessibility hierarchy (auto-fallback to OCR) |
| `ios-sim ui find <label> [--ocr\|--ax-only]` | ✅+ | Search by label/description (auto-fallback to OCR) |
| `ios-sim ui wait <selector>` | ✅ | Wait for element |
| `ios-sim ui tap <x> <y> [--offset-x\|--offset-y]` | ✅ | Tap at coordinates |
| `ios-sim ui type <text>` | ✅ | Type text |
| `ios-sim ui swipe <x1> <y1> <x2> <y2>` | ✅ | Swipe gesture |
| `ios-sim ui button <btn>` | ✅ | Hardware button (home/vol/lock/siri) |
| `ios-sim ui gesture <preset>` | ✅ | Gesture preset |
| `ios-sim ui long-press <ref>` | ✅ | Long press element |
| `ios-sim ui drag <ref> <dir>` | ✅ | Drag element |
| `ios-sim ui key-press <code>` | ✅ | HID key press |

### Simulator Settings
| Command | Codex Eq | Description |
|---------|---------|-------------|
| `ios-sim sim location <lat> <lng>` | ✅ | Set simulated GPS |
| `ios-sim sim location-reset` | ✅ | Clear location |
| `ios-sim sim appearance <light\|dark>` | ✅ | Toggle appearance |
| `ios-sim sim statusbar <json>` | ✅ | Override status bar |
| `ios-sim sim keyboard-connect` | ✅ | Toggle hardware keyboard |
| `ios-sim sim keyboard-software` | ✅ | Toggle software keyboard |

### Other
| Command | Codex Eq | Description |
|---------|---------|-------------|
| `ios-sim open <url>` | ✅ | Open URL / deep link |
| `ios-sim notification <file> [--bundle-id]` | ✅ | Simulate push notification |
| `ios-sim media add <path>` | ✅ | Add photo/video to library |
| `ios-sim privacy <grant\|revoke> <service> <bundle>` | ✅ | Manage permissions |
| `ios-sim pasteboard copy <text>` | ✅ | Copy to sim pasteboard |
| `ios-sim pasteboard paste` | ✅ | Read sim pasteboard |

### Debugging (XcodeBuildMCP)
| Command | Codex Eq | Description |
|---------|---------|-------------|
| `ios-sim xcode debugging attach <bundle>` | ✅ | Attach LLDB |
| `ios-sim xcode debugging add-breakpoint <file:line>` | ✅ | Set breakpoint |
| `ios-sim xcode debugging stack` | ✅ | Get backtrace |
| `ios-sim xcode debugging variables` | ✅ | Get frame variables |
| `ios-sim xcode debugging lldb-command <cmd>` | ✅ | Run LLDB command |

### XcodeBuildMCP Passthrough
| Command | Description |
|---------|-------------|
| `ios-sim xcode <workflow> <tool> [args]` | Direct XcodeBuildMCP command |

## Architecture

```
┌─────────────────────────────────────────────────┐
│  ios-sim (Python CLI) — unified command surface  │
├─────────────────────────────────────────────────┤
│  XcodeBuildMCP (npm) — 72 tools                 │
│  • build/test/run for sim, device, macOS        │
│  • UI automation (snapshot/ref-based)            │
│  • LLDB debugging                                │
│  • Code coverage, SPM, project scaffolding       │
├─────────────────────────────────────────────────┤
│  ax-helper (Swift binary) — AX bridge           │
│  • Accessibility tree dump                      │
│  • CGEvent tap/type/swipe                       │
│  • Element find/wait                            │
├─────────────────────────────────────────────────┤
│  simctl (Xcode CLI) — device ops                │
│  • Device lifecycle, notifications, media        │
│  • Privacy, pasteboard, location, status bar     │
└─────────────────────────────────────────────────┘
```

## How Agents Should Use This

### Workflow: Test iOS App

1. **Prep**: `ios-sim status` — verify everything is ready
2. **Boot**: `ios-sim device boot <udid>` if no device running
3. **Install**: `ios-sim app install build/ios/iphonesimulator/Runner.app`
4. **Launch**: `ios-sim app launch com.example.app`
5. **Observe**: `ios-sim screenshot` → analyze with vision model
6. **Read UI**: `ios-sim ui tree` → get accessibility hierarchy with positions
7. **Find elements**: `ios-sim ui find "button label"` → get coordinates
8. **Interact**: Use coordinates to tap, type, swipe
9. **Verify**: Screenshot again or check AX tree

### Workflow: Build & Deploy Changes

```bash
# Build changes and run
ios-sim build-run --scheme MyApp --workspace MyApp.xcworkspace
# This: builds + installs + launches + captures logs
```

### Workflow: Debug

```bash
# Attach debugger to running app
ios-sim xcode debugging attach com.example.app
# Set breakpoint
ios-sim xcode debugging add-breakpoint ViewController.swift:42
# Continue execution
ios-sim xcode debugging continue
# When breakpoint hits, inspect state
ios-sim xcode debugging variables
```

## Feature Comparison

| Feature | Codex Plugin | ios-sim v2 |
|---------|-------------|-----------|
| Device list/boot/shutdown | ✅ | ✅ |
| Install/launch/terminate | ✅ | ✅ |
| Build for simulator | ✅ | ✅ |
| Build + run (one-shot) | ✅ | ✅ |
| Run tests | ✅ | ✅ |
| Screenshots | ✅ | ✅ |
| Video recording | ✅ | ✅ |
| Tap/type/swipe | ✅ | ✅ |
| Accessibility tree | ✅ | ✅ |
| UI element find/wait | ✅ | ✅ |
| Hardware buttons | ✅ | ✅ |
| Gesture presets | ✅ | ✅ |
| Deep links | ✅ | ✅ |
| Push notifications | ✅ | ✅ |
| Location simulation | ✅ | ✅ |
| Media addition | ✅ | ✅ |
| Privacy permissions | ✅ | ✅ |
| Pasteboard ops | ✅ | ✅ |
| Status bar overrides | ✅ | ✅ |
| Appearance toggle | ✅ | ✅ |
| Keyboard toggle | ✅ | ✅ |
| LLDB debugging | ✅ | ✅ |
| Code coverage | ✅ | ✅ |
| SPM support | ✅ | ✅ |
| Physical device support | ✅ | ✅ |
| macOS app support | ✅ | ✅ |
| Project scaffolding | ✅ | ✅ |
| Model-agnostic | ❌ (Claude only) | ✅ |
