import UIKit

/// Native module: screen brightness control.
///
/// Operates on UIScreen.main.brightness (0–1).
/// dimBy(fraction:) saves the current level and reduces it by `fraction`.
/// restoreBrightness() brings it back.
@objc(BrightnessModule)
class BrightnessModule: NSObject {

    private var savedBrightness: CGFloat = -1

    @objc static func requiresMainQueueSetup() -> Bool { true }

    // ── get current brightness ───────────────────────────────────────────────

    @objc func getBrightness(
        _ resolve: @escaping RCTPromiseResolveBlock,
        rejecter _: RCTPromiseRejectBlock
    ) {
        DispatchQueue.main.async {
            resolve(Double(UIScreen.main.brightness))
        }
    }

    // ── set absolute brightness ──────────────────────────────────────────────

    @objc func setBrightness(
        _ brightness: Float,
        resolver resolve: @escaping RCTPromiseResolveBlock,
        rejecter _: RCTPromiseRejectBlock
    ) {
        DispatchQueue.main.async {
            UIScreen.main.brightness = CGFloat(max(0, min(1, brightness)))
            resolve(nil)
        }
    }

    // ── dim by relative fraction (saves for restore) ─────────────────────────

    @objc func dimBy(
        _ fraction: Float,
        resolver resolve: @escaping RCTPromiseResolveBlock,
        rejecter _: RCTPromiseRejectBlock
    ) {
        DispatchQueue.main.async {
            let current = UIScreen.main.brightness
            self.savedBrightness = current
            let target = max(0.05, current * CGFloat(1 - fraction))
            UIScreen.main.brightness = target
            resolve(Double(target))
        }
    }

    // ── restore saved brightness ─────────────────────────────────────────────

    @objc func restoreBrightness(
        _ resolve: @escaping RCTPromiseResolveBlock,
        rejecter _: RCTPromiseRejectBlock
    ) {
        guard savedBrightness >= 0 else { resolve(nil); return }
        let saved = savedBrightness
        savedBrightness = -1
        DispatchQueue.main.async {
            UIScreen.main.brightness = saved
            resolve(nil)
        }
    }
}
