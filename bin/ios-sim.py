#!/usr/bin/env python3
"""
ios-sim — iOS Simulator Control Tool for OpenCode
v2.0 — Integrated with XcodeBuildMCP (72+ tools)

Provides a unified CLI that wraps:
  - XcodeBuildMCP (build, test, simulate, debug, UI automation)
  - xcrun simctl (device mgmt, push, media, permissions, pasteboard)
  - ax-helper (Swift AX bridge for UI interaction)

Usage:
  ios-sim [command] [args...]

  # Quick start
  ios-sim status                          Check simulator readiness
  ios-sim help                            Show this help

  # Device management (wraps xcodebuildmcp + simctl)
  ios-sim device list                     List simulators
  ios-sim device boot <udid|name>         Boot a device
  ios-sim device shutdown <udid>          Shutdown a device
  ios-sim device erase <udid>             Erase device content
  ios-sim device info                     Show booted device info

  # App management (wraps xcodebuildmcp + simctl)
  ios-sim app install <path>              Install .app on booted device
  ios-sim app launch <bundle_id>          Launch app
  ios-sim app terminate <bundle_id>       Terminate app
  ios-sim app list                        List installed apps
  ios-sim app bundle-id <path>            Extract bundle ID from .app

  # Build & Test (wraps xcodebuildmcp)
  ios-sim build [--scheme X] [--project X]           Build for simulator
  ios-sim build-run [--scheme X] [--project X]        Build + install + launch
  ios-sim test [--scheme X] [--project X]             Test on simulator
  ios-sim discover-projects [path]                    Find Xcode projects

  # Screenshots & Video
  ios-sim screenshot [file.png]            Take screenshot
  ios-sim video [file.mp4]                 Record video (Ctrl+C to stop)

  # UI Interaction (wraps xcodebuildmcp's snapshot-based UI automation)
  ios-sim ui snapshot                      Take UI snapshot (returns elements with refs)
  ios-sim ui tap <elementRef>              Tap element by ref
  ios-sim ui type <elementRef> <text>      Type into element
  ios-sim ui swipe <elementRef> <dir>      Swipe within element (up/down/left/right)
  ios-sim ui long-press <elementRef>       Long press element
  ios-sim ui drag <elementRef> <dir>       Drag element
  ios-sim ui button <button>               Press hardware button (home/vol/siri)
  ios-sim ui gesture <preset>              Simulate gesture (shake/lock/rotate)
  ios-sim ui key-press <code>              Press HID key code
  ios-sim ui wait <selector>               Wait for element to appear

  # Simulator Settings
  ios-sim sim location <lat> <lng>         Set simulated location
  ios-sim sim location reset               Reset location to none
  ios-sim sim appearance <light|dark>      Toggle appearance
  ios-sim sim statusbar <json>             Override status bar
  ios-sim sim keyboard connect             Connect hardware keyboard
  ios-sim sim keyboard software            Toggle software keyboard

  # Other
  ios-sim open <url>                       Open URL/deep link
  ios-sim notification <file> [--bundle]   Push notification
  ios-sim media add <path>                 Add photo/video to simulator
  ios-sim privacy <bundle> <service>       Grant/revoke privacy permission
  ios-sim pasteboard copy <text>           Copy to simulator pasteboard
  ios-sim pasteboard paste                 Read simulator pasteboard

  # XcodeBuildMCP passthrough
  ios-sim xcode <workflow> <tool> [args]   Direct XcodeBuildMCP command
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AX_HELPER_PATH = os.path.join(SCRIPT_DIR, "ax-helper")
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# ── Helpers ─────────────────────────────────────────────────────────────────

def check_xcodebuildmcp():
    """Ensure XcodeBuildMCP is available."""
    if not shutil.which("xcodebuildmcp"):
        print("XcodeBuildMCP not found. Install with:", file=sys.stderr)
        print("  npm install -g xcodebuildmcp@latest", file=sys.stderr)
        print("  brew install xcodebuildmcp (after: brew tap getsentry/xcodebuildmcp)", file=sys.stderr)
        return False
    return True


def run_xcodebuildmcp(args: list[str], capture=True) -> subprocess.CompletedProcess:
    """Run an XcodeBuildMCP command."""
    cmd = ["xcodebuildmcp"] + args
    try:
        if capture:
            return subprocess.run(cmd, capture_output=True, text=True)
        return subprocess.run(cmd)
    except FileNotFoundError:
        # XcodeBuildMCP was removed between check and run
        print("❌ XcodeBuildMCP not found. Install: npm install -g xcodebuildmcp@latest", file=sys.stderr)
        sys.exit(1)


def run_simctl(args: list[str], capture=True) -> subprocess.CompletedProcess:
    """Run a simctl command."""
    cmd = ["xcrun", "simctl"] + args
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True)
    return subprocess.run(cmd)


def run_ax(action: str, **kwargs) -> dict:
    """Send a command to the AX helper."""
    if not os.path.exists(AX_HELPER_PATH):
        # Try compiling
        src = os.path.join(PROJECT_DIR, "ax-helper-src", "main.swift")
        if os.path.exists(src):
            subprocess.run(["swiftc", "-o", AX_HELPER_PATH, src], capture_output=True)
        if not os.path.exists(AX_HELPER_PATH):
            return {"success": False, "error": "AX helper not found"}
    cmd = {"action": action, **kwargs}
    try:
        proc = subprocess.run(
            [AX_HELPER_PATH], input=json.dumps(cmd),
            capture_output=True, text=True, timeout=60
        )
        return json.loads(proc.stdout)
    except Exception as e:
        return {"success": False, "error": str(e)}


def require_ax():
    """Require AX helper to be available."""
    if not os.path.exists(AX_HELPER_PATH):
        src = os.path.join(PROJECT_DIR, "ax-helper-src", "main.swift")
        if os.path.exists(src):
            print("Compiling AX helper...", file=sys.stderr)
            result = subprocess.run(["swiftc", "-o", AX_HELPER_PATH, src], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed: {result.stderr}", file=sys.stderr)
                sys.exit(1)


def output_json(data):
    """Print JSON response."""
    print(json.dumps(data, indent=2, default=str))


def ok(msg, data=None):
    """Print success with optional JSON."""
    if data:
        output_json(data)
    print(f"✅ {msg}", file=sys.stderr)


def fail(msg):
    """Print error and exit."""
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


# ── Device Commands ─────────────────────────────────────────────────────────

def cmd_device_list(args):
    """List simulators using xcodebuildmcp."""
    if check_xcodebuildmcp():
        result = run_xcodebuildmcp(["simulator", "list"])
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                output_json(data)
                return
            except json.JSONDecodeError:
                pass
    # Fallback to simctl
    result = run_simctl(["list", "devices"])
    lines = result.stdout.split("\n")
    booted, shutdown = [], []
    current_runtime = None
    for line in lines:
        if line.startswith("==") and "--" in line:
            current_runtime = line.strip("= -")
        elif "(" in line and ")" in line and "--" not in line:
            parts = line.strip().split(" (")
            if len(parts) >= 2:
                name = parts[0].strip()
                udid = parts[1].split(")")[0]
                status = "Booted" if "Booted" in line else "Shutdown"
                entry = {"name": name, "udid": udid, "runtime": current_runtime, "status": status}
                if status == "Booted":
                    booted.append(entry)
                else:
                    shutdown.append(entry)
    output_json({"booted": booted, "shutdown": shutdown, "count": len(booted) + len(shutdown)})


def cmd_device_boot(args):
    """Boot a device."""
    identifier = args.identifier
    # Try xcodebuildmcp first
    if check_xcodebuildmcp():
        result = run_xcodebuildmcp(["simulator", "boot", identifier])
        if result.returncode == 0:
            ok(f"Device booted ({identifier})")
            return
    # Fallback to simctl
    result = run_simctl(["boot", identifier], capture=False)
    if result.returncode != 0:
        check = run_simctl(["list", "devices", identifier])
        if "Booted" in check.stdout:
            ok(f"Device already booted ({identifier})")
            return
        fail(f"Boot failed: {result.stderr or result.stdout}")
    ok(f"Device booted ({identifier})")


def cmd_device_shutdown(args):
    """Shutdown a device."""
    udid = args.udid
    result = run_simctl(["shutdown", udid], capture=False)
    if result.returncode != 0:
        check = run_simctl(["list", "devices", udid])
        if "Shutdown" in check.stdout:
            ok(f"Device already shutdown")
            return
        fail(f"Shutdown failed: {result.stderr}")
    ok(f"Device shutdown")


def cmd_device_erase(args):
    """Erase a device."""
    udid = args.udid
    result = run_simctl(["erase", udid], capture=False)
    if result.returncode != 0:
        fail(f"Erase failed: {result.stderr}")
    ok(f"Device erased")


def cmd_device_info(args):
    """Show booted device info."""
    result = run_simctl(["list", "devices", "booted"])
    devices = []
    for line in result.stdout.split("\n"):
        if "Booted" in line:
            parts = line.strip().split(" (")
            if len(parts) >= 2:
                name = parts[0].strip()
                udid = parts[1].split(")")[0]
                devices.append({"name": name, "udid": udid})
    if not devices:
        output_json({"status": "no_booted_device"})
        return
    for d in devices:
        runtime = run_simctl(["list", "devices", d["udid"]])
        for rline in runtime.stdout.split("\n"):
            if rline.startswith("--") and "iOS" in rline:
                d["runtime"] = rline.strip("-= ").strip()
                break
        if "runtime" not in d:
            d["runtime"] = "unknown"
    output_json({"devices": devices, "count": len(devices)})


# ── App Commands ─────────────────────────────────────────────────────────────

def cmd_app_install(args):
    """Install a .app bundle."""
    path = args.path
    if not os.path.exists(path):
        fail(f"App bundle not found: {path}")
    result = run_simctl(["install", "booted", path], capture=False)
    if result.returncode != 0:
        fail(f"Install failed: {result.stderr}")
    ok("App installed", {"status": "installed", "path": path})


def cmd_app_launch(args):
    """Launch an app."""
    bundle_id = args.bundle_id
    extra_args = args.extra_args or []
    result = run_simctl(["launch", "booted", bundle_id] + extra_args, capture=False)
    if result.returncode != 0:
        fail(f"Launch failed: {result.stderr}")
    pid = None
    for line in (result.stdout or "").split("\n") + (result.stderr or "").split("\n"):
        if "PID" in line:
            try:
                pid = int(line.split("PID")[-1].strip().split()[0])
            except:
                pass
    ok(f"App launched (PID: {pid})", {"bundle_id": bundle_id, "pid": pid})


def cmd_app_terminate(args):
    """Terminate an app."""
    bundle_id = args.bundle_id
    result = run_simctl(["terminate", "booted", bundle_id])
    if result.returncode != 0:
        fail(f"Terminate failed: {result.stderr}")
    ok("App terminated")


def cmd_app_list(args):
    """List installed apps."""
    result = run_simctl(["listapps", "booted"])
    try:
        plutil = subprocess.run(
            ["plutil", "-convert", "json", "-o", "-", "-"],
            input=result.stdout, capture_output=True, text=True
        )
        data = json.loads(plutil.stdout) if plutil.returncode == 0 else json.loads(result.stdout)
    except (json.JSONDecodeError, Exception):
        print(result.stdout)
        return
    apps = []
    for bundle_id, info in data.items():
        if isinstance(info, dict):
            apps.append({
                "bundle_id": bundle_id,
                "name": info.get("CFBundleDisplayName", info.get("CFBundleName", bundle_id)),
                "version": info.get("CFBundleVersion", "?"),
                "type": info.get("ApplicationType", "?"),
            })
    output_json({"apps": apps, "count": len(apps)})


def cmd_app_bundle_id(args):
    """Extract bundle ID from .app."""
    path = args.path
    plist_path = os.path.join(path, "Info.plist")
    if not os.path.exists(plist_path):
        fail(f"Info.plist not found in {path}")
    result = subprocess.run(
        ["plutil", "-extract", "CFBundleIdentifier", "raw", "-o", "-", plist_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        fail(f"Failed to extract bundle ID: {result.stderr}")
    bid = result.stdout.strip()
    ok(f"Bundle ID: {bid}", {"bundle_id": bid})


# ── Build & Test ─────────────────────────────────────────────────────────────

def cmd_build(args):
    """Build for simulator using XcodeBuildMCP."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required for build commands. Install: npm install -g xcodebuildmcp@latest")
    cmd = ["simulator", "build"]
    if args.scheme: cmd += ["--scheme", args.scheme]
    if args.project: cmd += ["--project-path", args.project]
    if args.workspace: cmd += ["--workspace-path", args.workspace]
    if args.config: cmd += ["--configuration", args.config]
    if args.extra: cmd += ["--extra-args"] + args.extra
    result = run_xcodebuildmcp(cmd)
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        fail("Build failed")
    print(result.stdout)
    ok("Build succeeded")


def cmd_build_run(args):
    """Build, install, and launch on simulator using XcodeBuildMCP."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    cmd = ["simulator", "build-and-run"]
    if args.scheme: cmd += ["--scheme", args.scheme]
    if args.project: cmd += ["--project-path", args.project]
    if args.workspace: cmd += ["--workspace-path", args.workspace]
    if args.config: cmd += ["--configuration", args.config]
    if args.sim: cmd += ["--simulator-name", args.sim]
    if args.launch_args: cmd += ["--launch-args"] + args.launch_args
    result = run_xcodebuildmcp(cmd, capture=False)
    if result.returncode != 0:
        fail("Build & run failed")
    ok("App built and launched")


def cmd_test(args):
    """Test on simulator using XcodeBuildMCP."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    cmd = ["simulator", "test"]
    if args.scheme: cmd += ["--scheme", args.scheme]
    if args.project: cmd += ["--project-path", args.project]
    if args.workspace: cmd += ["--workspace-path", args.workspace]
    if args.test_plan: cmd += ["--test-plan", args.test_plan]
    result = run_xcodebuildmcp(cmd, capture=False)
    if result.returncode != 0:
        fail("Test failed")
    ok("Tests completed")


def cmd_discover(args):
    """Discover Xcode projects."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    path = args.path or "."
    result = run_xcodebuildmcp(["project-discovery", "discover-projects", path])
    print(result.stdout or result.stderr)


# ── Screenshots & Video ──────────────────────────────────────────────────────

def cmd_screenshot(args):
    """Take a screenshot. Returns both file path (for read tool) and base64 (for vision)."""
    # Always use a temp file for reliability, then serve path + base64
    temp_dir = tempfile.mkdtemp(prefix="ios_sim_ss_")
    temp_path = os.path.join(temp_dir, "screenshot.png")
    
    result = run_simctl(["io", "booted", "screenshot", temp_path], capture=False)
    if result.returncode != 0:
        os.rmdir(temp_dir)
        fail(f"Screenshot failed: {result.stderr}")
    
    if not os.path.exists(temp_path):
        os.rmdir(temp_dir)
        fail("Screenshot file not created")
    
    with open(temp_path, "rb") as f:
        img_data = f.read()
    
    b64 = base64.b64encode(img_data).decode()
    
    # If user specified an output path, copy it there and clean up temp
    if args.output:
        shutil.copy2(temp_path, args.output)
        path = os.path.abspath(args.output)
        shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        path = temp_path
    
    print(f"✅ Screenshot captured: {path} ({len(img_data)} bytes)", file=sys.stderr)
    output_json({
        "path": path,
        "base64": b64,
        "size": len(img_data),
        "tip": "Use the OpenCode read tool on <path> to view the image",
        "saved_to": path
    })


def cmd_video(args):
    """Record video."""
    if check_xcodebuildmcp():
        output = args.output or f"simulator_{int(time.time())}.mp4"
        ok(f"Recording to {output} (Ctrl+C to stop)")
        try:
            run_xcodebuildmcp(["simulator", "record-video", output], capture=False)
        except KeyboardInterrupt:
            ok(f"Video saved to {output}")
        return
    # Fallback
    output = args.output or f"simulator_{int(time.time())}.mp4"
    ok(f"Recording to {output} (Ctrl+C to stop)")
    try:
        run_simctl(["io", "booted", "recordVideo", output], capture=False)
    except KeyboardInterrupt:
        ok(f"Video saved to {output}")


# ── UI Interaction (using AX helper + xcodebuildmcp) ─────────────────────────

def cmd_ui_snapshot(args):
    """Take a UI snapshot using XcodeBuildMCP."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required for snapshot-based UI")
    result = run_xcodebuildmcp(["simulator", "snapshot-ui"])
    if result.returncode != 0:
        fail(f"Snapshot failed: {result.stderr}")
    try:
        data = json.loads(result.stdout)
        output_json(data)
    except json.JSONDecodeError:
        print(result.stdout)


def cmd_ui_tap(args):
    """Tap element by ref (XcodeBuildMCP) or coordinates (AX helper)."""
    require_ax()
    if hasattr(args, 'element_ref') and args.element_ref:
        if not check_xcodebuildmcp():
            fail("XcodeBuildMCP required for elementRef-based tap")
        result = run_xcodebuildmcp(["ui-automation", "tap", args.element_ref])
        print(result.stdout or result.stderr)
    else:
        x, y = float(args.x), float(args.y)
        offset_x = float(getattr(args, 'offset_x', 0))
        offset_y = float(getattr(args, 'offset_y', 0))
        if offset_x != 0 or offset_y != 0:
            x += offset_x
            y += offset_y
            if offset_y != 0:
                print(f"ℹ️  Applying Y offset {offset_y} for chrome compensation", file=sys.stderr)
        result = run_ax("tap", x=x, y=y)
        if not result.get("success"):
            fail(f"Tap failed: {result.get('error')}")
        ok(f"Tapped at ({x}, {y})")


def cmd_ui_type(args):
    """Type text."""
    require_ax()
    if hasattr(args, 'element_ref') and args.element_ref:
        if not check_xcodebuildmcp():
            fail("XcodeBuildMCP required")
        result = run_xcodebuildmcp(["ui-automation", "type-text", args.element_ref, "--text", args.text])
        print(result.stdout or result.stderr)
    else:
        text = args.text
        result = run_ax("type", text=text)
        if not result.get("success"):
            fail(f"Type failed: {result.get('error')}")
        ok(f"Typed: {repr(text)}")


def cmd_ui_swipe(args):
    """Swipe."""
    if hasattr(args, 'element_ref') and args.element_ref:
        if not check_xcodebuildmcp():
            fail("XcodeBuildMCP required")
        result = run_xcodebuildmcp(["ui-automation", "swipe", args.element_ref, "--direction", args.direction])
        print(result.stdout or result.stderr)
    else:
        require_ax()
        x1, y1, x2, y2 = float(args.x1), float(args.y1), float(args.x2), float(args.y2)
        result = run_ax("swipe", x1=x1, y1=y1, x2=x2, y2=y2)
        if not result.get("success"):
            fail(f"Swipe failed: {result.get('error')}")
        ok(f"Swiped")


def cmd_ui_button(args):
    """Press hardware button."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    result = run_xcodebuildmcp(["ui-automation", "button", args.button])
    print(result.stdout or result.stderr)


def cmd_ui_gesture(args):
    """Simulate gesture."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    result = run_xcodebuildmcp(["ui-automation", "gesture", args.preset])
    print(result.stdout or result.stderr)


def cmd_ui_wait(args):
    """Wait for UI element."""
    if not check_xcodebuildmcp():
        # Fallback to ax-helper
        require_ax()
        result = run_ax("wait", label=args.selector, timeout=args.timeout)
        if result.get("success"):
            ok(f"Found element", result.get("data"))
        else:
            fail(f"Element not found: {result.get('error')}")
        return
    result = run_xcodebuildmcp(["ui-automation", "wait-for-ui", "--predicate", args.selector])
    print(result.stdout or result.stderr)


def cmd_ui_tree(args):
    """Dump accessibility tree. Falls back to OCR if AX tree is empty."""
    require_ax()
    depth = getattr(args, 'depth', 5)
    force_ocr = getattr(args, 'ocr', False)
    ax_only = getattr(args, 'ax_only', False)
    
    if force_ocr:
        # OCR only
        result = run_ax("ocr")
        if not result.get("success"):
            fail(f"OCR failed: {result.get('error')}")
        data = result.get("data", {})
        output_json({"source": "ocr", "texts": data.get("texts", []), "count": data.get("count", 0)})
        if data.get("count", 0) == 0:
            print("⚠️  No text detected on screen", file=sys.stderr)
        return
    
    if ax_only:
        # AX only, no fallback
        result = run_ax("contentTree", maxDepth=depth)
        if not result.get("success"):
            fail(f"Tree failed: {result.get('error')}")
        output_json({"source": "ax", "tree": result.get("data", {})})
        return
    
    # Default: combined AX + OCR fallback
    result = run_ax("treex", maxDepth=depth)
    if not result.get("success"):
        fail(f"Tree failed: {result.get('error')}")
    data = result.get("data", {})
    source = data.get("source", "unknown")
    
    if source == "ocr":
        texts = data.get("texts", [])
        output_json({"source": "ocr", "texts": texts, "count": len(texts)})
        print(f"ℹ️  AX tree was empty — showing OCR text regions ({len(texts)} found)", file=sys.stderr)
        if len(texts) == 0:
            print("⚠️  No text detected on screen. Try a screenshot instead.", file=sys.stderr)
    else:
        output_json({"source": "ax", "tree": data.get("tree", {})})


def cmd_ui_find(args):
    """Find elements by label. Falls back to OCR text search if AX finds nothing."""
    require_ax()
    force_ocr = getattr(args, 'ocr', False)
    ax_only = getattr(args, 'ax_only', False)
    
    if force_ocr:
        # OCR-only find
        result = run_ax("ocr")
        if not result.get("success"):
            fail(f"OCR failed: {result.get('error')}")
        texts = result.get("data", {}).get("texts", [])
        matches = [t for t in texts if args.label.lower() in t.get("text", "").lower()]
        output_json({"source": "ocr", "matches": matches, "count": len(matches), "query": args.label})
        if len(matches) == 0:
            print(f"⚠️  No text matching '{args.label}' found via OCR", file=sys.stderr)
        return
    
    # AX find
    result = run_ax("find", label=args.label)
    if not result.get("success"):
        fail(f"Find failed: {result.get('error')}")
    data = result.get("data", {})
    ax_count = data.get("count", 0)
    
    if ax_count > 0 or ax_only:
        output_json(data)
        if ax_count == 0:
            print(f"⚠️  No elements found matching '{args.label}'", file=sys.stderr)
        return
    
    # AX found nothing → fallback to OCR
    print(f"ℹ️  AX find returned 0 matches — falling back to OCR text search for '{args.label}'", file=sys.stderr)
    result = run_ax("ocr")
    if not result.get("success"):
        fail(f"OCR failed: {result.get('error')}")
    texts = result.get("data", {}).get("texts", [])
    matches = [t for t in texts if args.label.lower() in t.get("text", "").lower()]
    output_json({"source": "ocr", "matches": matches, "count": len(matches), "query": args.label, "ax_fallback_reason": "AX tree empty (Flutter app with disabled semantics?)"})
    if len(matches) == 0:
        print(f"⚠️  No text matching '{args.label}' found via OCR either", file=sys.stderr)
    else:
        print(f"✅ Found {len(matches)} text match(es) via OCR", file=sys.stderr)


def cmd_ui_long_press(args):
    """Long press element."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    result = run_xcodebuildmcp(["ui-automation", "long-press", args.element_ref])
    print(result.stdout or result.stderr)


def cmd_ui_drag(args):
    """Drag element."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    result = run_xcodebuildmcp(["ui-automation", "drag", args.element_ref, "--direction", args.direction])
    print(result.stdout or result.stderr)


def cmd_ui_key_press(args):
    """Press hardware key."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    result = run_xcodebuildmcp(["ui-automation", "key-press", args.key_code])
    print(result.stdout or result.stderr)


# ── Simulator Settings ──────────────────────────────────────────────────────

def cmd_sim_location(args):
    """Set simulated location."""
    coord = f"{args.lat},{args.lng}"
    result = run_simctl(["location", "booted", "set", coord])
    if result.returncode != 0:
        fail(f"Set location failed: {result.stderr}")
    ok(f"Location set to {coord}")


def cmd_sim_location_reset(args):
    """Reset simulated location."""
    result = run_simctl(["location", "booted", "clear"])
    if result.returncode != 0:
        fail(f"Reset location failed: {result.stderr}")
    ok("Location reset")


def cmd_sim_appearance(args):
    """Set appearance (light/dark)."""
    mode = args.mode
    if check_xcodebuildmcp():
        result = run_xcodebuildmcp(["simulator-management", "set-appearance", mode])
        if result.returncode == 0:
            ok(f"Appearance set to {mode}")
            return
    # Fallback
    fail("XcodeBuildMCP required for appearance")


def cmd_sim_statusbar(args):
    """Set status bar overrides."""
    payload = args.payload
    # Payload can be a JSON string or path to JSON file
    if os.path.exists(payload):
        with open(payload) as f:
            payload = f.read()
    # Write to temp file and use simctl
    try:
        # If it's not raw JSON, try parsing as path first (handled above), then validate
        if not payload.startswith('{'):
            payload = json.dumps(json.loads(payload))  # validate + re-serialize
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON payload: {e}")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(payload)
        temp_path = f.name
    result = run_simctl(["status_bar", "booted", "override", "--data", temp_path])
    os.unlink(temp_path)
    if result.returncode != 0:
        fail(f"Status bar override failed: {result.stderr}")
    ok("Status bar overridden")


def cmd_sim_keyboard_connect(args):
    """Toggle hardware keyboard connection."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    result = run_xcodebuildmcp(["simulator-management", "toggle-connect-hardware-keyboard"])
    print(result.stdout or result.stderr)


def cmd_sim_keyboard_software(args):
    """Toggle software keyboard."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP required")
    result = run_xcodebuildmcp(["simulator-management", "toggle-software-keyboard"])
    print(result.stdout or result.stderr)


# ── Other Commands ───────────────────────────────────────────────────────────

def cmd_open(args):
    """Open URL."""
    url = args.url
    result = run_simctl(["openurl", "booted", url])
    if result.returncode != 0:
        fail(f"Open URL failed: {result.stderr}")
    ok(f"Opened URL: {url}")


def cmd_notification(args):
    """Send push notification."""
    payload_path = args.payload
    bundle_id = args.bundle_id
    if not os.path.exists(payload_path):
        fail(f"Payload not found: {payload_path}")
    cmd = ["push", "booted"]
    if bundle_id:
        cmd.append(bundle_id)
    cmd.append(payload_path)
    result = run_simctl(cmd)
    if result.returncode != 0:
        fail(f"Notification failed: {result.stderr}")
    ok("Notification sent")


def cmd_media_add(args):
    """Add media to simulator."""
    path = args.path
    if not os.path.exists(path):
        fail(f"File not found: {path}")
    result = run_simctl(["addmedia", "booted", path])
    if result.returncode != 0:
        fail(f"Add media failed: {result.stderr}")
    ok(f"Media added: {path}")


def cmd_privacy(args):
    """Grant/revoke privacy permission."""
    bundle_id = args.bundle_id
    service = args.service
    action = args.action  # grant | revoke | reset
    if action not in ("grant", "revoke", "reset"):
        fail("Action must be grant, revoke, or reset")
    if action == "grant":
        result = run_simctl(["privacy", "booted", "grant", service, bundle_id])
    elif action == "revoke":
        result = run_simctl(["privacy", "booted", "revoke", service, bundle_id])
    else:
        result = run_simctl(["privacy", "booted", "reset", service, bundle_id])
    if result.returncode != 0:
        fail(f"Privacy {action} failed: {result.stderr}")
    ok(f"Privacy {action}: {service} for {bundle_id}")


def cmd_pasteboard_copy(args):
    """Copy text to simulator pasteboard."""
    text = args.text
    result = subprocess.run(
        ["xcrun", "simctl", "pbcopy", "booted"],
        input=text, capture_output=True, text=True
    )
    if result.returncode != 0:
        fail(f"Pasteboard copy failed: {result.stderr}")
    ok("Text copied to simulator pasteboard")


def cmd_pasteboard_paste(args):
    """Read simulator pasteboard."""
    result = run_simctl(["pbpaste", "booted"])
    if result.returncode != 0:
        fail(f"Pasteboard paste failed: {result.stderr}")
    print(result.stdout)


# ── XcodeBuildMCP Passthrough ────────────────────────────────────────────────

def cmd_xcode(args):
    """Direct XcodeBuildMCP passthrough."""
    if not check_xcodebuildmcp():
        fail("XcodeBuildMCP not found")
    cmd_parts = [args.workflow]
    if args.tool:
        cmd_parts.append(args.tool)
    if args.args:
        cmd_parts.extend(args.args)
    result = run_xcodebuildmcp(cmd_parts, capture=False)
    if result.returncode != 0:
        sys.exit(result.returncode)


# ── Status ───────────────────────────────────────────────────────────────────

def cmd_status(args):
    """Check simulator state."""
    ax = run_ax("check")
    sim_ax_ok = ax.get("data", {}).get("simulatorRunning", False)
    win_ok = ax.get("data", {}).get("mainWindowAvailable", False)
    devices = run_simctl(["list", "devices", "booted"])
    booted_count = devices.stdout.count("Booted")
    xbmcp = check_xcodebuildmcp()
    status = {
        "simulator_app_running": sim_ax_ok,
        "main_window_available": win_ok,
        "booted_devices": booted_count,
        "ax_helper_ok": ax.get("success", False),
        "xcodebuildmcp_available": xbmcp,
        "ready": sim_ax_ok and win_ok and booted_count > 0,
    }
    output_json(status)
    if not status["ready"]:
        if not sim_ax_ok: print("⚠️  Simulator app not running", file=sys.stderr)
        if not win_ok: print("⚠️  No main window (wait for boot)", file=sys.stderr)
        if booted_count == 0: print("⚠️  No booted devices", file=sys.stderr)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="iOS Simulator Control Tool (v2)")
    parser.add_argument("--version", action="version", version="ios-sim v2.0.0")
    subparsers = parser.add_subparsers(dest="command")

    # Device
    p = subparsers.add_parser("device", help="Device management")
    sp = p.add_subparsers(dest="device_action")
    sp.add_parser("list").set_defaults(func=cmd_device_list)
    p_boot = sp.add_parser("boot", help="Boot a device")
    p_boot.add_argument("identifier", help="UDID or name")
    p_boot.set_defaults(func=cmd_device_boot)
    p_shut = sp.add_parser("shutdown", help="Shutdown a device")
    p_shut.add_argument("udid", help="Device UDID")
    p_shut.set_defaults(func=cmd_device_shutdown)
    p_erase = sp.add_parser("erase", help="Erase device")
    p_erase.add_argument("udid", help="Device UDID")
    p_erase.set_defaults(func=cmd_device_erase)
    sp.add_parser("info").set_defaults(func=cmd_device_info)

    # App
    p = subparsers.add_parser("app", help="App management")
    sp = p.add_subparsers(dest="app_action")
    p_inst = sp.add_parser("install", help="Install .app bundle")
    p_inst.add_argument("path", help="Path to .app")
    p_inst.set_defaults(func=cmd_app_install)
    p_lnch = sp.add_parser("launch", help="Launch app")
    p_lnch.add_argument("bundle_id", help="Bundle identifier")
    p_lnch.add_argument("extra_args", nargs="*", help="Extra args")
    p_lnch.set_defaults(func=cmd_app_launch)
    p_term = sp.add_parser("terminate", help="Terminate app")
    p_term.add_argument("bundle_id")
    p_term.set_defaults(func=cmd_app_terminate)
    sp.add_parser("list").set_defaults(func=cmd_app_list)
    p_bid = sp.add_parser("bundle-id", help="Extract bundle ID")
    p_bid.add_argument("path", help="Path to .app")
    p_bid.set_defaults(func=cmd_app_bundle_id)

    # Build
    p = subparsers.add_parser("build", help="Build for simulator")
    p.add_argument("--scheme", help="Xcode scheme")
    p.add_argument("--project", help=".xcodeproj path")
    p.add_argument("--workspace", help=".xcworkspace path")
    p.add_argument("--config", help="Build configuration (Debug/Release)")
    p.add_argument("--extra", nargs="*", help="Extra xcodebuild args")
    p.set_defaults(func=cmd_build)

    p = subparsers.add_parser("build-run", help="Build, install, launch")
    p.add_argument("--scheme")
    p.add_argument("--project")
    p.add_argument("--workspace")
    p.add_argument("--config")
    p.add_argument("--sim", help="Simulator name")
    p.add_argument("--launch-args", nargs="*")
    p.set_defaults(func=cmd_build_run)

    p = subparsers.add_parser("test", help="Test on simulator")
    p.add_argument("--scheme")
    p.add_argument("--project")
    p.add_argument("--workspace")
    p.add_argument("--test-plan")
    p.set_defaults(func=cmd_test)

    p = subparsers.add_parser("discover-projects", help="Find Xcode projects")
    p.add_argument("path", nargs="?", default=".", help="Directory to scan")
    p.set_defaults(func=cmd_discover)

    # Screenshot / Video
    p = subparsers.add_parser("screenshot", help="Take screenshot")
    p.add_argument("output", nargs="?", default=None, help="Output file (omit for base64)")
    p.set_defaults(func=cmd_screenshot)

    p = subparsers.add_parser("video", help="Record video")
    p.add_argument("output", nargs="?", default=None)
    p.set_defaults(func=cmd_video)

    # UI
    p = subparsers.add_parser("ui", help="UI interaction")
    sp = p.add_subparsers(dest="ui_action")
    sp.add_parser("snapshot", help="Take UI snapshot").set_defaults(func=cmd_ui_snapshot)

    p_tap = sp.add_parser("tap", help="Tap at coordinates or element")
    p_tap.add_argument("x", type=float, help="X coordinate")
    p_tap.add_argument("y", type=float, help="Y coordinate")
    p_tap.add_argument("--offset-x", type=float, default=0, help="X offset adjustment (for chrome compensation)")
    p_tap.add_argument("--offset-y", type=float, default=0, help="Y offset adjustment (for chrome compensation)")
    p_tap.set_defaults(func=cmd_ui_tap, element_ref=None)

    p_type = sp.add_parser("type", help="Type text")
    p_type.add_argument("text", help="Text to type")
    p_type.set_defaults(func=cmd_ui_type, element_ref=None)

    p_swipe = sp.add_parser("swipe", help="Swipe gesture")
    p_swipe.add_argument("x1", type=float)
    p_swipe.add_argument("y1", type=float)
    p_swipe.add_argument("x2", type=float)
    p_swipe.add_argument("y2", type=float)
    p_swipe.set_defaults(func=cmd_ui_swipe, element_ref=None)

    p_tree = sp.add_parser("tree", help="Dump accessibility tree (auto-fallback to OCR when AX empty)")
    p_tree.add_argument("--depth", type=int, default=5, help="Max depth (default: 5)")
    p_tree.add_argument("--ax-only", action="store_true", help="Skip OCR fallback, return raw AX tree only")
    p_tree.add_argument("--ocr", action="store_true", help="Force OCR mode (skip AX entirely)")
    p_tree.set_defaults(func=cmd_ui_tree)
    p_find = sp.add_parser("find", help="Find elements by label (auto-fallback to OCR text search)")
    p_find.add_argument("label")
    p_find.add_argument("--ax-only", action="store_true", help="Skip OCR fallback, return raw AX results only")
    p_find.add_argument("--ocr", action="store_true", help="Force OCR mode (skip AX entirely)")
    p_find.set_defaults(func=cmd_ui_find)

    p_wait = sp.add_parser("wait", help="Wait for element")
    p_wait.add_argument("selector")
    p_wait.add_argument("--timeout", type=float, default=10)
    p_wait.set_defaults(func=cmd_ui_wait)

    p_btn = sp.add_parser("button", help="Press hardware button")
    p_btn.add_argument("button", choices=["home", "volumeup", "volumedown", "siri", "lock", "action"])
    p_btn.set_defaults(func=cmd_ui_button)

    p_gesture = sp.add_parser("gesture", help="Simulate gesture")
    p_gesture.add_argument("preset", choices=["shake", "lock", "rotate", "home"])
    p_gesture.set_defaults(func=cmd_ui_gesture)

    p_key = sp.add_parser("key-press", help="Press HID key")
    p_key.add_argument("key_code", help="HID key code (e.g. 40=Enter, 42=Backspace)")
    p_key.set_defaults(func=cmd_ui_key_press)

    # Simulator Settings
    p = subparsers.add_parser("sim", help="Simulator settings")
    sp = p.add_subparsers(dest="sim_action")

    p_loc = sp.add_parser("location", help="Set location")
    p_loc.add_argument("lat", type=float)
    p_loc.add_argument("lng", type=float)
    p_loc.set_defaults(func=cmd_sim_location)

    sp.add_parser("location-reset", help="Reset location").set_defaults(func=cmd_sim_location_reset)

    p_app = sp.add_parser("appearance", help="Set appearance")
    p_app.add_argument("mode", choices=["light", "dark"])
    p_app.set_defaults(func=cmd_sim_appearance)

    p_sb = sp.add_parser("statusbar", help="Override status bar")
    p_sb.add_argument("payload", help="JSON string or path to JSON file")
    p_sb.set_defaults(func=cmd_sim_statusbar)

    sp.add_parser("keyboard-connect", help="Toggle hardware keyboard").set_defaults(func=cmd_sim_keyboard_connect)
    sp.add_parser("keyboard-software", help="Toggle software keyboard").set_defaults(func=cmd_sim_keyboard_software)

    # Other
    p = subparsers.add_parser("open", help="Open URL")
    p.add_argument("url")
    p.set_defaults(func=cmd_open)

    p = subparsers.add_parser("notification", help="Push notification")
    p.add_argument("payload", help="JSON payload file")
    p.add_argument("--bundle-id", help="Target bundle ID")
    p.set_defaults(func=cmd_notification)

    p = subparsers.add_parser("media", help="Add media")
    sp = p.add_subparsers(dest="media_action")
    p_add = sp.add_parser("add", help="Add photo/video")
    p_add.add_argument("path")
    p_add.set_defaults(func=cmd_media_add)

    p = subparsers.add_parser("privacy", help="Privacy permissions")
    p.add_argument("action", choices=["grant", "revoke", "reset"])
    p.add_argument("service", help="e.g. camera, photos, location, microphone")
    p.add_argument("bundle_id", help="Bundle identifier")
    p.set_defaults(func=cmd_privacy)

    p = subparsers.add_parser("pasteboard", help="Pasteboard operations")
    sp = p.add_subparsers(dest="pb_action")
    p_cp = sp.add_parser("copy", help="Copy to sim pasteboard")
    p_cp.add_argument("text")
    p_cp.set_defaults(func=cmd_pasteboard_copy)
    sp.add_parser("paste", help="Read sim pasteboard").set_defaults(func=cmd_pasteboard_paste)

    # XcodeBuildMCP passthrough
    p = subparsers.add_parser("xcode", help="Direct XcodeBuildMCP command")
    p.add_argument("workflow", help="Workflow name (simulator, device, ui-automation, etc.)")
    p.add_argument("tool", nargs="?", help="Tool name")
    p.add_argument("args", nargs="*", help="Tool arguments")
    p.set_defaults(func=cmd_xcode)

    # Status
    p = subparsers.add_parser("status", help="Check state")
    p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, "func"):
        args.func(args)
    else:
        # Subcommand needs a sub-action
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
