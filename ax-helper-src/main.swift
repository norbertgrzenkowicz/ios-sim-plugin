#!/usr/bin/env swift
/// ax-helper — Accessibility helper for iOS Simulator control
/// Communicates via JSON on stdin/stdout.
/// Commands: tree, tap, type, swipe, screenshot, wait
///
/// Usage: swift ax-helper/main.swift
///        Or compile: swiftc -o ax-helper ax-helper/main.swift
///        Then: ./ax-helper < command.json

import Foundation
import ApplicationServices
import AppKit
import Vision

// MARK: - AX Helpers

/// Get the Simulator app's AXUIElement
func getSimulatorApp() -> AXUIElement? {
    let workspace = NSWorkspace.shared
    let apps = workspace.runningApplications
    guard let simApp = apps.first(where: { $0.bundleIdentifier == "com.apple.iphonesimulator" }) else {
        return nil
    }
    return AXUIElementCreateApplication(simApp.processIdentifier)
}

/// Get the AXMainWindow of the Simulator
func getSimulatorMainWindow() -> AXUIElement? {
    guard let app = getSimulatorApp() else { return nil }
    var window: CFTypeRef?
    let err = AXUIElementCopyAttributeValue(app, "AXMainWindow" as CFString, &window)
    guard err == .success, window != nil else { return nil }
    return unsafeBitCast(window!, to: AXUIElement.self)
}

/// Get the iOS content area (the simulated device screen) from the window.
/// First tries the standard `iOSContentGroup` subrole.
/// Falls back to the largest child (by area) which is typically the device screen.
func getIOSContentGroup() -> AXUIElement? {
    guard let window = getSimulatorMainWindow() else { return nil }
    var children: CFTypeRef?
    let err = AXUIElementCopyAttributeValue(window, "AXChildren" as CFString, &children)
    guard err == .success, let childArr = children as? [AXUIElement] else { return nil }
    
    // Primary: match by subrole
    for child in childArr {
        var subrole: CFTypeRef?
        AXUIElementCopyAttributeValue(child, "AXSubrole" as CFString, &subrole)
        if let sub = subrole as? String, sub == "iOSContentGroup" {
            return child
        }
    }
    
    // Fallback: find the largest child by area (heuristic: the device screen
    // is the largest AX element inside the Simulator window)
    var largestChild: AXUIElement?
    var largestArea: Double = 0
    for child in childArr {
        var role: CFTypeRef?
        AXUIElementCopyAttributeValue(child, "AXRole" as CFString, &role)
        
        var size: CFTypeRef?
        if AXUIElementCopyAttributeValue(child, "AXSize" as CFString, &size) == .success,
           let sizeVal = size {
            var cgSize = CGSize.zero
            AXValueGetValue(sizeVal as! AXValue, .cgSize, &cgSize)
            let area = cgSize.width * cgSize.height
            if area > largestArea {
                // Skip likely UI elements (menu bars, toolbars — they're long and thin)
                if cgSize.width > 100 && cgSize.height > 100 {
                    largestArea = area
                    largestChild = child
                }
            }
        }
    }
    return largestChild
}

/// Recursively collect accessibility element info
func collectAXInfo(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 8) -> [String: Any] {
    var info: [String: Any] = [:]
    
    // Basic attributes
    for attr in ["AXRole", "AXSubrole", "AXTitle", "AXDescription", "AXLabel", "AXValue", "AXIdentifier", "AXHelp"] {
        var val: CFTypeRef?
        let err = AXUIElementCopyAttributeValue(element, attr as CFString, &val)
        if err == .success, let v = val {
            if let s = v as? String, !s.isEmpty {
                info[attr] = s
            }
        }
    }
    
    // Check if element is enabled
    var enabled: CFTypeRef?
    if AXUIElementCopyAttributeValue(element, "AXEnabled" as CFString, &enabled) == .success,
       let e = enabled as? Bool {
        info["AXEnabled"] = e
    }
    
    // Position and size
    var position: CFTypeRef?
    var size: CFTypeRef?
    let posErr = AXUIElementCopyAttributeValue(element, "AXPosition" as CFString, &position)
    let sizeErr = AXUIElementCopyAttributeValue(element, "AXSize" as CFString, &size)
    
    if posErr == .success, let posVal = position {
        var point = CGPoint.zero
        AXValueGetValue(posVal as! AXValue, .cgPoint, &point)
        info["x"] = Double(point.x)
        info["y"] = Double(point.y)
    }
    if sizeErr == .success, let sizeVal = size {
        var cgSize = CGSize.zero
        AXValueGetValue(sizeVal as! AXValue, .cgSize, &cgSize)
        info["width"] = Double(cgSize.width)
        info["height"] = Double(cgSize.height)
    }
    
    // Actions
    var actionNames: CFArray?
    if AXUIElementCopyActionNames(element, &actionNames) == .success,
       let actions = actionNames as? [String] {
        info["actions"] = actions
    }
    
    // Recursively collect children (limit depth)
    if depth < maxDepth {
        var children: CFTypeRef?
        let err = AXUIElementCopyAttributeValue(element, "AXChildren" as CFString, &children)
        if err == .success, let childArr = children as? [AXUIElement], !childArr.isEmpty {
            var childInfos: [[String: Any]] = []
            for child in childArr {
                childInfos.append(collectAXInfo(child, depth: depth + 1, maxDepth: maxDepth))
            }
            info["children"] = childInfos
        }
    }
    
    return info
}

/// Find elements matching a predicate
func findElements(_ element: AXUIElement, role: String? = nil, label: String? = nil, depth: Int = 0, maxDepth: Int = 8) -> [[String: Any]] {
    var results: [[String: Any]] = []
    let info = collectAXInfo(element, depth: 0, maxDepth: 0)
    
    var match = true
    if let r = role {
        if info["AXRole"] as? String != r { match = false }
    }
    if let l = label {
        let title = info["AXTitle"] as? String ?? ""
        let desc = info["AXDescription"] as? String ?? ""
        let axLabel = info["AXLabel"] as? String ?? ""
        if !title.contains(l) && !desc.contains(l) && !axLabel.contains(l) { match = false }
    }
    if match {
        results.append(info)
    }
    
    if depth < maxDepth {
        var children: CFTypeRef?
        let err = AXUIElementCopyAttributeValue(element, "AXChildren" as CFString, &children)
        if err == .success, let childArr = children as? [AXUIElement] {
            for child in childArr {
                results.append(contentsOf: findElements(child, role: role, label: label, depth: depth + 1, maxDepth: maxDepth))
            }
        }
    }
    
    return results
}

/// Estimate the chrome offset (title bar + border) of the Simulator.app window.
/// Returns the difference between the main window's top-left corner and the
/// content area's top-left corner in points.
func detectChromeOffset() -> CGPoint {
    guard let window = getSimulatorMainWindow() else { return .zero }
    guard let content = getIOSContentGroup() else { return .zero }
    
    var winPos: CFTypeRef?
    var conPos: CFTypeRef?
    
    let winOk = AXUIElementCopyAttributeValue(window, "AXPosition" as CFString, &winPos) == .success
    let conOk = AXUIElementCopyAttributeValue(content, "AXPosition" as CFString, &conPos) == .success
    
    if winOk, conOk {
        var winOrigin = CGPoint.zero
        var conOrigin = CGPoint.zero
        AXValueGetValue(winPos as! AXValue, .cgPoint, &winOrigin)
        AXValueGetValue(conPos as! AXValue, .cgPoint, &conOrigin)
        return CGPoint(x: conOrigin.x - winOrigin.x, y: conOrigin.y - winOrigin.y)
    }
    // Default chrome offset if AX doesn't cooperate (~19pt title bar + 1pt border)
    return CGPoint(x: 1, y: 19)
}

/// Get the screen-space origin for tap/swipe coordinate translation.
/// Uses the iOSContentGroup position if available, or the main window position
/// plus estimated chrome offset.
func getContentOrigin() -> CGPoint? {
    // Prefer the content group directly
    if let content = getIOSContentGroup() {
        var pos: CFTypeRef?
        if AXUIElementCopyAttributeValue(content, "AXPosition" as CFString, &pos) == .success,
           let posVal = pos {
            var origin = CGPoint.zero
            AXValueGetValue(posVal as! AXValue, .cgPoint, &origin)
            return origin
        }
    }
    // Fallback: main window + chrome offset
    if let window = getSimulatorMainWindow() {
        var pos: CFTypeRef?
        if AXUIElementCopyAttributeValue(window, "AXPosition" as CFString, &pos) == .success,
           let posVal = pos {
            var origin = CGPoint.zero
            AXValueGetValue(posVal as! AXValue, .cgPoint, &origin)
            let chrome = detectChromeOffset()
            return CGPoint(x: origin.x + chrome.x, y: origin.y + chrome.y)
        }
    }
    return nil
}

/// Convert a content-relative point to screen coordinates
func contentToScreen(_ point: CGPoint) -> CGPoint? {
    guard let origin = getContentOrigin() else { return nil }
    return CGPoint(x: origin.x + point.x, y: origin.y + point.y)
}

/// Tap at a point (in simulator screen content coordinates, not window coords)
func tapAtPoint(_ point: CGPoint) -> Bool {
    guard let screenPoint = contentToScreen(point) else { return false }
    
    // Mouse down
    if let downEvent = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: screenPoint, mouseButton: .left) {
        downEvent.post(tap: .cghidEventTap)
    }
    Thread.sleep(forTimeInterval: 0.05)
    // Mouse up
    if let upEvent = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: screenPoint, mouseButton: .left) {
        upEvent.post(tap: .cghidEventTap)
    }
    
    return true
}

/// Perform a swipe/drag gesture
func swipe(from: CGPoint, to: CGPoint, duration: Double = 0.2) -> Bool {
    guard let startPoint = contentToScreen(from),
          let endPoint = contentToScreen(to) else { return false }
    
    // Mouse down
    if let downEvent = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: startPoint, mouseButton: .left) {
        downEvent.post(tap: .cghidEventTap)
    }
    
    // Interpolate for smooth drag
    let steps = max(Int(duration / 0.016), 5)
    for i in 1...steps {
        let t = Double(i) / Double(steps)
        let x = startPoint.x + (endPoint.x - startPoint.x) * t
        let y = startPoint.y + (endPoint.y - startPoint.y) * t
        if let moveEvent = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDragged, mouseCursorPosition: CGPoint(x: x, y: y), mouseButton: .left) {
            moveEvent.post(tap: .cghidEventTap)
        }
        Thread.sleep(forTimeInterval: 0.005)
    }
    
    // Mouse up
    if let upEvent = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: endPoint, mouseButton: .left) {
        upEvent.post(tap: .cghidEventTap)
    }
    
    return true
}

/// Get the center point of the iOS content area
func getContentCenter() -> CGPoint {
    guard let content = getIOSContentGroup() else { return CGPoint(x: 200, y: 400) }
    var size: CFTypeRef?
    let sizeErr = AXUIElementCopyAttributeValue(content, "AXSize" as CFString, &size)
    guard sizeErr == .success, let sizeVal = size else { return CGPoint(x: 200, y: 400) }
    var cgSize = CGSize.zero
    AXValueGetValue(sizeVal as! AXValue, .cgSize, &cgSize)
    return CGPoint(x: cgSize.width / 2, y: cgSize.height / 2)
}

/// Type text using the pasteboard (most reliable for simulator)
func typeText(_ text: String) -> Bool {
    // First, copy text to pasteboard
    let pasteboard = NSPasteboard.general
    pasteboard.clearContents()
    pasteboard.setString(text, forType: .string)
    
    // Give it a moment
    Thread.sleep(forTimeInterval: 0.1)
    
    // Click in the center of the screen to focus
    _ = tapAtPoint(getContentCenter())
    Thread.sleep(forTimeInterval: 0.3)
    
    // Cmd+V to paste
    if let downCmd = CGEvent(keyboardEventSource: nil, virtualKey: 56, keyDown: true) {
        downCmd.post(tap: .cghidEventTap)
    }
    if let downV = CGEvent(keyboardEventSource: nil, virtualKey: 9, keyDown: true) {
        downV.post(tap: .cghidEventTap)
    }
    Thread.sleep(forTimeInterval: 0.05)
    if let upV = CGEvent(keyboardEventSource: nil, virtualKey: 9, keyDown: false) {
        upV.post(tap: .cghidEventTap)
    }
    if let upCmd = CGEvent(keyboardEventSource: nil, virtualKey: 56, keyDown: false) {
        upCmd.post(tap: .cghidEventTap)
    }
    
    return true
}

/// Take a screenshot of the Simulator using simctl
func takeScreenshot() -> String? {
    let tempPath = "/tmp/ax_screenshot_\(UUID().uuidString).png"
    defer { try? FileManager.default.removeItem(atPath: tempPath) }
    
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/xcrun")
    process.arguments = ["simctl", "io", "booted", "screenshot", tempPath]
    process.standardError = FileHandle.nullDevice
    
    do {
        try process.run()
        // 15-second timeout for screenshot
        let deadline = Date().addingTimeInterval(15)
        while process.isRunning && Date() < deadline {
            Thread.sleep(forTimeInterval: 0.1)
        }
        if process.isRunning {
            process.terminate()
            return nil
        }
        
        guard process.terminationStatus == 0,
              let data = try? Data(contentsOf: URL(fileURLWithPath: tempPath)) else {
            return nil
        }
        return data.base64EncodedString()
    } catch {
        return nil
    }
}

/// Wait for an element matching criteria to appear
func waitForElement(label: String, timeout: Double = 5.0) -> [String: Any]? {
    let deadline = Date().addingTimeInterval(timeout)
    while Date() < deadline {
        guard let app = getSimulatorApp() else {
            Thread.sleep(forTimeInterval: 0.5)  // Don't busy-loop if sim not ready
            continue
        }
        let results = findElements(app, label: label)
        if let first = results.first {
            return first
        }
        Thread.sleep(forTimeInterval: 0.3)
    }
    return nil
}

// MARK: - Scale Detection

/// Detect the content scale factor: screenshot pixels ÷ logical points
/// Returns 1.0 if undetermined.
func detectContentScale(screenshotWidth: Int, screenshotHeight: Int) -> Double {
    // Prefer the AX content group size (in logical points)
    if let content = getIOSContentGroup() {
        var size: CFTypeRef?
        if AXUIElementCopyAttributeValue(content, "AXSize" as CFString, &size) == .success,
           let sizeVal = size {
            var cgSize = CGSize.zero
            AXValueGetValue(sizeVal as! AXValue, .cgSize, &cgSize)
            if cgSize.width > 0 {
                return Double(screenshotWidth) / cgSize.width
            }
        }
    }
    // Fallback: main window size minus chrome estimate
    if let window = getSimulatorMainWindow() {
        var size: CFTypeRef?
        if AXUIElementCopyAttributeValue(window, "AXSize" as CFString, &size) == .success,
           let sizeVal = size {
            var cgSize = CGSize.zero
            AXValueGetValue(sizeVal as! AXValue, .cgSize, &cgSize)
            // The window includes chrome (~19pt title bar, ~1pt border each side)
            let contentWidth = cgSize.width - 2  // approx chrome width
            if contentWidth > 0 {
                return Double(screenshotWidth) / contentWidth
            }
        }
    }
    // Last resort: common device scales
    return 2.0
}

// MARK: - Vision OCR

/// Take a screenshot and run OCR via Apple Vision framework.
/// Returns an array of text region dicts with keys:
///   text, confidence, x, y, width, height (in logical point coordinates)
func ocrScreen() -> [[String: Any]] {
    let tempPath = "/tmp/ax_ocr_\(UUID().uuidString).png"
    defer { try? FileManager.default.removeItem(atPath: tempPath) }
    
    // Take screenshot via simctl
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/xcrun")
    process.arguments = ["simctl", "io", "booted", "screenshot", tempPath]
    process.standardError = FileHandle.nullDevice
    
    do {
        try process.run()
        process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            return [["error": "Screenshot failed", "text": ""]]
        }
        
        guard let imageData = try? Data(contentsOf: URL(fileURLWithPath: tempPath)),
              let dataProvider = CGDataProvider(data: imageData as CFData),
              let cgImage = CGImage(pngDataProviderSource: dataProvider, decode: nil, shouldInterpolate: false, intent: .defaultIntent) else {
            return [["error": "Could not load screenshot image", "text": ""]]
        }
        
        let imgWidth = cgImage.width
        let imgHeight = cgImage.height
        let scale = detectContentScale(screenshotWidth: imgWidth, screenshotHeight: imgHeight)
        
        // Run Vision OCR synchronously
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = false
        request.recognitionLanguages = ["en-US"]
        
        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        try handler.perform([request])
        
        guard let observations = request.results else {
            return []
        }
        
        var results: [[String: Any]] = []
        for observation in observations {
            // Get the top candidate (highest confidence text)
            guard let topCandidate = observation.topCandidates(1).first else { continue }
            let text = topCandidate.string
            let confidence = Double(topCandidate.confidence)
            
            // Bounding box in normalized coordinates (0..1, bottom-left origin)
            let bb = observation.boundingBox
            // Convert to top-left origin, pixel coordinates
            let pixelX = bb.minX * CGFloat(imgWidth)
            let pixelY = (1.0 - bb.maxY) * CGFloat(imgHeight)  // top-left
            let pixelW = bb.width * CGFloat(imgWidth)
            let pixelH = bb.height * CGFloat(imgHeight)
            
            // Convert to logical point coordinates
            let ptX = Double(pixelX) / scale
            let ptY = Double(pixelY) / scale
            let ptW = Double(pixelW) / scale
            let ptH = Double(pixelH) / scale
            
            // Only include reasonably confident results (>= 0.3)
            if confidence >= 0.3 {
                results.append([
                    "text": text,
                    "confidence": confidence,
                    "x": ptX,
                    "y": ptY,
                    "width": ptW,
                    "height": ptH,
                    "source": "ocr"
                ])
            }
        }
        
        return results
    } catch {
        return [["error": "OCR failed: \(error.localizedDescription)", "text": ""]]
    }
}

// MARK: - JSON Encoding Helpers

func serializeToJSON(_ value: Any) -> String? {
    if let data = try? JSONSerialization.data(withJSONObject: serializeForJSON(value), options: [.sortedKeys]) {
        return String(data: data, encoding: .utf8)
    }
    return nil
}

func serializeForJSON(_ value: Any) -> Any {
    switch value {
    case let dict as [String: Any]:
        var result: [String: Any] = [:]
        for (k, v) in dict {
            result[k] = serializeForJSON(v)
        }
        return result
    case let arr as [Any]:
        return arr.map { serializeForJSON($0) }
    case let str as String:
        return str
    case let num as Int:
        return num
    case let num as Double:
        return num
    case let num as Float:
        return Double(num)
    case let bool as Bool:
        return bool
    case let data as Data:
        return data.base64EncodedString()
    case is NSNull:
        return NSNull()
    default:
        return String(describing: value)
    }
}

// MARK: - Command Processing

struct Command: Codable {
    let action: String
    let x: Double?
    let y: Double?
    let x1: Double?
    let y1: Double?
    let x2: Double?
    let y2: Double?
    let text: String?
    let role: String?
    let label: String?
    let timeout: Double?
    let maxDepth: Int?
}

// MARK: - Main

func main() {
    // Read command from stdin
    guard let input = readLine(strippingNewline: true) else {
        let resp: [String: Any] = ["success": false, "error": "No input received"]
        print(serializeToJSON(resp) ?? "{\"success\":false}")
        return
    }
    
    guard let cmdData = input.data(using: .utf8),
          let cmd = try? JSONDecoder().decode(Command.self, from: cmdData) else {
        let resp: [String: Any] = ["success": false, "error": "Invalid JSON command"]
        print(serializeToJSON(resp) ?? "{\"success\":false}")
        return
    }
    
    // Ensure accessibility permissions
    let trusted = AXIsProcessTrusted()
    if !trusted {
        let resp: [String: Any] = ["success": false, "error": "Accessibility permissions required. Grant in System Settings > Privacy & Security > Accessibility for Terminal/swift."]
        print(serializeToJSON(resp) ?? "{\"success\":false}")
        return
    }
    
    var response: [String: Any] = ["success": false, "error": "Unknown error"]
    
    switch cmd.action {
    case "check":
        let hasSim = getSimulatorApp() != nil
        let hasWin = getSimulatorMainWindow() != nil
        response = ["success": true, "data": ["simulatorRunning": hasSim, "mainWindowAvailable": hasWin]]
        
    case "tree":
        guard let app = getSimulatorApp() else {
            response = ["success": false, "error": "Simulator not running"]
            break
        }
        let tree = collectAXInfo(app)
        response = ["success": true, "data": ["tree": tree]]
        
    case "contentTree":
        guard let content = getIOSContentGroup() else {
            response = ["success": false, "error": "No iOS content area found"]
            break
        }
        let tree = collectAXInfo(content, maxDepth: cmd.maxDepth ?? 8)
        response = ["success": true, "data": tree]
        
    case "tap":
        guard let x = cmd.x, let y = cmd.y else {
            response = ["success": false, "error": "x and y required"]
            break
        }
        let result = tapAtPoint(CGPoint(x: x, y: y))
        response = ["success": result]
        if !result { response["error"] = "Tap failed" }
        
    case "swipe":
        guard let x1 = cmd.x1, let y1 = cmd.y1, let x2 = cmd.x2, let y2 = cmd.y2 else {
            response = ["success": false, "error": "x1,y1,x2,y2 required"]
            break
        }
        let result = swipe(from: CGPoint(x: x1, y: y1), to: CGPoint(x: x2, y: y2))
        response = ["success": result]
        if !result { response["error"] = "Swipe failed" }
        
    case "type":
        guard let text = cmd.text else {
            response = ["success": false, "error": "text required"]
            break
        }
        let result = typeText(text)
        response = ["success": result]
        if !result { response["error"] = "Type failed" }
        
    case "screenshot":
        guard let b64 = takeScreenshot() else {
            response = ["success": false, "error": "Screenshot failed"]
            break
        }
        response = ["success": true, "data": ["base64": b64]]
        
    case "find":
        guard let app = getSimulatorApp() else {
            response = ["success": false, "error": "Simulator not running"]
            break
        }
        var results = findElements(app, role: cmd.role, label: cmd.label)
        // Also search the main window and content group (app's AXChildren only has menu bar)
        if let window = getSimulatorMainWindow() {
            results.append(contentsOf: findElements(window, role: cmd.role, label: cmd.label))
        }
        if let content = getIOSContentGroup() {
            results.append(contentsOf: findElements(content, role: cmd.role, label: cmd.label))
        }
        response = ["success": true, "data": ["matches": results, "count": results.count]]
        
    case "wait":
        guard let label = cmd.label else {
            response = ["success": false, "error": "label required"]
            break
        }
        let timeout = cmd.timeout ?? 5.0
        if let found = waitForElement(label: label, timeout: timeout) {
            response = ["success": true, "data": ["found": found]]
        } else {
            // Also try searching from content group
            let deadline = Date().addingTimeInterval(timeout)
            while Date() < deadline {
                if let content = getIOSContentGroup() {
                    let results = findElements(content, label: label)
                    if let first = results.first {
                        response = ["success": true, "data": ["found": first]]
                        break
                    }
                }
                Thread.sleep(forTimeInterval: 0.2)
            }
            // If still not found (response wasn't updated in the loop), set error
            if response["success"] as? Bool != true {
                response = ["success": false, "error": "Element not found within timeout"]
            }
        }
        
    case "windowInfo":
        guard let window = getSimulatorMainWindow() else {
            response = ["success": false, "error": "No main window"]
            break
        }
        let info = collectAXInfo(window, maxDepth: 2)
        response = ["success": true, "data": info]
        
    case "ocr":
        let texts = ocrScreen()
        let hasError = texts.first?["error"] != nil
        response = ["success": !hasError, "data": ["texts": texts, "count": texts.count]]
        if hasError { response["error"] = texts.first?["error"] ?? "OCR failed" }
        
    case "treex":
        // Combined tree: AX first, fallback to OCR if empty
        guard let app = getSimulatorApp() else {
            response = ["success": false, "error": "Simulator not running"]
            break
        }
        var axTree = collectAXInfo(app)
        let hasAXChildren = {
            if let children = axTree["children"] as? [[String: Any]], !children.isEmpty {
                return true
            }
            // Check content group directly
            if let content = getIOSContentGroup() {
                let contentInfo = collectAXInfo(content, maxDepth: cmd.maxDepth ?? 4)
                if let c = contentInfo["children"] as? [[String: Any]], !c.isEmpty {
                    axTree = contentInfo
                    return true
                }
            }
            return false
        }()
        
        if hasAXChildren {
            response = ["success": true, "data": ["source": "ax", "tree": axTree]]
        } else {
            // Fallback to OCR
            let texts = ocrScreen()
            let hasError = texts.first?["error"] != nil
            if hasError {
                response = ["success": false, "error": "AX tree empty and OCR failed: \(texts.first?["error"] ?? "unknown")"]
            } else {
                response = ["success": true, "data": ["source": "ocr", "texts": texts, "count": texts.count]]
            }
        }
        
    default:
        response = ["success": false, "error": "Unknown action: \(cmd.action)"]
    }
    
    print(serializeToJSON(response) ?? "{\"success\":false}")
}

main()
