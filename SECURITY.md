# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | ✅ |
| < 2.0   | ❌ |

## Reporting a Vulnerability

This tool interacts with the iOS Simulator through Apple's public APIs (`simctl`,
Accessibility API, CoreGraphics). If you find a security issue:

1. **Do not** open a public GitHub issue
2. Email the maintainer, or
3. Open a [security advisory](https://github.com/norbertgrzenkowicz/ios-sim-plugin/security/advisories)

## Scope

This plugin:
- **Does** read/write simulator state via `simctl` and Accessibility APIs
- **Does not** access physical device data, keychains, or Apple ID credentials
- **Does not** transmit any telemetry or usage data
- **Does not** require network access beyond what the simulator itself needs

## Permissions Required

- **Accessibility API**: Required for UI interaction (tap, type, swipe, tree)
- **Xcode Developer Tools**: Required for `simctl` and `xcodebuild` commands
