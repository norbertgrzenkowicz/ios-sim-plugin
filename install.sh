#!/bin/bash
# install.sh — One-command installer for ios-sim-plugin
# Installs the skill for OpenCode, Claude Code, and optionally Codex + CLI.
# Auto-detects which tools you have installed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_FILE="$SCRIPT_DIR/SKILL.md"
CLI_SOURCE="$SCRIPT_DIR/bin/ios-sim.py"
AX_SOURCE="$SCRIPT_DIR/ax-helper-src/main.swift"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     ios-sim-plugin installer             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Detect tools ───────────────────────────────────────────────────────────

detect_openmode() {
  if [ -d "$HOME/.agents/skills" ]; then
    return 0
  fi
  return 1
}

detect_claude() {
  if [ -d "$HOME/.claude/skills" ]; then
    return 0
  fi
  return 1
}

detect_codex() {
  if [ -d "$HOME/.codex/skills/.system" ] || [ -d "$HOME/.codex/skills" ]; then
    return 0
  fi
  return 1
}

detect_mcp_json() {
  # Check if any project has an .mcp.json that could use xcodebuildmcp
  if [ -f "$PWD/.mcp.json" ] || [ -f "$HOME/.claude/mcp.json" ]; then
    return 0
  fi
  return 1
}

detect_node() {
  if command -v node &>/dev/null; then
    return 0
  fi
  return 1
}

detect_xcode() {
  if command -v xcrun &>/dev/null && xcrun --version &>/dev/null 2>&1; then
    return 0
  fi
  return 1
}

# ── Install function ────────────────────────────────────────────────────────

install_skill() {
  local target_dir="$1"
  local tool_name="$2"
  
  mkdir -p "$target_dir/ios-sim"
  if cp "$SKILL_FILE" "$target_dir/ios-sim/SKILL.md"; then
    echo -e "  ${GREEN}✅${NC} Installed skill for $tool_name"
  else
    echo -e "  ${RED}❌${NC} Failed to install for $tool_name"
    return 1
  fi
}

install_cli() {
  local target="/usr/local/bin/ios-sim"
  # Prefer ~/.local/bin if it exists and is in PATH
  if [ -d "$HOME/.local/bin" ]; then
    target="$HOME/.local/bin/ios-sim"
  fi
  
  # Embed the actual install path into the wrapper
  local plugin_dir="$SCRIPT_DIR"
  
  # Create wrapper script with embedded path
  cat > "$target" << WRAPPER
#!/bin/bash
# ios-sim — auto-discovering wrapper (installed from $plugin_dir)
PLUGIN_DIR="$plugin_dir"
SEARCH_PATHS=(
  "\$PLUGIN_DIR"
  "\$PLUGIN_DIR/bin"
  "\$PWD"
  "\$PWD/bin"
)
for path in "\${SEARCH_PATHS[@]}"; do
  if [ -f "\$path/ios-sim.py" ]; then
    exec python3 "\$path/ios-sim.py" "\$@"
  fi
  if [ -f "\$path/bin/ios-sim.py" ]; then
    exec python3 "\$path/bin/ios-sim.py" "\$@"
  fi
done
echo "ios-sim: plugin not found at \$PLUGIN_DIR" >&2
exit 1
WRAPPER
  chmod +x "$target"
  echo -e "  ${GREEN}✅${NC} Installed CLI wrapper to $target"
}

# ── Compile AX helper ───────────────────────────────────────────────────────

compile_ax_helper() {
  if [ ! -f "$AX_SOURCE" ]; then
    echo -e "  ${YELLOW}⚠${NC} AX helper source not found at $AX_SOURCE, skipping"
    return 0
  fi
  
  if ! command -v swift &>/dev/null; then
    echo -e "  ${YELLOW}⚠${NC} Swift not available, skipping AX helper compilation"
    return 0
  fi
  
  local output="$SCRIPT_DIR/bin/ax-helper"
  echo -e "  ${BLUE}ℹ${NC} Compiling AX helper..."
  if swiftc -o "$output" "$AX_SOURCE" 2>/dev/null; then
    chmod +x "$output"
    echo -e "  ${GREEN}✅${NC} AX helper compiled"
  else
    echo -e "  ${YELLOW}⚠${NC} AX helper compilation failed (will compile on first use)"
  fi
}

# ── Main ────────────────────────────────────────────────────────────────────

echo -e "${BLUE}Checking environment...${NC}"

if detect_xcode; then
  echo -e "  ${GREEN}✅${NC} Xcode found"
else
  echo -e "  ${RED}❌${NC} Xcode not found. Install Xcode from the Mac App Store first."
  exit 1
fi

echo ""
echo -e "${BLUE}Installing skill for AI coding tools...${NC}"

INSTALLED=false

if detect_openmode; then
  install_skill "$HOME/.agents/skills" "OpenCode"
  INSTALLED=true
fi

if detect_claude; then
  install_skill "$HOME/.claude/skills" "Claude Code"
  INSTALLED=true
fi

if detect_codex; then
  CODEX_SKILL_DIR="$HOME/.codex/skills/.system"
  # Fallback to .codex/skills if .system doesn't exist
  [ -d "$HOME/.codex/skills/.system" ] || CODEX_SKILL_DIR="$HOME/.codex/skills"
  install_skill "$CODEX_SKILL_DIR" "Codex"
  INSTALLED=true
fi

if [ "$INSTALLED" = false ]; then
  echo -e "  ${YELLOW}⚠${NC} No AI coding tools detected. Installing for OpenCode anyway..."
  mkdir -p "$HOME/.agents/skills"
  install_skill "$HOME/.agents/skills" "OpenCode"
fi

echo ""
echo -e "${BLUE}Installing CLI...${NC}"
install_cli

echo ""
echo -e "${BLUE}Compiling AX helper...${NC}"
compile_ax_helper

# ── opencode.json ───────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}OpenCode config...${NC}"
if [ -f "opencode.json" ]; then
  echo -e "  ${GREEN}✅${NC} opencode.json present (grants ios-sim skill permission)"
fi

# ── Install XcodeBuildMCP hint ──────────────────────────────────────────────

echo ""
if detect_node; then
  if ! command -v xcodebuildmcp &>/dev/null; then
    echo -e "${YELLOW}💡 Install XcodeBuildMCP for build/test/debug features:${NC}"
    echo -e "   npm install -g xcodebuildmcp@latest"
    echo ""
  fi
fi

# ── MCP config hint ─────────────────────────────────────────────────────────

if ! detect_mcp_json; then
  echo -e "${YELLOW}💡 To use XcodeBuildMCP as an MCP server, add this to your .mcp.json:${NC}"
  echo -e "   Copy from: installer/mcp-config.json"
  echo ""
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Installation complete!               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "Try: ${BLUE}ios-sim status${NC}"
echo ""
echo -e "If \`ios-sim\` is not found, add to your shell profile:"
echo -e "  ${YELLOW}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
echo ""
echo -e "For full docs, see: ${BLUE}https://github.com/norbertgrzenkowicz/ios-sim-plugin${NC}"
