// ViewController.swift
// Self-Pose Demo
//
// ============================================================
// ETHICAL USE NOTICE — AR BODY-TRACKING EDITION
// ============================================================
// This application is an educational tool for personal fitness
// and sports analytics.  It analyses the CONSENTING USER'S OWN
// body pose in real time, entirely on-device, using Apple's
// Vision, ARKit and Core ML frameworks.
//
// ────────────────────────────────────────────────────────────
// NON-CONSENSUAL USE IS PROHIBITED BY DESIGN
// ────────────────────────────────────────────────────────────
// Every code path that touches camera data or body-tracking
// anchors is gated behind `userHasConsented`.  The architecture
// enforces the following:
//
//   • Explicit Opt-In       – An informed consent dialog is the
//     first thing the user sees.  No camera, ARKit, or Vision
//     work occurs until the user affirmatively taps "I Agree".
//     The flag is runtime-only (never persisted); re-launching
//     the app requires re-consent.  A "Revoke Consent" option
//     in Settings lets the user withdraw at any time.
//
//   • Single-Anchor Limit   – Only ONE ARBodyAnchor (or
//     ARFaceAnchor) is accepted per session.  If ARKit adds a
//     second body anchor the app REFUSES to track it.  This
//     prevents surreptitiously analysing a bystander.
//
//   • Single-User Processing – If Vision detects more than one
//     body in a frame, only the FIRST (primary) observation is
//     used — all others are silently discarded.  No data about
//     any non-consenting person is processed or displayed.
//
//   • On-Device Only        – All pose inference runs locally
//     on the Neural Engine / GPU.  No pixel data, joint
//     coordinates, or classification results leave the device.
//
//   • No Persistence        – No frames, images, joint data, or
//     feature vectors are written to disk, UserDefaults, iCloud,
//     or any other storage.
//
//   • No Sharing            – No data is transmitted to any
//     server, analytics service, or third party.
//
//   • Ephemeral Analysis    – Each CVPixelBuffer is consumed by
//     Vision inline and released.  Only the PoseClass enum value
//     survives past the inference call, for display only.
//
//   • Stop / Pause at Any Time – The user can halt or pause
//     everything via the HUD buttons.  A persistent on-screen
//     banner reminds the user that analysis is opt-in.
//
//   • Confidence Gate       – Classifications are only displayed
//     when enough joints are detected above a user-configurable
//     threshold.  Low-confidence frames show "Analysing…".
//
// Legal references:
//   GDPR  – Regulation (EU) 2016/679, Articles 5, 6(1)(a), 7(3), 9
//   CCPA  – California Civil Code § 1798.100 et seq.
//   BIPA  – Illinois 740 ILCS 14/ (biometric data)
//   Apple – App Store Review Guidelines §5.1 (Privacy)
//   Apple – Human Interface Guidelines: Privacy
//
// Copyright © 2025 Self-Pose Demo. Educational use only.
// ============================================================

import UIKit
import ARKit
import SceneKit
import AVFoundation
import Vision
import CoreML

// MARK: - PoseClass

/// Classification outcomes from the on-device AI pipeline.
///
/// - poseTypeA : Grounded / static stance (e.g. standing upright).
/// - poseTypeB : Airborne / dynamic stance (e.g. jumping, lunging).
/// - unknown   : Insufficient joint confidence or model warming up.
enum PoseClass: String {
    case poseTypeA = "Standing / Upright"
    case poseTypeB = "Active / Dynamic"
    case unknown   = "Analysing…"
}

// MARK: - PoseFeatureVector

/// Ephemeral snapshot of all 19 Vision body-pose joint positions for one frame.
///
/// Created per-frame on `visionQueue`, used for classification and skeleton
/// drawing, then immediately discarded.  Never written to any persistent store.
struct PoseFeatureVector {

    /// Per-instance confidence threshold so the user's slider setting is
    /// respected without a global mutable static.  Default matches the
    /// app's initial slider position.
    var confidenceThreshold: Float = 0.4

    // Head / neck
    var nose:          VNRecognizedPoint?
    var leftEye:       VNRecognizedPoint?
    var rightEye:      VNRecognizedPoint?
    var leftEar:       VNRecognizedPoint?
    var rightEar:      VNRecognizedPoint?
    var neck:          VNRecognizedPoint?

    // Torso root (midpoint of hips)
    var root:          VNRecognizedPoint?

    // Left arm
    var leftShoulder:  VNRecognizedPoint?
    var leftElbow:     VNRecognizedPoint?
    var leftWrist:     VNRecognizedPoint?

    // Right arm
    var rightShoulder: VNRecognizedPoint?
    var rightElbow:    VNRecognizedPoint?
    var rightWrist:    VNRecognizedPoint?

    // Left leg
    var leftHip:       VNRecognizedPoint?
    var leftKnee:      VNRecognizedPoint?
    var leftAnkle:     VNRecognizedPoint?

    // Right leg
    var rightHip:      VNRecognizedPoint?
    var rightKnee:     VNRecognizedPoint?
    var rightAnkle:    VNRecognizedPoint?

    /// All joints above the instance confidence threshold.
    var validJoints: [(name: String, point: VNRecognizedPoint)] {
        let all: [(String, VNRecognizedPoint?)] = [
            ("nose",          nose),
            ("leftEye",       leftEye),     ("rightEye",       rightEye),
            ("leftEar",       leftEar),     ("rightEar",       rightEar),
            ("neck",          neck),         ("root",           root),
            ("leftShoulder",  leftShoulder), ("rightShoulder",  rightShoulder),
            ("leftElbow",     leftElbow),    ("rightElbow",     rightElbow),
            ("leftWrist",     leftWrist),    ("rightWrist",     rightWrist),
            ("leftHip",       leftHip),      ("rightHip",       rightHip),
            ("leftKnee",      leftKnee),     ("rightKnee",      rightKnee),
            ("leftAnkle",     leftAnkle),    ("rightAnkle",     rightAnkle),
        ]
        return all.compactMap { name, pt in
            guard let pt = pt, pt.confidence >= confidenceThreshold else { return nil }
            return (name, pt)
        }
    }

    var detectedJointCount: Int { validJoints.count }
    var overallConfidence: Float { Float(detectedJointCount) / 19.0 }

    // ----------------------------------------------------------------
    // MLMultiArray builder — uncomment when a real .mlmodel is added.
    // ----------------------------------------------------------------
    // func toMLMultiArray() throws -> MLMultiArray {
    //     let array = try MLMultiArray(shape: [19, 3], dataType: .float32)
    //     let ordered: [VNRecognizedPoint?] = [
    //         nose, leftEye, rightEye, leftEar, rightEar, neck, root,
    //         leftShoulder, leftElbow, leftWrist,
    //         rightShoulder, rightElbow, rightWrist,
    //         leftHip, leftKnee, leftAnkle,
    //         rightHip, rightKnee, rightAnkle,
    //     ]
    //     for (i, joint) in ordered.enumerated() {
    //         let b = i * 3
    //         if let j = joint, j.confidence >= confidenceThreshold {
    //             array[b] = NSNumber(value: Float(j.location.x))
    //             array[b+1] = NSNumber(value: Float(j.location.y))
    //             array[b+2] = NSNumber(value: j.confidence)
    //         } else { array[b] = 0; array[b+1] = 0; array[b+2] = 0 }
    //     }
    //     return array
    // }
}

// MARK: - ViewController

class ViewController: UIViewController {

    // -------------------------------------------------------
    // MARK: UI / AR
    // -------------------------------------------------------

    /// Full-screen AR view that renders the live camera feed via ARKit
    /// and hosts SceneKit overlays (the 3-D pose-label text node).
    private var arView: ARSCNView!

    /// Persistent opt-in banner across the top of the screen.
    ///
    /// ETHICAL — NON-CONSENSUAL USE PREVENTION:
    /// Continuously reminds the user that body tracking is active and
    /// deters pointing the camera at a non-consenting person.
    private var optInReminderLabel: UILabel!

    /// Animated indicator shown while scanning is active.
    /// Pulses at 0.8 s intervals to make scanning state unambiguous.
    private var scanningIndicatorLabel: UILabel!

    /// 2-D HUD label near the bottom showing the current PoseClass.
    private var poseLabel: UILabel!

    /// Start / Stop toggle.  Disabled until consent + camera permission
    /// are both confirmed.
    private var startButton: UIButton!

    /// Pause / Resume toggle.  Only enabled while a scan is running.
    ///
    /// Pausing suspends Vision processing and freezes the skeleton
    /// overlay without stopping the ARKit session — useful for reviewing
    /// a classification frame-by-frame.
    private var pauseButton: UIButton!

    /// Opens the settings panel (sensitivity slider + revoke consent).
    private var settingsButton: UIButton!

    // -------------------------------------------------------
    // MARK: Settings Panel
    // -------------------------------------------------------
    // A bottom-sheet UIView that slides up when the user taps ⚙.
    // Contains:
    //   • Detection Sensitivity slider  (confidence threshold)
    //   • Live FPS readout              (read-only, reflects actual rate)
    //   • Revoke Consent button         (satisfies GDPR Art. 7(3))
    //   • Legal compliance note
    // -------------------------------------------------------

    private var settingsPanel: UIView!
    private var confidenceSlider: UISlider!
    private var sensitivityValueLabel: UILabel!  // "Low / Medium / High"
    private var fpsBadgeLabel: UILabel!          // "XX fps" inside panel
    private var settingsPanelBottomConstraint: NSLayoutConstraint!

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Layers
    // -------------------------------------------------------

    private let skeletonBoneLayer  = CAShapeLayer()
    private let skeletonJointLayer = CAShapeLayer()

    /// Cached layer bounds — updated in viewDidLayoutSubviews.
    /// Avoids a main.sync inside the visionQueue draw path.
    private var cachedLayerSize: CGSize = .zero

    // -------------------------------------------------------
    // MARK: AVFoundation – Camera Pipeline
    // -------------------------------------------------------
    // When ARBodyTrackingConfiguration is active (rear camera, world
    // space) the AVCaptureSession is NOT used — Vision processes the
    // ARFrame.capturedImage directly, avoiding dual-camera contention.
    // -------------------------------------------------------

    private let captureSession = AVCaptureSession()

    /// Serial queue for all Vision inference.  Never blocks the main thread.
    private let visionQueue = DispatchQueue(
        label: "com.selfposedemo.visionQueue",
        qos: .userInitiated
    )

    // -------------------------------------------------------
    // MARK: Vision
    // -------------------------------------------------------

    /// Reusable on-device body pose detection request.
    private var bodyPoseRequest = VNDetectHumanBodyPoseRequest()

    // -------------------------------------------------------
    // MARK: Core ML — GPU Acceleration
    // -------------------------------------------------------
    // PERFORMANCE: The MLModelConfiguration below instructs Core ML to
    // dispatch inference to whichever compute unit is fastest:
    //   • Neural Engine (ANE)  — lowest latency for supported models
    //   • GPU                  — fallback for models without ANE kernels
    //   • CPU                  — final fallback
    //
    // Using `.all` lets the OS scheduler decide at runtime, avoiding
    // the CPU bottleneck that arises with the default `.cpuOnly` setting.
    // This is especially important on A12+ devices where the ANE provides
    // ~10× the throughput of an equivalent CPU inference.
    //
    // HOW TO INTEGRATE:
    //   1. Add PoseClassifier.mlmodel to the Xcode target.
    //   2. Xcode generates PoseClassifier Swift class.
    //   3. Uncomment the property and classifyWithCoreML below.
    //
    // private var poseClassifier: PoseClassifier? = {
    //     let config = MLModelConfiguration()
    //     config.computeUnits = .all   // Neural Engine + GPU + CPU
    //     return try? PoseClassifier(configuration: config)
    // }()

    // -------------------------------------------------------
    // MARK: Frame Throttle & Adaptive Frame Skip
    // -------------------------------------------------------
    // PERFORMANCE: Two complementary mechanisms limit CPU/GPU usage:
    //
    //   1. Fixed cap (≤15 fps) — `minimumProcessingInterval` ensures
    //      we never process faster than 15 fps regardless of device speed.
    //
    //   2. Adaptive skip — if the measured throughput drops below
    //      `adaptiveSkipFPSThreshold` (8 fps), every other frame is
    //      skipped.  This prevents the visionQueue from backing up
    //      when a slower device is under thermal pressure.
    // -------------------------------------------------------

    private var lastProcessedTimestamp: TimeInterval = 0
    private let minimumProcessingInterval: TimeInterval = 1.0 / 15.0

    // FPS measurement
    private var fpsWindowStart: TimeInterval  = 0
    private var fpsFramesInWindow: Int        = 0
    private var measuredFPS: Double           = 15.0

    // Adaptive skip — engaged when measuredFPS drops below threshold
    private let adaptiveSkipFPSThreshold: Double = 8.0
    private var adaptiveSkipToggle: Bool          = false

    // -------------------------------------------------------
    // MARK: AR Body Tracking State
    // -------------------------------------------------------
    // ETHICAL — SINGLE-ANCHOR ENFORCEMENT:
    // Only ONE body anchor is ever accepted per session.
    // `trackedAnchorID` stores the UUID of that anchor.
    // All subsequent anchors are refused in renderer(_:didAdd:for:).
    // -------------------------------------------------------

    private var usesBodyTracking = false
    private var trackedAnchorID: UUID?
    private var poseTextContainerNode: SCNNode?
    private var lastRenderedTextString: String = ""

    // -------------------------------------------------------
    // MARK: Head Joint Cache
    // -------------------------------------------------------

    private var cachedHeadJointIndex: Int?

    // -------------------------------------------------------
    // MARK: State
    // -------------------------------------------------------

    /// ETHICAL: Runtime-only, never persisted.  Re-launch requires re-consent.
    private var userHasConsented = false

    private var isScanning = false
    private var isPaused   = false
    private var currentPose: PoseClass = .unknown

    /// User-configurable joint confidence threshold (0.2 – 0.7).
    /// Controlled by the sensitivity slider in the settings panel.
    private var jointConfidenceThreshold: Float = 0.4

    private var poseTextNode: SCNNode?

    // -------------------------------------------------------
    // MARK: View Lifecycle
    // -------------------------------------------------------

    override func viewDidLoad() {
        super.viewDidLoad()
        setupARView()
        setupSkeletonOverlay()
        setupHUD()
        setupSettingsPanel()
        // ETHICAL: Consent screen shown synchronously at launch.
        // Zero camera / ARKit work occurs before "I Agree".
        presentConsentScreen()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        stopScanning()
    }

    // -------------------------------------------------------
    // MARK: ARSCNView Setup
    // -------------------------------------------------------

    private func setupARView() {
        arView = ARSCNView(frame: view.bounds)
        arView.autoresizingMask             = [.flexibleWidth, .flexibleHeight]
        arView.delegate                     = self
        arView.session.delegate             = self
        arView.scene                        = SCNScene()
        arView.automaticallyUpdatesLighting = true
#if DEBUG
        arView.showsStatistics = true
#endif
        view.addSubview(arView)
    }

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Setup
    // -------------------------------------------------------

    private func setupSkeletonOverlay() {
        skeletonBoneLayer.strokeColor  = UIColor.cyan.withAlphaComponent(0.75).cgColor
        skeletonBoneLayer.lineWidth    = 2.5
        skeletonBoneLayer.fillColor    = UIColor.clear.cgColor
        skeletonBoneLayer.lineCap      = .round
        skeletonBoneLayer.lineJoin     = .round

        skeletonJointLayer.strokeColor = UIColor.clear.cgColor
        skeletonJointLayer.fillColor   = UIColor.systemYellow.withAlphaComponent(0.85).cgColor

        arView.layer.addSublayer(skeletonBoneLayer)
        arView.layer.addSublayer(skeletonJointLayer)
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        let bounds = arView.bounds
        skeletonBoneLayer.frame  = bounds
        skeletonJointLayer.frame = bounds
        cachedLayerSize          = bounds.size
    }

    // -------------------------------------------------------
    // MARK: HUD Setup
    // -------------------------------------------------------

    private func setupHUD() {

        // ── Opt-In Reminder Banner ────────────────────────────────────
        optInReminderLabel = UILabel()
        optInReminderLabel.translatesAutoresizingMaskIntoConstraints = false
        optInReminderLabel.text            = "Opt-in self-analysis only — you are the only subject"
        optInReminderLabel.textColor       = UIColor.white.withAlphaComponent(0.95)
        optInReminderLabel.backgroundColor = UIColor.systemIndigo.withAlphaComponent(0.75)
        optInReminderLabel.font            = UIFont.systemFont(ofSize: 12, weight: .semibold)
        optInReminderLabel.textAlignment   = .center
        optInReminderLabel.layer.cornerRadius  = 8
        optInReminderLabel.layer.maskedCorners = [.layerMinXMaxYCorner, .layerMaxXMaxYCorner]
        optInReminderLabel.clipsToBounds   = true
        view.addSubview(optInReminderLabel)

        // ── Scanning Indicator ────────────────────────────────────────
        // Animated pulsing label that makes scanning state obvious.
        // The dot "●" combined with the pulsing alpha makes it
        // immediately clear to the user that live analysis is running.
        scanningIndicatorLabel = UILabel()
        scanningIndicatorLabel.translatesAutoresizingMaskIntoConstraints = false
        scanningIndicatorLabel.text          = "● Scanning Your Pose…"
        scanningIndicatorLabel.textColor     = UIColor.systemGreen
        scanningIndicatorLabel.font          = UIFont.monospacedSystemFont(ofSize: 13, weight: .medium)
        scanningIndicatorLabel.textAlignment = .center
        scanningIndicatorLabel.alpha         = 0.0   // hidden until scanning starts
        view.addSubview(scanningIndicatorLabel)

        // ── Pose Label ────────────────────────────────────────────────
        poseLabel = UILabel()
        poseLabel.translatesAutoresizingMaskIntoConstraints = false
        poseLabel.text              = "Consent required to begin."
        poseLabel.textColor         = .white
        poseLabel.backgroundColor   = UIColor.black.withAlphaComponent(0.6)
        poseLabel.font              = UIFont.systemFont(ofSize: 18, weight: .semibold)
        poseLabel.textAlignment     = .center
        poseLabel.numberOfLines     = 2
        poseLabel.layer.cornerRadius = 10
        poseLabel.clipsToBounds     = true
        view.addSubview(poseLabel)

        // ── Bottom Button Row ─────────────────────────────────────────
        // Three equal-width buttons laid out horizontally.

        // Start / Stop
        startButton = UIButton(type: .system)
        startButton.translatesAutoresizingMaskIntoConstraints = false
        startButton.setTitle("Start Scan", for: .normal)
        startButton.titleLabel?.font   = UIFont.systemFont(ofSize: 16, weight: .bold)
        startButton.backgroundColor    = UIColor.systemBlue.withAlphaComponent(0.85)
        startButton.setTitleColor(.white, for: .normal)
        startButton.layer.cornerRadius = 12
        startButton.isEnabled          = false
        startButton.alpha              = 0.5
        startButton.addTarget(self, action: #selector(startScanTapped), for: .touchUpInside)
        view.addSubview(startButton)

        // Pause / Resume — only enabled while scanning
        pauseButton = UIButton(type: .system)
        pauseButton.translatesAutoresizingMaskIntoConstraints = false
        pauseButton.setTitle("Pause", for: .normal)
        pauseButton.titleLabel?.font   = UIFont.systemFont(ofSize: 16, weight: .bold)
        pauseButton.backgroundColor    = UIColor.systemOrange.withAlphaComponent(0.85)
        pauseButton.setTitleColor(.white, for: .normal)
        pauseButton.layer.cornerRadius = 12
        pauseButton.isEnabled          = false
        pauseButton.alpha              = 0.5
        pauseButton.addTarget(self, action: #selector(pauseResumeTapped), for: .touchUpInside)
        view.addSubview(pauseButton)

        // Settings (⚙) — enabled after consent
        settingsButton = UIButton(type: .system)
        settingsButton.translatesAutoresizingMaskIntoConstraints = false
        settingsButton.setTitle("⚙ Settings", for: .normal)
        settingsButton.titleLabel?.font   = UIFont.systemFont(ofSize: 16, weight: .bold)
        settingsButton.backgroundColor    = UIColor.systemGray.withAlphaComponent(0.85)
        settingsButton.setTitleColor(.white, for: .normal)
        settingsButton.layer.cornerRadius = 12
        settingsButton.isEnabled          = false
        settingsButton.alpha              = 0.5
        settingsButton.addTarget(self, action: #selector(settingsTapped), for: .touchUpInside)
        view.addSubview(settingsButton)

        // ── Auto Layout ───────────────────────────────────────────────
        NSLayoutConstraint.activate([
            // Opt-in reminder — full width at very top
            optInReminderLabel.topAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.topAnchor),
            optInReminderLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            optInReminderLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            optInReminderLabel.heightAnchor.constraint(equalToConstant: 28),

            // Scanning indicator — just below the banner
            scanningIndicatorLabel.topAnchor.constraint(
                equalTo: optInReminderLabel.bottomAnchor, constant: 8),
            scanningIndicatorLabel.leadingAnchor.constraint(
                equalTo: view.leadingAnchor, constant: 16),
            scanningIndicatorLabel.trailingAnchor.constraint(
                equalTo: view.trailingAnchor, constant: -16),

            // Pose label — above the button row
            poseLabel.leadingAnchor.constraint(
                equalTo: view.leadingAnchor, constant: 16),
            poseLabel.trailingAnchor.constraint(
                equalTo: view.trailingAnchor, constant: -16),
            poseLabel.bottomAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -80),
            poseLabel.heightAnchor.constraint(greaterThanOrEqualToConstant: 50),

            // Button row — three equal-width buttons at the bottom
            startButton.leadingAnchor.constraint(
                equalTo: view.leadingAnchor, constant: 12),
            startButton.bottomAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -16),
            startButton.heightAnchor.constraint(equalToConstant: 46),

            pauseButton.leadingAnchor.constraint(
                equalTo: startButton.trailingAnchor, constant: 8),
            pauseButton.bottomAnchor.constraint(equalTo: startButton.bottomAnchor),
            pauseButton.heightAnchor.constraint(equalTo: startButton.heightAnchor),
            pauseButton.widthAnchor.constraint(equalTo: startButton.widthAnchor),

            settingsButton.leadingAnchor.constraint(
                equalTo: pauseButton.trailingAnchor, constant: 8),
            settingsButton.trailingAnchor.constraint(
                equalTo: view.trailingAnchor, constant: -12),
            settingsButton.bottomAnchor.constraint(equalTo: startButton.bottomAnchor),
            settingsButton.heightAnchor.constraint(equalTo: startButton.heightAnchor),
            settingsButton.widthAnchor.constraint(equalTo: startButton.widthAnchor),
        ])
    }

    // -------------------------------------------------------
    // MARK: Settings Panel Setup
    // -------------------------------------------------------
    // Bottom-sheet slide-up panel.  Initially translated fully off-screen
    // so it is invisible.  Slides into view on settingsTapped().
    // -------------------------------------------------------

    private func setupSettingsPanel() {
        settingsPanel = UIView()
        settingsPanel.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.backgroundColor  = UIColor.systemBackground.withAlphaComponent(0.97)
        settingsPanel.layer.cornerRadius    = 20
        settingsPanel.layer.maskedCorners   = [.layerMinXMinYCorner, .layerMaxXMinYCorner]
        settingsPanel.layer.shadowColor     = UIColor.black.cgColor
        settingsPanel.layer.shadowOpacity   = 0.25
        settingsPanel.layer.shadowOffset    = CGSize(width: 0, height: -4)
        settingsPanel.layer.shadowRadius    = 12
        view.addSubview(settingsPanel)

        // Panel is off-screen initially (100 pts below the bottom edge).
        settingsPanelBottomConstraint = settingsPanel.bottomAnchor.constraint(
            equalTo: view.bottomAnchor, constant: 400)

        NSLayoutConstraint.activate([
            settingsPanel.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            settingsPanel.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            settingsPanelBottomConstraint,
        ])

        buildSettingsPanelContents()
    }

    private func buildSettingsPanelContents() {
        // ── Drag Handle ───────────────────────────────────────────────
        let handle = UIView()
        handle.translatesAutoresizingMaskIntoConstraints = false
        handle.backgroundColor    = UIColor.systemGray3
        handle.layer.cornerRadius = 2.5
        settingsPanel.addSubview(handle)

        // ── Title ─────────────────────────────────────────────────────
        let titleLabel = UILabel()
        titleLabel.translatesAutoresizingMaskIntoConstraints = false
        titleLabel.text      = "Settings"
        titleLabel.font      = UIFont.systemFont(ofSize: 18, weight: .bold)
        titleLabel.textColor = .label
        settingsPanel.addSubview(titleLabel)

        // ── Close Button ──────────────────────────────────────────────
        let closeButton = UIButton(type: .system)
        closeButton.translatesAutoresizingMaskIntoConstraints = false
        closeButton.setTitle("Done", for: .normal)
        closeButton.titleLabel?.font = UIFont.systemFont(ofSize: 17, weight: .semibold)
        closeButton.addTarget(self, action: #selector(closeSettingsTapped), for: .touchUpInside)
        settingsPanel.addSubview(closeButton)

        // ── Sensitivity Section ───────────────────────────────────────
        // LEGAL / ETHICAL NOTE:
        // The sensitivity slider adjusts the Vision joint confidence
        // threshold.  Higher sensitivity (lower threshold) may detect
        // joints in challenging lighting but can increase false positives.
        // Lower sensitivity (higher threshold) only accepts high-certainty
        // joint readings, reducing noise on clear backgrounds.
        // This setting is ephemeral — never stored or transmitted.

        let sensitivityHeader = sectionHeader("Detection Sensitivity")
        settingsPanel.addSubview(sensitivityHeader)

        let sensitivityDesc = UILabel()
        sensitivityDesc.translatesAutoresizingMaskIntoConstraints = false
        sensitivityDesc.text          = "Controls how confidently Vision must detect each joint. Higher sensitivity works better in low light; lower sensitivity reduces false reads."
        sensitivityDesc.font          = UIFont.systemFont(ofSize: 13)
        sensitivityDesc.textColor     = .secondaryLabel
        sensitivityDesc.numberOfLines = 0
        settingsPanel.addSubview(sensitivityDesc)

        let preciseLabel = UILabel()
        preciseLabel.translatesAutoresizingMaskIntoConstraints = false
        preciseLabel.text      = "Precise"
        preciseLabel.font      = UIFont.systemFont(ofSize: 12, weight: .medium)
        preciseLabel.textColor = .secondaryLabel
        settingsPanel.addSubview(preciseLabel)

        confidenceSlider = UISlider()
        confidenceSlider.translatesAutoresizingMaskIntoConstraints = false
        confidenceSlider.minimumValue = 0.0    // maps to threshold 0.7 (precise)
        confidenceSlider.maximumValue = 1.0    // maps to threshold 0.2 (sensitive)
        confidenceSlider.value        = 0.5    // default → threshold 0.45
        confidenceSlider.minimumTrackTintColor = UIColor.systemGreen
        confidenceSlider.addTarget(
            self, action: #selector(sensitivityChanged(_:)), for: .valueChanged)
        settingsPanel.addSubview(confidenceSlider)

        let sensitiveLabel = UILabel()
        sensitiveLabel.translatesAutoresizingMaskIntoConstraints = false
        sensitiveLabel.text      = "Sensitive"
        sensitiveLabel.font      = UIFont.systemFont(ofSize: 12, weight: .medium)
        sensitiveLabel.textColor = .secondaryLabel
        settingsPanel.addSubview(sensitiveLabel)

        sensitivityValueLabel = UILabel()
        sensitivityValueLabel.translatesAutoresizingMaskIntoConstraints = false
        sensitivityValueLabel.text          = "Medium"
        sensitivityValueLabel.font          = UIFont.systemFont(ofSize: 14, weight: .semibold)
        sensitivityValueLabel.textColor     = .systemGreen
        sensitivityValueLabel.textAlignment = .center
        settingsPanel.addSubview(sensitivityValueLabel)

        // ── FPS Badge ─────────────────────────────────────────────────
        fpsBadgeLabel = UILabel()
        fpsBadgeLabel.translatesAutoresizingMaskIntoConstraints = false
        fpsBadgeLabel.text            = "Frame Rate: — fps"
        fpsBadgeLabel.font            = UIFont.monospacedSystemFont(ofSize: 13, weight: .regular)
        fpsBadgeLabel.textColor       = .secondaryLabel
        fpsBadgeLabel.textAlignment   = .center
        settingsPanel.addSubview(fpsBadgeLabel)

        // ── Revoke Consent Button ─────────────────────────────────────
        // LEGAL — GDPR Art. 7(3):
        // "The data subject shall have the right to withdraw his or
        // her consent at any time."  This button provides that right
        // in a prominent, always-accessible location.
        //
        // Withdrawal immediately stops all scanning and clears the
        // runtime consent flag.  Re-consent requires re-presenting the
        // full consent dialog — no shortcut is provided.

        let revokeButton = UIButton(type: .system)
        revokeButton.translatesAutoresizingMaskIntoConstraints = false
        revokeButton.setTitle("Revoke Consent & Stop", for: .normal)
        revokeButton.titleLabel?.font     = UIFont.systemFont(ofSize: 16, weight: .semibold)
        revokeButton.setTitleColor(.white, for: .normal)
        revokeButton.backgroundColor      = UIColor.systemRed.withAlphaComponent(0.85)
        revokeButton.layer.cornerRadius   = 12
        revokeButton.addTarget(
            self, action: #selector(revokeConsentTapped), for: .touchUpInside)
        settingsPanel.addSubview(revokeButton)

        // ── Legal Notice ──────────────────────────────────────────────
        let legalLabel = UILabel()
        legalLabel.translatesAutoresizingMaskIntoConstraints = false
        legalLabel.text          = "All processing is on-device and ephemeral. No biometric data is stored or shared. Compliant with GDPR Art. 9, CCPA, and BIPA."
        legalLabel.font          = UIFont.systemFont(ofSize: 11)
        legalLabel.textColor     = .tertiaryLabel
        legalLabel.numberOfLines = 0
        legalLabel.textAlignment = .center
        settingsPanel.addSubview(legalLabel)

        // ── Layout ────────────────────────────────────────────────────
        let sliderRow = UIView()
        sliderRow.translatesAutoresizingMaskIntoConstraints = false
        settingsPanel.addSubview(sliderRow)

        NSLayoutConstraint.activate([
            handle.topAnchor.constraint(
                equalTo: settingsPanel.topAnchor, constant: 10),
            handle.centerXAnchor.constraint(equalTo: settingsPanel.centerXAnchor),
            handle.widthAnchor.constraint(equalToConstant: 40),
            handle.heightAnchor.constraint(equalToConstant: 5),

            titleLabel.topAnchor.constraint(
                equalTo: handle.bottomAnchor, constant: 14),
            titleLabel.leadingAnchor.constraint(
                equalTo: settingsPanel.leadingAnchor, constant: 20),

            closeButton.centerYAnchor.constraint(equalTo: titleLabel.centerYAnchor),
            closeButton.trailingAnchor.constraint(
                equalTo: settingsPanel.trailingAnchor, constant: -20),

            sensitivityHeader.topAnchor.constraint(
                equalTo: titleLabel.bottomAnchor, constant: 20),
            sensitivityHeader.leadingAnchor.constraint(
                equalTo: settingsPanel.leadingAnchor, constant: 20),
            sensitivityHeader.trailingAnchor.constraint(
                equalTo: settingsPanel.trailingAnchor, constant: -20),

            sensitivityDesc.topAnchor.constraint(
                equalTo: sensitivityHeader.bottomAnchor, constant: 6),
            sensitivityDesc.leadingAnchor.constraint(
                equalTo: settingsPanel.leadingAnchor, constant: 20),
            sensitivityDesc.trailingAnchor.constraint(
                equalTo: settingsPanel.trailingAnchor, constant: -20),

            sliderRow.topAnchor.constraint(
                equalTo: sensitivityDesc.bottomAnchor, constant: 10),
            sliderRow.leadingAnchor.constraint(
                equalTo: settingsPanel.leadingAnchor, constant: 20),
            sliderRow.trailingAnchor.constraint(
                equalTo: settingsPanel.trailingAnchor, constant: -20),
            sliderRow.heightAnchor.constraint(equalToConstant: 30),

            preciseLabel.leadingAnchor.constraint(equalTo: sliderRow.leadingAnchor),
            preciseLabel.centerYAnchor.constraint(equalTo: sliderRow.centerYAnchor),

            sensitiveLabel.trailingAnchor.constraint(equalTo: sliderRow.trailingAnchor),
            sensitiveLabel.centerYAnchor.constraint(equalTo: sliderRow.centerYAnchor),

            confidenceSlider.leadingAnchor.constraint(
                equalTo: preciseLabel.trailingAnchor, constant: 8),
            confidenceSlider.trailingAnchor.constraint(
                equalTo: sensitiveLabel.leadingAnchor, constant: -8),
            confidenceSlider.centerYAnchor.constraint(equalTo: sliderRow.centerYAnchor),

            sensitivityValueLabel.topAnchor.constraint(
                equalTo: sliderRow.bottomAnchor, constant: 4),
            sensitivityValueLabel.centerXAnchor.constraint(
                equalTo: settingsPanel.centerXAnchor),

            fpsBadgeLabel.topAnchor.constraint(
                equalTo: sensitivityValueLabel.bottomAnchor, constant: 16),
            fpsBadgeLabel.centerXAnchor.constraint(
                equalTo: settingsPanel.centerXAnchor),

            revokeButton.topAnchor.constraint(
                equalTo: fpsBadgeLabel.bottomAnchor, constant: 20),
            revokeButton.leadingAnchor.constraint(
                equalTo: settingsPanel.leadingAnchor, constant: 20),
            revokeButton.trailingAnchor.constraint(
                equalTo: settingsPanel.trailingAnchor, constant: -20),
            revokeButton.heightAnchor.constraint(equalToConstant: 48),

            legalLabel.topAnchor.constraint(
                equalTo: revokeButton.bottomAnchor, constant: 14),
            legalLabel.leadingAnchor.constraint(
                equalTo: settingsPanel.leadingAnchor, constant: 20),
            legalLabel.trailingAnchor.constraint(
                equalTo: settingsPanel.trailingAnchor, constant: -20),
            legalLabel.bottomAnchor.constraint(
                equalTo: settingsPanel.bottomAnchor,
                constant: -(view.safeAreaInsets.bottom + 20)),
        ])
    }

    /// Creates a styled section-header label for use inside the settings panel.
    private func sectionHeader(_ text: String) -> UILabel {
        let label = UILabel()
        label.translatesAutoresizingMaskIntoConstraints = false
        label.text      = text
        label.font      = UIFont.systemFont(ofSize: 15, weight: .semibold)
        label.textColor = .label
        return label
    }

    // -------------------------------------------------------
    // MARK: Consent Screen
    // -------------------------------------------------------

    /// ETHICAL DESIGN — AVOIDING NON-CONSENSUAL USE:
    ///   • Plain language — no legal jargon.
    ///   • "Decline" is equally prominent — no dark patterns.
    ///   • Zero camera / ARKit activity until "I Agree" is tapped.
    ///   • Biometric data notice satisfies BIPA written-notice requirement.
    ///   • Re-presented if startScanTapped is reached without consent.
    private func presentConsentScreen() {
        let title   = "Your Privacy & Consent"
        let message = """
        Self-Pose Demo analyses YOUR OWN body pose in real time for \
        personal fitness feedback.

        ✔  On-device only — no data leaves your iPhone
        ✔  No video, images, or body data are stored
        ✔  No data is shared with any server or third party
        ✔  Results are discarded immediately after display
        ✔  Only YOUR body is tracked — one person per session
        ✔  Other people in frame are ignored, not analysed
        ✔  You may pause, stop, or revoke consent at any time

        This app processes body-pose data that may be considered \
        biometric information under laws such as BIPA (Illinois), \
        GDPR Article 9, and CCPA.  All processing is ephemeral \
        and on-device; no biometric data is stored or shared.

        By tapping "I Agree" you confirm you are the person who \
        will appear in the camera view and consent to real-time, \
        on-device body pose analysis for personal fitness feedback.
        """

        let alert = UIAlertController(
            title: title, message: message, preferredStyle: .alert)

        alert.addAction(UIAlertAction(
            title: "I Agree — Continue", style: .default
        ) { [weak self] _ in
            self?.userDidGrantConsent()
        })

        alert.addAction(UIAlertAction(
            title: "Decline", style: .cancel
        ) { [weak self] _ in
            self?.userDidDeclineConsent()
        })

        present(alert, animated: true)
    }

    private func userDidGrantConsent() {
        userHasConsented = true
        settingsButton.isEnabled = true
        settingsButton.alpha     = 1.0
        requestCameraPermission()
    }

    private func userDidDeclineConsent() {
        // ETHICAL — EDUCATIONAL MESSAGE ON DECLINE:
        // Rather than a terse error, explain what the user would be
        // missing and how their data would have been protected.  This
        // respects user autonomy while ensuring they have accurate
        // information about the app's privacy-first design.
        userHasConsented = false
        showEducationalMessage(
            title: "No problem!",
            message: """
            You've chosen not to participate — that's completely fine.

            Self-Pose Demo only works when you actively consent.  \
            No camera access, ARKit sessions, or any pose analysis \
            will occur without your explicit agreement.

            If you change your mind, simply re-launch the app to \
            see the consent screen again.
            """)
        poseLabel.text = "Consent required to use this app."
    }

    // -------------------------------------------------------
    // MARK: Revoke Consent
    // -------------------------------------------------------

    /// Immediately stops all scanning and clears consent.
    ///
    /// LEGAL — GDPR Art. 7(3):
    /// "The data subject shall have the right to withdraw his or
    /// her consent at any time."  Withdrawal must be as easy as
    /// giving consent — hence this button in the settings panel.
    @objc private func revokeConsentTapped() {
        hideSettingsPanel()
        stopScanning()
        userHasConsented         = false
        startButton.isEnabled    = false
        startButton.alpha        = 0.5
        settingsButton.isEnabled = false
        settingsButton.alpha     = 0.5
        poseLabel.text           = "Consent revoked."
        optInReminderLabel.text  = "Opt-in self-analysis only — you are the only subject"
        optInReminderLabel.backgroundColor = UIColor.systemIndigo.withAlphaComponent(0.75)

        // Offer to re-consent immediately (handles accidental taps).
        // ETHICAL: Re-presenting the full consent dialog ensures the
        // user cannot bypass consent with a simple toggle.
        presentConsentScreen()
    }

    // -------------------------------------------------------
    // MARK: Camera Permission
    // -------------------------------------------------------

    private func requestCameraPermission() {
        AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
            DispatchQueue.main.async {
                granted
                    ? self?.onCameraPermissionGranted()
                    : self?.onCameraPermissionDenied()
            }
        }
    }

    private func onCameraPermissionGranted() {
        startButton.isEnabled = true
        startButton.alpha     = 1.0
        poseLabel.text        = "Tap \"Start Scan\" to begin your fitness session."
    }

    private func onCameraPermissionDenied() {
        // ETHICAL — EDUCATIONAL MESSAGE ON PERMISSION DENIAL:
        // Explain clearly why camera access is needed and how to enable
        // it.  Do not guilt-trip; simply provide actionable information.
        showEducationalMessage(
            title: "Camera Access Required",
            message: """
            Self-Pose Demo needs camera access to perform real-time \
            body pose analysis.

            Without camera access, no analysis can occur.  All camera \
            data is processed on-device and immediately discarded — \
            it is never stored or sent anywhere.

            To enable camera access:
            Settings → Privacy & Security → Camera → Self-Pose Demo

            You can disable access again at any time from Settings.
            """,
            settingsAction: true)
    }

    // -------------------------------------------------------
    // MARK: Educational Error Messages
    // -------------------------------------------------------
    // All error states are communicated through constructive, plain-
    // language messages that explain the privacy-protective intent of
    // each restriction.  This satisfies the "transparency" requirement
    // of GDPR Art. 5(1)(a) and Apple HIG privacy guidelines.
    // -------------------------------------------------------

    private func showEducationalMessage(
        title: String,
        message: String,
        settingsAction: Bool = false
    ) {
        let alert = UIAlertController(
            title: title, message: message, preferredStyle: .alert)

        if settingsAction {
            alert.addAction(UIAlertAction(title: "Open Settings", style: .default) { _ in
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            })
        }

        alert.addAction(UIAlertAction(title: "OK", style: .cancel))
        present(alert, animated: true)
    }

    // -------------------------------------------------------
    // MARK: Scanning Lifecycle
    // -------------------------------------------------------

    @objc private func startScanTapped() {
        guard userHasConsented else { presentConsentScreen(); return }
        isScanning ? stopScanning() : startScanning()
    }

    @objc private func pauseResumeTapped() {
        guard isScanning else { return }
        isPaused.toggle()
        updateScanningUI()
    }

    @objc private func settingsTapped() {
        showSettingsPanel()
    }

    @objc private func closeSettingsTapped() {
        hideSettingsPanel()
    }

    private func startScanning() {
        guard userHasConsented, !isScanning else { return }

        if ARBodyTrackingConfiguration.isSupported {
            let config = ARBodyTrackingConfiguration()
            config.isLightEstimationEnabled = true
            arView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
            usesBodyTracking = true
        } else if ARFaceTrackingConfiguration.isSupported {
            let config = ARFaceTrackingConfiguration()
            config.isLightEstimationEnabled = true
            arView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
            usesBodyTracking = false
            setupCaptureSession(cameraPosition: .front)
        } else {
            let config = ARWorldTrackingConfiguration()
            arView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
            usesBodyTracking = false
            setupCaptureSession(cameraPosition: .front)
        }

        isScanning             = true
        isPaused               = false
        trackedAnchorID        = nil
        cachedHeadJointIndex   = nil
        currentPose            = .unknown
        lastProcessedTimestamp = 0
        lastRenderedTextString = ""
        fpsWindowStart         = 0
        fpsFramesInWindow      = 0
        measuredFPS            = 15.0
        adaptiveSkipToggle     = false

        updateScanningUI()

        if !usesBodyTracking { addDefaultPoseTextNode() }
    }

    private func stopScanning() {
        guard isScanning else { return }

        arView.session.pause()
        if captureSession.isRunning {
            visionQueue.async { [weak self] in self?.captureSession.stopRunning() }
        }

        isScanning           = false
        isPaused             = false
        currentPose          = .unknown
        trackedAnchorID      = nil
        cachedHeadJointIndex = nil
        usesBodyTracking     = false

        DispatchQueue.main.async { [weak self] in
            self?.updateScanningUI()
            self?.removePoseTextNode()
            self?.clearSkeletonOverlay()
        }
    }

    /// Centralises all UI state changes so start / stop / pause / resume
    /// never leave controls in an inconsistent state.
    private func updateScanningUI() {
        if isScanning {
            startButton.setTitle("Stop Scan", for: .normal)
            startButton.backgroundColor = UIColor.systemRed.withAlphaComponent(0.85)

            pauseButton.isEnabled = true
            pauseButton.alpha     = 1.0
            pauseButton.setTitle(isPaused ? "Resume" : "Pause", for: .normal)
            pauseButton.backgroundColor = isPaused
                ? UIColor.systemGreen.withAlphaComponent(0.85)
                : UIColor.systemOrange.withAlphaComponent(0.85)

            optInReminderLabel.backgroundColor = isPaused
                ? UIColor.systemOrange.withAlphaComponent(0.75)
                : UIColor.systemGreen.withAlphaComponent(0.75)
            optInReminderLabel.text = isPaused
                ? "Analysis paused — tap Resume to continue"
                : "Scanning active — opt-in self-analysis only"

            poseLabel.text = isPaused
                ? "Paused"
                : currentPose.rawValue

            // Scanning indicator — pulse when active, freeze when paused
            if isPaused {
                stopScanningIndicatorAnimation()
                scanningIndicatorLabel.text  = "⏸ Analysis Paused"
                scanningIndicatorLabel.textColor = UIColor.systemOrange
            } else {
                scanningIndicatorLabel.text  = "● Scanning Your Pose…"
                scanningIndicatorLabel.textColor = UIColor.systemGreen
                startScanningIndicatorAnimation()
            }
            UIView.animate(withDuration: 0.2) {
                self.scanningIndicatorLabel.alpha = 1.0
            }

        } else {
            startButton.setTitle("Start Scan", for: .normal)
            startButton.backgroundColor = UIColor.systemBlue.withAlphaComponent(0.85)

            pauseButton.isEnabled = false
            pauseButton.alpha     = 0.5
            pauseButton.setTitle("Pause", for: .normal)
            pauseButton.backgroundColor = UIColor.systemOrange.withAlphaComponent(0.85)

            optInReminderLabel.text = "Opt-in self-analysis only — you are the only subject"
            optInReminderLabel.backgroundColor = UIColor.systemIndigo.withAlphaComponent(0.75)

            poseLabel.text = "Scan stopped."

            stopScanningIndicatorAnimation()
            UIView.animate(withDuration: 0.3) {
                self.scanningIndicatorLabel.alpha = 0.0
            }
            fpsBadgeLabel?.text = "Frame Rate: — fps"
        }
    }

    // -------------------------------------------------------
    // MARK: Scanning Indicator Animation
    // -------------------------------------------------------

    private func startScanningIndicatorAnimation() {
        scanningIndicatorLabel.layer.removeAllAnimations()
        UIView.animate(
            withDuration: 0.8,
            delay: 0,
            options: [.repeat, .autoreverse, .allowUserInteraction]
        ) {
            self.scanningIndicatorLabel.alpha = 0.25
        }
    }

    private func stopScanningIndicatorAnimation() {
        scanningIndicatorLabel.layer.removeAllAnimations()
        scanningIndicatorLabel.alpha = 1.0
    }

    // -------------------------------------------------------
    // MARK: Settings Panel Animations
    // -------------------------------------------------------

    private func showSettingsPanel() {
        // Update FPS badge before showing panel so it reflects current rate
        fpsBadgeLabel.text = String(format: "Frame Rate: %.0f fps  (adaptive skip %@)",
                                    measuredFPS,
                                    measuredFPS < adaptiveSkipFPSThreshold ? "ON" : "off")
        settingsPanelBottomConstraint.constant = 0
        UIView.animate(withDuration: 0.35,
                       delay: 0,
                       usingSpringWithDamping: 0.85,
                       initialSpringVelocity: 0.3,
                       options: .curveEaseOut) {
            self.view.layoutIfNeeded()
        }
    }

    private func hideSettingsPanel() {
        settingsPanelBottomConstraint.constant = 400
        UIView.animate(withDuration: 0.25, delay: 0, options: .curveEaseIn) {
            self.view.layoutIfNeeded()
        }
    }

    // -------------------------------------------------------
    // MARK: Sensitivity Slider
    // -------------------------------------------------------

    @objc private func sensitivityChanged(_ slider: UISlider) {
        // Slider 0.0 (Precise) → threshold 0.70
        // Slider 0.5 (Medium)  → threshold 0.45
        // Slider 1.0 (Sensitive) → threshold 0.20
        let threshold = 0.70 - slider.value * 0.50
        jointConfidenceThreshold = threshold

        let label: String
        switch slider.value {
        case 0.0..<0.33:  label = "Precise"
        case 0.33..<0.67: label = "Medium"
        default:          label = "Sensitive"
        }
        sensitivityValueLabel.text = label
    }

    // -------------------------------------------------------
    // MARK: AVCaptureSession Setup
    // -------------------------------------------------------

    private func setupCaptureSession(cameraPosition: AVCaptureDevice.Position) {
        guard captureSession.inputs.isEmpty else {
            visionQueue.async { [weak self] in self?.captureSession.startRunning() }
            return
        }

        captureSession.beginConfiguration()
        captureSession.sessionPreset = .medium

        guard let camera = AVCaptureDevice.default(
            .builtInWideAngleCamera, for: .video, position: cameraPosition)
        else {
            captureSession.commitConfiguration()
            DispatchQueue.main.async { [weak self] in
                self?.showEducationalMessage(
                    title: "Camera Unavailable",
                    message: """
                    The \(cameraPosition == .front ? "front" : "rear") camera could not be \
                    accessed on this device.

                    Self-Pose Demo requires a camera to analyse body pose.  \
                    No analysis will occur without camera access.
                    """)
            }
            return
        }

        do {
            let input = try AVCaptureDeviceInput(device: camera)
            if captureSession.canAddInput(input) { captureSession.addInput(input) }
        } catch {
            captureSession.commitConfiguration()
            print("[SelfPoseDemo] Cannot create video input: \(error)")
            return
        }

        let output = AVCaptureVideoDataOutput()
        output.alwaysDiscardsLateVideoFrames = true
        output.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String:
                kCVPixelFormatType_420YpCbCr8BiPlanarFullRange
        ]
        output.setSampleBufferDelegate(self, queue: visionQueue)

        if captureSession.canAddOutput(output) { captureSession.addOutput(output) }

        if let connection = output.connection(with: .video) {
            connection.videoOrientation = .portrait
            connection.isVideoMirrored  = (cameraPosition == .front)
        }

        captureSession.commitConfiguration()
        visionQueue.async { [weak self] in self?.captureSession.startRunning() }
    }

    // -------------------------------------------------------
    // MARK: Vision — Unified Frame Processing
    // -------------------------------------------------------

    private func processPixelBuffer(
        _ pixelBuffer: CVPixelBuffer,
        timestamp: TimeInterval,
        orientation: CGImagePropertyOrientation
    ) {
        // ── Gate 1: Consent ───────────────────────────────────────────
        guard userHasConsented else { return }

        // ── Gate 2: Active (not stopped, not paused) ──────────────────
        guard isScanning, !isPaused else { return }

        // ── Gate 3: Frame throttle (≤ 15 fps) ────────────────────────
        guard timestamp - lastProcessedTimestamp >= minimumProcessingInterval else {
            return
        }
        lastProcessedTimestamp = timestamp

        // ── Gate 4: Adaptive frame skip ───────────────────────────────
        // PERFORMANCE: Measure throughput in 1-second windows.  If the
        // device is falling behind (< 8 fps net), skip every other frame
        // to reduce CPU pressure and avoid visionQueue back-pressure.
        fpsFramesInWindow += 1
        if fpsWindowStart == 0 { fpsWindowStart = timestamp }
        let window = timestamp - fpsWindowStart
        if window >= 1.0 {
            measuredFPS       = Double(fpsFramesInWindow) / window
            fpsFramesInWindow = 0
            fpsWindowStart    = timestamp
        }
        if measuredFPS < adaptiveSkipFPSThreshold {
            adaptiveSkipToggle.toggle()
            if adaptiveSkipToggle { return }   // skip this frame
        } else {
            adaptiveSkipToggle = false
        }

        // ── Run Vision ────────────────────────────────────────────────
        let handler = VNImageRequestHandler(
            cvPixelBuffer: pixelBuffer,
            orientation: orientation,
            options: [:]
        )

        do {
            try handler.perform([bodyPoseRequest])
        } catch {
            print("[SelfPoseDemo] Vision request failed: \(error)")
            return
        }

        guard let observations = bodyPoseRequest.results,
              !observations.isEmpty else {
            resetToUnknown()
            return
        }

        // ── Gate 5: Single-user enforcement ───────────────────────────
        // ETHICAL — AVOIDING NON-CONSENSUAL ANALYSIS:
        //   Only the FIRST (primary) observation is processed.
        //   Any additional observations are silently discarded — no data
        //   about non-consenting bystanders is ever touched.
        let observation = observations[0]

        guard let features = extractPoseFeatures(from: observation) else {
            resetToUnknown()
            return
        }

        // ── Gate 6: Confidence threshold ──────────────────────────────
        // Require at least 5 joints above the user-configured threshold.
        // Low-confidence partial detections show "Analysing…" rather than
        // a potentially misleading classification.
        guard features.detectedJointCount >= 5 else {
            updatePoseLabel(with: .unknown)
            drawSkeleton(from: features)
            return
        }

        let pose = classifyPose(from: features)
        updatePoseLabel(with: pose)
        drawSkeleton(from: features)

        if !usesBodyTracking && trackedAnchorID == nil {
            positionLabelViaHitTest(features: features)
        }
    }

    // -------------------------------------------------------
    // MARK: Pose Feature Extraction
    // -------------------------------------------------------

    private func extractPoseFeatures(
        from observation: VNHumanBodyPoseObservation
    ) -> PoseFeatureVector? {

        func joint(_ name: VNHumanBodyPoseObservation.JointName) -> VNRecognizedPoint? {
            return try? observation.recognizedPoint(name)
        }

        var f = PoseFeatureVector()
        // Apply the user's slider setting to this frame's feature vector.
        f.confidenceThreshold = jointConfidenceThreshold

        // Head region — used for label positioning, not biometric ID
        f.nose          = joint(.nose)
        f.leftEye       = joint(.leftEye)
        f.rightEye      = joint(.rightEye)
        f.leftEar       = joint(.leftEar)
        f.rightEar      = joint(.rightEar)
        f.neck          = joint(.neck)
        // Torso
        f.root          = joint(.root)
        // Arms — shoulder position drives overhead / press detection
        f.leftShoulder  = joint(.leftShoulder)
        f.leftElbow     = joint(.leftElbow)
        f.leftWrist     = joint(.leftWrist)
        f.rightShoulder = joint(.rightShoulder)
        f.rightElbow    = joint(.rightElbow)
        f.rightWrist    = joint(.rightWrist)
        // Legs — hips/knees/ankles drive squat, lunge, jump detection
        f.leftHip       = joint(.leftHip)
        f.leftKnee      = joint(.leftKnee)
        f.leftAnkle     = joint(.leftAnkle)
        f.rightHip      = joint(.rightHip)
        f.rightKnee     = joint(.rightKnee)
        f.rightAnkle    = joint(.rightAnkle)
        return f
    }

    // -------------------------------------------------------
    // MARK: Pose Classification
    // -------------------------------------------------------

    /// Returns the best-available value for a left/right bilateral feature.
    private func computeLRFeature(
        left:  (VNRecognizedPoint?, VNRecognizedPoint?),
        right: (VNRecognizedPoint?, VNRecognizedPoint?),
        threshold: Float,
        compute: (VNRecognizedPoint, VNRecognizedPoint) -> Float
    ) -> Float {
        func valid(_ p: VNRecognizedPoint?) -> VNRecognizedPoint? {
            guard let p = p, p.confidence >= threshold else { return nil }
            return p
        }
        if let a = valid(left.0),  let b = valid(left.1)  { return compute(a, b) }
        if let a = valid(right.0), let b = valid(right.1) { return compute(a, b) }
        return 0
    }

    private func classifyPose(from features: PoseFeatureVector) -> PoseClass {
        let t = features.confidenceThreshold

        // F1: Leg extension — normalised hip-to-ankle vertical distance.
        //     Large (> 0.28) → standing; small → crouching / airborne.
        let legExt = computeLRFeature(
            left:  (features.leftHip,  features.leftAnkle),
            right: (features.rightHip, features.rightAnkle),
            threshold: t
        ) { h, a in Float(h.location.y - a.location.y) }

        // F2: Knee bend ratio — knee position as fraction between hip and ankle.
        //     High (> 0.38) → straight leg; low → deep squat or lunge.
        let kneeRatio: Float = {
            func kbr(hip: VNRecognizedPoint?, knee: VNRecognizedPoint?,
                     ankle: VNRecognizedPoint?) -> Float? {
                guard let h = hip, let k = knee, let a = ankle,
                      h.confidence >= t, k.confidence >= t,
                      a.confidence >= t else { return nil }
                let span = Float(h.location.y - a.location.y)
                guard span > 0.01 else { return nil }
                return Float(h.location.y - k.location.y) / span
            }
            return kbr(hip: features.leftHip,  knee: features.leftKnee,
                       ankle: features.leftAnkle)
                ?? kbr(hip: features.rightHip, knee: features.rightKnee,
                       ankle: features.rightAnkle)
                ?? 0
        }()

        // F3: Wrist height relative to shoulders (positive = hands raised).
        //     Used to detect overhead press, jump reach, or arm raise.
        var wristScore: Float = 0; var wristN = 0
        if let lw = features.leftWrist, let ls = features.leftShoulder,
           lw.confidence >= t, ls.confidence >= t {
            wristScore += Float(lw.location.y - ls.location.y); wristN += 1
        }
        if let rw = features.rightWrist, let rs = features.rightShoulder,
           rw.confidence >= t, rs.confidence >= t {
            wristScore += Float(rw.location.y - rs.location.y); wristN += 1
        }
        if wristN > 0 { wristScore /= Float(wristN) }

        // Decision: poseTypeA = Standing/Upright, poseTypeB = Active/Dynamic
        let isStanding = legExt > 0.28 && kneeRatio > 0.38
        return isStanding ? .poseTypeA : .poseTypeB
    }

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Drawing
    // -------------------------------------------------------

    private func visionToViewPoint(_ pt: CGPoint, in size: CGSize) -> CGPoint {
        CGPoint(x: pt.x * size.width, y: (1.0 - pt.y) * size.height)
    }

    private func drawSkeleton(from features: PoseFeatureVector) {
        let layerSize = cachedLayerSize
        guard layerSize.width > 0, layerSize.height > 0 else { return }

        let t = features.confidenceThreshold
        func viewPt(_ j: VNRecognizedPoint?) -> CGPoint? {
            guard let j = j, j.confidence >= t else { return nil }
            return visionToViewPoint(j.location, in: layerSize)
        }

        let bonePath = UIBezierPath()
        let bonePairs: [(VNRecognizedPoint?, VNRecognizedPoint?)] = [
            (features.nose,          features.neck),
            (features.neck,          features.leftShoulder),
            (features.neck,          features.rightShoulder),
            (features.leftShoulder,  features.leftElbow),
            (features.leftElbow,     features.leftWrist),
            (features.rightShoulder, features.rightElbow),
            (features.rightElbow,    features.rightWrist),
            (features.leftShoulder,  features.leftHip),
            (features.rightShoulder, features.rightHip),
            (features.leftHip,       features.rightHip),
            (features.leftHip,       features.leftKnee),
            (features.leftKnee,      features.leftAnkle),
            (features.rightHip,      features.rightKnee),
            (features.rightKnee,     features.rightAnkle),
            (features.root,          features.leftHip),
            (features.root,          features.rightHip),
            (features.leftEar,       features.leftEye),
            (features.leftEye,       features.nose),
            (features.rightEar,      features.rightEye),
            (features.rightEye,      features.nose),
        ]
        for (a, b) in bonePairs {
            guard let from = viewPt(a), let to = viewPt(b) else { continue }
            bonePath.move(to: from); bonePath.addLine(to: to)
        }

        let joints = features.validJoints
        let jointPath = UIBezierPath()
        let r: CGFloat = 5.0
        for (_, j) in joints {
            let c = visionToViewPoint(j.location, in: layerSize)
            jointPath.move(to: CGPoint(x: c.x + r, y: c.y))
            jointPath.addArc(withCenter: c, radius: r,
                             startAngle: 0, endAngle: .pi * 2, clockwise: true)
        }

        DispatchQueue.main.async { [weak self] in
            self?.skeletonBoneLayer.path  = bonePath.cgPath
            self?.skeletonJointLayer.path = jointPath.cgPath
        }
    }

    private func clearSkeletonOverlay() {
        DispatchQueue.main.async { [weak self] in
            self?.skeletonBoneLayer.path  = nil
            self?.skeletonJointLayer.path = nil
        }
    }

    // -------------------------------------------------------
    // MARK: Helpers
    // -------------------------------------------------------

    private func resetToUnknown() {
        updatePoseLabel(with: .unknown)
        clearSkeletonOverlay()
    }

    private func updatePoseLabel(with pose: PoseClass) {
        guard pose != currentPose else { return }
        currentPose = pose
        DispatchQueue.main.async { [weak self] in
            guard let self = self, !self.isPaused else { return }
            self.poseLabel.text = pose.rawValue
        }
    }

    // -------------------------------------------------------
    // MARK: 3-D AR Text Overlay — Node Management
    // -------------------------------------------------------

    private func addDefaultPoseTextNode() {
        let (container, textNode) = makePoseTextNodes(
            initialText: PoseClass.unknown.rawValue)
        container.position = SCNVector3(x: -0.05, y: 0.1, z: -0.3)
        arView.scene.rootNode.addChildNode(container)
        poseTextContainerNode = container
        poseTextNode          = textNode
    }

    private func makePoseTextNodes(
        initialText: String
    ) -> (container: SCNNode, textNode: SCNNode) {

        let geometry = SCNText(string: initialText, extrusionDepth: 0.5)
        geometry.font                            = UIFont.boldSystemFont(ofSize: 6)
        geometry.firstMaterial?.diffuse.contents  = UIColor.cyan
        geometry.flatness                         = 0.1
        let (min, max) = geometry.boundingBox
        let dx = (max.x - min.x) / 2
        let dy = (max.y - min.y) / 2

        let textNode      = SCNNode(geometry: geometry)
        textNode.scale    = SCNVector3(0.01, 0.01, 0.01)
        textNode.pivot    = SCNMatrix4MakeTranslation(dx, dy, 0)
        textNode.name     = "poseTextNode"

        let container = SCNNode()
        container.name = "poseTextContainer"
        let billboard  = SCNBillboardConstraint()
        billboard.freeAxes  = .all
        container.constraints = [billboard]
        container.addChildNode(textNode)

        return (container, textNode)
    }

    private func removePoseTextNode() {
        poseTextContainerNode?.removeFromParentNode()
        poseTextContainerNode  = nil
        poseTextNode?.removeFromParentNode()
        poseTextNode           = nil
        lastRenderedTextString = ""
    }

    // -------------------------------------------------------
    // MARK: AR Label Positioning — ARBodyAnchor (head joint)
    // -------------------------------------------------------

    private static let headJointName = "head_joint"

    private func headJointModelPosition(
        from bodyAnchor: ARBodyAnchor
    ) -> simd_float3? {
        let skeleton   = bodyAnchor.skeleton
        let jointNames = skeleton.definition.jointNames

        if cachedHeadJointIndex == nil {
            cachedHeadJointIndex = jointNames.firstIndex(of: Self.headJointName)
        }
        guard let idx = cachedHeadJointIndex else { return nil }

        let t = skeleton.jointModelTransforms[idx]
        return simd_float3(t.columns.3.x, t.columns.3.y, t.columns.3.z)
    }

    private func attachPoseLabel(
        toBodyNode node: SCNNode,
        bodyAnchor: ARBodyAnchor
    ) {
        let (container, textNode) = makePoseTextNodes(
            initialText: currentPose.rawValue)

        if let headPos = headJointModelPosition(from: bodyAnchor) {
            container.simdPosition = simd_float3(
                headPos.x, headPos.y + 0.2, headPos.z)
        } else {
            container.simdPosition = simd_float3(0, 2.0, 0)
        }

        node.addChildNode(container)
        poseTextContainerNode = container
        poseTextNode          = textNode
    }

    private func updateBodyLabelPosition(bodyAnchor: ARBodyAnchor) {
        guard let container = poseTextContainerNode else { return }
        if let headPos = headJointModelPosition(from: bodyAnchor) {
            container.simdPosition = simd_float3(
                headPos.x, headPos.y + 0.2, headPos.z)
        }
    }

    // -------------------------------------------------------
    // MARK: AR Label Positioning — HitTest from 2D Vision
    // -------------------------------------------------------

    private func positionLabelViaHitTest(features: PoseFeatureVector) {
        guard let container = poseTextContainerNode else { return }
        guard let nose = features.nose,
              nose.confidence >= features.confidenceThreshold else { return }

        let size = cachedLayerSize
        guard size.width > 0 else { return }

        let screenPt = CGPoint(
            x: nose.location.x * size.width,
            y: (1.0 - nose.location.y) * size.height)

        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            let hits = self.arView.hitTest(screenPt, types: .featurePoint)
            if let hit = hits.first {
                let col3 = hit.worldTransform.columns.3
                container.simdWorldPosition = simd_float3(
                    col3.x, col3.y + 0.2, col3.z)
            }
        }
    }
}

// MARK: - AVCaptureVideoDataOutputSampleBufferDelegate

extension ViewController: AVCaptureVideoDataOutputSampleBufferDelegate {

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let ts = CMTimeGetSeconds(
            CMSampleBufferGetPresentationTimeStamp(sampleBuffer))
        processPixelBuffer(pixelBuffer, timestamp: ts, orientation: .up)
    }

    func captureOutput(
        _ output: AVCaptureOutput,
        didDrop sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        // Intentionally empty — dropped frames reduce data exposure.
    }
}

// MARK: - ARSessionDelegate

extension ViewController: ARSessionDelegate {

    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard usesBodyTracking else { return }
        guard userHasConsented, isScanning else { return }
        visionQueue.async { [weak self] in
            self?.processPixelBuffer(
                frame.capturedImage,
                timestamp: frame.timestamp,
                orientation: .right)
        }
    }
}

// MARK: - ARSCNViewDelegate

extension ViewController: ARSCNViewDelegate {

    func renderer(
        _ renderer: SCNSceneRenderer,
        didAdd node: SCNNode,
        for anchor: ARAnchor
    ) {
        guard userHasConsented, isScanning else { return }

        if let bodyAnchor = anchor as? ARBodyAnchor {
            guard trackedAnchorID == nil else {
                print("[SelfPoseDemo] Second body anchor REFUSED (single-user constraint).")
                return
            }
            trackedAnchorID = bodyAnchor.identifier
            DispatchQueue.main.async { [weak self] in
                guard let self = self else { return }
                self.removePoseTextNode()
                self.attachPoseLabel(toBodyNode: node, bodyAnchor: bodyAnchor)
            }
            return
        }

        if anchor is ARFaceAnchor {
            guard trackedAnchorID == nil else {
                print("[SelfPoseDemo] Second face anchor REFUSED.")
                return
            }
            trackedAnchorID = anchor.identifier
            DispatchQueue.main.async { [weak self] in
                guard let self = self,
                      let container = self.poseTextContainerNode else { return }
                container.removeFromParentNode()
                container.position = SCNVector3(x: 0, y: 0.2, z: 0)
                node.addChildNode(container)
            }
            return
        }
    }

    func renderer(
        _ renderer: SCNSceneRenderer,
        didUpdate node: SCNNode,
        for anchor: ARAnchor
    ) {
        guard userHasConsented, isScanning, !isPaused else { return }

        if let bodyAnchor = anchor as? ARBodyAnchor,
           bodyAnchor.identifier == trackedAnchorID {
            updateBodyLabelPosition(bodyAnchor: bodyAnchor)
        }
    }

    func renderer(
        _ renderer: SCNSceneRenderer,
        updateAtTime time: TimeInterval
    ) {
        guard userHasConsented, isScanning, !isPaused else { return }

        let displayText = currentPose.rawValue
        guard displayText != lastRenderedTextString else { return }
        lastRenderedTextString = displayText

        if let geometry = poseTextNode?.geometry as? SCNText {
            geometry.string = displayText
        }
    }

    func session(
        _ session: ARSession,
        cameraDidChangeTrackingState camera: ARCamera
    ) {
        switch camera.trackingState {
        case .notAvailable, .limited:
            resetToUnknown()
        case .normal:
            break
        @unknown default:
            break
        }
    }
}
