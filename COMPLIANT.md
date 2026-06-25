# ios-sim Compliance Report

Tested: 2026-06-25, macOS 15.x, iOS 18.4 Simulator  
Device: iPad Pro 13-inch (M4), iPhone 16 Plus  
App: Flutter 3.41.6 (debug build for simulator) — also tested with native SwiftUI app

## Works ✅

| Feature | Notes |
|---------|-------|
| `ios-sim status` | Shows sim state, AX helper, XcodeBuildMCP readiness |
| `ios-sim ui find "<text>"` | Finds elements by `AXDescription` (e.g. `Weight`, `Add Meal`) |
| `ios-sim ui tap <x> <y>` | Registers tap on simulator content at logical-point coordinates |
| `ios-sim ui tree --ocr` | Vision-based OCR returning text regions with coordinates (falls back to this automatically when AX tree is empty) |
| `ios-sim ui find "<text>" --ocr` | Searches OCR text regions for matching labels |
| `xcrun simctl io <udid> screenshot` | Saves full-res PNG (2064x2752 for iPad 13") |

## Partially Resolved / Improved 🟡

### 1. `ios-sim ui tree` — OCR fallback (was empty for Flutter apps)

**Before:** The AX tree dump returned only a root `AXGroup` with no children. Flutter widgets do not surface their semantics hierarchy unless `ensureSemantics()` is called.

**Now:** `ios-sim ui tree` **automatically falls back to OCR** (Apple Vision `VNRecognizeTextRequest`) when the AX tree is empty. Returns detected text labels with bounding-box coordinates in logical-point space. Text discovery is no longer blind:

```
ios-sim ui tree  →  (AX tree empty → OCR fallback)
                    { "source": "ocr", "texts": [
                        {"text":"Welcome Back!", "x":382, "y":442, "width":166, "height":19},
                        {"text":"Email", "x":75, "y":556, "width":36, "height":10},
                        ...
                      ]}
```

**Flags:** `--ocr` forces OCR-only mode; `--ax-only` shows raw (empty) AX tree for debugging.

### 2. `ios-sim ui snapshot` — remains AX-only (no change)

XcodeBuildMCP's snapshot uses the AX bridge. For Flutter without semantics, it returns empty. No OCR integration planned for this command — use `screenshot` + `ui tree --ocr` instead.

### 3. PopupMenuButton / overflow menu not accessible

**Unchanged.** Flutter's `PopupMenuButton` renders outside the standard iOS accessibility hierarchy (known Flutter engine bug `flutter/flutter#186544`, `#182604`). OCR won't detect menu labels if they're rendered as shapes rather than text.

**Impact:** Cannot navigate through the primary menu of a Flutter app programmatically. Still requires manual interaction or pre-computed coordinates for these menus.

### 4. Coordinate system — improved chrome compensation

**Before:** Ambiguous coordinate mapping; taps < y:100 could hit the macOS menu bar. The AX bridge did not consistently compensate for Simulator.app window chrome (title bar + border).

**Now:** `tapAtPoint` and `swipe` use `getContentOrigin()` which:
1. Queries the `iOSContentGroup`'s absolute `AXPosition` (preferred)
2. Falls back to the main window position + estimated chrome offset (~19pt title bar, ~1pt border)  
3. Still allows manual `--offset-x` and `--offset-y` flags on `ios-sim ui tap` for fine-tuning

Note: Some Flutter apps have `SafeArea` insets (status bar ~24pt, notch). Taps in those zones may not trigger Flutter gesture detectors even if the coordinate math is correct.

### 5. `ios-sim ui type` — not tested for this use case

No change. The test app has no editable text fields at navigation level.

### 6. `ios-sim ui swipe` — coordinates improved

Now uses same `contentToScreen()` mapping as `tapAtPoint`. Coordinate system consistent across all gesture commands.

## Multi-simulator confusion ⚠️

When multiple simulators are booted, `ios-sim` targets the last-booted device (or whichever is "main window"). The behaviour is undefined. Manually shutting down unused simulators with `xcrun simctl shutdown <udid>` avoids this.

## Summary for Flutter screenshot automation

| Requirement | Can ios-sim do it? |
|-------------|-------------------|
| Install & launch app | ✅ via `xcrun simctl install` + `launch` |
| Know what's on screen | ✅ `ui tree` auto-fallback to OCR (text regions with coords) |
| Find element by label | ✅ OCR-based find via `--ocr` flag (or auto-fallback) |
| Tap known coordinates | ✅ Coordinate system fixed with chrome compensation + `--offset-*` flags |
| Swipe/scroll | ✅ Coordinates fixed; test on your app |
| Navigate to sub-screens (Settings, Progress) | ❌ PopupMenuButton invisible (Flutter engine bug) |
| Take screenshot | ✅ `xcrun simctl io screenshot` |

## Recommendation (updated)

For Flutter screenshot workflows on iOS simulator:

1. **Try AX first** — `ios-sim ui tree` automatically falls back to OCR if the AX tree is empty.
2. **For discovery:** Use `ios-sim ui tree --ocr` to see all visible text with coordinates.
3. **For navigation:** Use `ios-sim ui find "<label>" --ocr` to locate text, then `ios-sim ui tap <x> <y>` using the returned coordinates.
4. **If taps are off:** Use `--offset-y <n>` (positive = down) to adjust for chrome/SafeArea.
5. **PopupMenuButton workaround:** Still requires manual navigation or pre-computed coordinates (Flutter engine bug, not solvable from outside).
