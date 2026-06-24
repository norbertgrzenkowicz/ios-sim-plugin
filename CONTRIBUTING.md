# Contributing to ios-sim-plugin

Thanks for your interest! This project follows standard open-source practices.

## 🔒 No Direct Commits

**Direct commits to `main` are prohibited.** All changes must go through pull requests.
This applies to everyone, including maintainers.

## 🛠️ Development Setup

```bash
git clone https://github.com/norbertgrzenkowicz/ios-sim-plugin.git
cd ios-sim-plugin

# Make the CLI accessible
export PATH="$PWD/bin:$PATH"

# Install optional build tools
npm install -g xcodebuildmcp@latest
```

## 📋 Pull Request Process

1. **Fork the repo** and create your branch from `main`
2. **Test your changes** — run `ios-sim status` to verify core functionality
3. **Update docs** if you add or change commands
4. **Submit a PR** with a clear description of what and why

### PR Checklist

- [ ] Code follows existing style
- [ ] Commands are documented in SKILL.md
- [ ] No breaking changes to existing CLI interface without deprecation notice
- [ ] Error messages are informative

## 🧪 Testing

```bash
# Test device operations
ios-sim device list
ios-sim device info

# Test app operations
ios-sim app list

# Test UI (requires booted simulator with app)
ios-sim status
ios-sim screenshot /tmp/test.png
ios-sim ui tree
```

## 🎯 Code Style

- **Python**: Follow PEP 8. Use type hints for new functions.
- **Swift**: Follow Swift API design guidelines.
- **SKILL.md**: Keep command examples runnable. Test each command before documenting.

## ❓ Questions

Open a [Discussion](https://github.com/norbertgrzenkowicz/ios-sim-plugin/discussions) or
[Issue](https://github.com/norbertgrzenkowicz/ios-sim-plugin/issues).

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
