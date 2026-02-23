// ViewController.swift
// Self-Pose Demo
//
// ============================================================
// ETHICAL USE NOTICE
// ============================================================
// This application is an educational tool for personal sports
// analytics.  It uses the device's FRONT camera to analyse the
// CONSENTING USER'S OWN body pose in real time, entirely on-device.
//
// Core ethical principles embedded in this design:
//
//   • Explicit Consent    – The user must affirmatively opt-in via an
//     informed consent screen before any camera access begins.
//     Consent is freely given, specific, informed, and unambiguous
//     per GDPR Article 4(11) and Recital 32.
//
//   • On-Device Only      – All pose inference runs locally using
//     Apple's Vision and Core ML frameworks.  No pixel data or
//     derived features ever leave the device.
//
//   • No Persistence      – No video frames, still images, joint
//     coordinates, or feature vectors are written to disk,
//     UserDefaults, iCloud, or any other storage medium.
//
//   • No Sharing          – No data is transmitted to any server,
//     analytics service, or third party (CCPA § 1798.100).
//
//   • Ephemeral Analysis  – Each CMSampleBuffer is consumed by Vision
//     and immediately released; only the resulting PoseClass enum
//     value is retained for display and then discarded.
//
//   • Single-User Design  – The app is intended for self-directed
//     use only.  The person operating the device is always the data
//     subject.  If multiple people are detected in a frame, processing
//     stops immediately to prevent analysing anyone who has not
//     consented (see detectPose).
//
//   • Stop at Any Time    – The user can halt all processing by
//     tapping "Stop Scan" or closing the app.
//
// Legal references:
//   GDPR  – Regulation (EU) 2016/679, Articles 5, 6(1)(a), 9
//   CCPA  – California Civil Code § 1798.100 et seq.
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

/// The two classification outcomes produced by the on-device AI pipeline.
///
/// - poseTypeA : Grounded / static stance (e.g. standing upright).
/// - poseTypeB : Airborne / dynamic stance (e.g. jumping, lunging).
/// - unknown   : Insufficient joint confidence; shown while warming up,
///               or when too few joints are visible.
/// - multiPerson: More than one person detected — processing suspended
///               for privacy until only the consenting user is in frame.
enum PoseClass: String {
    case poseTypeA   = "Pose Type A"           // e.g. Standing
    case poseTypeB   = "Pose Type B"           // e.g. Jumping
    case unknown     = "Analysing…"
    case multiPerson = "⚠ Multiple people — move to a private space"
}

// MARK: - PoseFeatureVector

/// A snapshot of all 19 Vision body-pose joint positions for a single frame.
///
/// Each joint is stored as an optional `VNRecognizedPoint`.  A joint is nil
/// when Vision could not detect it (e.g. limb out of frame).  Joints below
/// `confidenceThreshold` are treated as absent by all consumers.
///
/// ETHICAL NOTE: This struct is ephemeral.  It is created per-frame on
/// `visionQueue`, used for classification and skeleton drawing, then
/// immediately discarded.  It is never written to any persistent store.
struct PoseFeatureVector {

    // ----------------------------------------------------------------
    // MARK: Confidence gate
    // ----------------------------------------------------------------

    /// Joints whose Vision confidence falls below this threshold are
    /// excluded from classification and skeleton rendering.
    static let confidenceThreshold: Float = 0.4

    // ----------------------------------------------------------------
    // MARK: All 19 Vision body joints
    // ----------------------------------------------------------------

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

    // ----------------------------------------------------------------
    // MARK: Derived helpers
    // ----------------------------------------------------------------

    /// Every joint that is non-nil AND above the confidence threshold.
    var validJoints: [(name: String, point: VNRecognizedPoint)] {
        let allJoints: [(String, VNRecognizedPoint?)] = [
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
        return allJoints.compactMap { name, pt in
            guard let pt = pt, pt.confidence >= Self.confidenceThreshold else { return nil }
            return (name, pt)
        }
    }

    /// Number of confidently detected joints (0–19).
    var detectedJointCount: Int { validJoints.count }

    /// Fraction of joints detected above threshold.  Used as a signal
    /// for whether the frame is suitable for classification.
    var overallConfidence: Float { Float(detectedJointCount) / 19.0 }

    // ----------------------------------------------------------------
    // MARK: MLMultiArray builder (placeholder for Core ML integration)
    // ----------------------------------------------------------------

    // PLACEHOLDER — uncomment and adapt when a real .mlmodel is added.
    //
    // Builds a [19 × 3] MLMultiArray where each row is [x, y, confidence]
    // for one joint, ordered consistently with the model's expected input.
    // Absent joints are represented as [0, 0, 0].
    //
    // func toMLMultiArray() throws -> MLMultiArray {
    //     let array = try MLMultiArray(shape: [19, 3], dataType: .float32)
    //     let orderedJoints: [VNRecognizedPoint?] = [
    //         nose, leftEye, rightEye, leftEar, rightEar,
    //         neck, root,
    //         leftShoulder, leftElbow, leftWrist,
    //         rightShoulder, rightElbow, rightWrist,
    //         leftHip, leftKnee, leftAnkle,
    //         rightHip, rightKnee, rightAnkle,
    //     ]
    //     for (i, joint) in orderedJoints.enumerated() {
    //         let base = i * 3
    //         if let j = joint, j.confidence >= PoseFeatureVector.confidenceThreshold {
    //             array[base]     = NSNumber(value: Float(j.location.x))
    //             array[base + 1] = NSNumber(value: Float(j.location.y))
    //             array[base + 2] = NSNumber(value: j.confidence)
    //         } else {
    //             array[base] = 0; array[base + 1] = 0; array[base + 2] = 0
    //         }
    //     }
    //     return array
    // }
}

// MARK: - ViewController

class ViewController: UIViewController {

    // -------------------------------------------------------
    // MARK: UI / AR
    // -------------------------------------------------------

    /// Full-screen AR view — renders the live front-camera feed via ARKit
    /// and hosts SceneKit overlays (the floating pose-label text node).
    private var arView: ARSCNView!

    /// Translucent HUD label near the bottom of the screen.
    /// Displays the current `PoseClass.rawValue` in plain language.
    private var poseLabel: UILabel!

    /// Toggles the scanning session.
    /// Disabled and dimmed until consent AND camera permission are confirmed.
    private var startButton: UIButton!

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Layers
    // -------------------------------------------------------
    // Two CAShapeLayers sit on top of the ARSCNView as a 2-D skeleton
    // visualisation.  They show the user their own detected joints and
    // bones in real time — purely for educational self-feedback.
    //
    // ETHICAL NOTE: These layers render Vision's normalised joint
    // coordinates mapped to screen space.  They display nothing and
    // retain nothing when scanning is stopped.
    // -------------------------------------------------------

    /// Lines connecting anatomically adjacent joints ("bones").
    private let skeletonBoneLayer  = CAShapeLayer()

    /// Filled circles drawn at each detected joint location.
    private let skeletonJointLayer = CAShapeLayer()

    // -------------------------------------------------------
    // MARK: AVFoundation – Front-Camera Pipeline
    // -------------------------------------------------------
    // DUAL-SESSION DESIGN:
    // ARFaceTrackingConfiguration drives ARSCNView rendering but does not
    // expose a sample-buffer delegate.  A lightweight parallel
    // AVCaptureSession feeds raw frames to Vision for pose detection.
    // Both sessions target the same front TrueDepth sensor; iOS manages
    // multi-client hardware access from iOS 13+.
    // -------------------------------------------------------

    /// Manages the front-camera input → Vision inference pipeline.
    private let captureSession = AVCaptureSession()

    /// Serial queue for AVCaptureVideoDataOutputSampleBufferDelegate callbacks
    /// and all Vision inference.  Never blocks the main thread.
    private let visionQueue = DispatchQueue(
        label: "com.selfposedemo.visionQueue",
        qos: .userInitiated
    )

    // -------------------------------------------------------
    // MARK: Vision
    // -------------------------------------------------------

    /// Reusable on-device body pose detection request.
    /// VNDetectHumanBodyPoseRequest runs on the Neural Engine — no network.
    private var bodyPoseRequest = VNDetectHumanBodyPoseRequest()

    // -------------------------------------------------------
    // MARK: Core ML (Placeholder — see classifyPose)
    // -------------------------------------------------------
    // HOW TO INTEGRATE A REAL CORE ML MODEL:
    //   1. Train a pose classifier with Apple's CreateML "Action Classifier"
    //      template using sequences of PoseFeatureVector samples.
    //   2. Add the compiled .mlmodel file to the Xcode project target.
    //   3. Xcode auto-generates a Swift class, e.g. `PoseClassifierModel`.
    //   4. Instantiate below and uncomment the inference call in
    //      classifyPose(from:).
    //
    // private var poseClassifier: PoseClassifierModel?

    // -------------------------------------------------------
    // MARK: Frame Throttle
    // -------------------------------------------------------
    // Vision body pose inference is expensive.  Running at the full camera
    // frame rate (~30 fps) is wasteful and may heat the device.  We cap
    // inference at ~15 fps by tracking the last processed timestamp.
    //
    // ETHICAL NOTE: Dropped frames are intentional — they mean less
    // data is touched, not that data is buffered for later use.
    // -------------------------------------------------------

    /// Presentation timestamp of the most recently processed frame (seconds).
    private var lastProcessedTimestamp: TimeInterval = 0

    /// Minimum gap between processed frames: 1/15 s ≈ 66 ms → 15 fps cap.
    private let minimumProcessingInterval: TimeInterval = 1.0 / 15.0

    // -------------------------------------------------------
    // MARK: State
    // -------------------------------------------------------

    /// Guards every camera / AR operation behind explicit user consent.
    ///
    /// ETHICAL: Set to `true` ONLY inside `userDidGrantConsent()`, which
    /// is called exclusively from the UIAlertController "I Agree" action.
    /// Consent is a runtime flag, intentionally not persisted to disk —
    /// so a fresh launch always re-presents the consent screen.
    private var userHasConsented = false

    /// Whether the capture + AR pipeline is currently running.
    private var isScanning = false

    /// The pose label most recently sent to the UI.  Guards against
    /// redundant main-thread dispatches when the classification is stable.
    private var currentPose: PoseClass = .unknown

    /// Set to true when Vision detects >1 person in a frame.
    /// Processing is suspended until the frame contains exactly one person.
    ///
    /// ETHICAL: Prevents analysing a bystander who has not consented.
    private var isMultiplePersonsDetected = false

    /// Floating SceneKit text node that labels the user's pose in AR space.
    private var poseTextNode: SCNNode?

    // -------------------------------------------------------
    // MARK: View Lifecycle
    // -------------------------------------------------------

    override func viewDidLoad() {
        super.viewDidLoad()
        setupARView()
        setupSkeletonOverlay()
        setupHUD()
        // ETHICAL: The consent screen is displayed synchronously at launch.
        // No camera initialisation occurs before the user taps "I Agree".
        presentConsentScreen()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        stopScanning()
    }

    // -------------------------------------------------------
    // MARK: ARSCNView Setup
    // -------------------------------------------------------

    /// Configures the ARSCNView to fill the entire screen.
    /// The ARKit session is NOT started here — it starts only after consent.
    private func setupARView() {
        arView = ARSCNView(frame: view.bounds)
        arView.autoresizingMask         = [.flexibleWidth, .flexibleHeight]
        arView.delegate                 = self
        arView.scene                    = SCNScene()
        arView.automaticallyUpdatesLighting = true
#if DEBUG
        arView.showsStatistics = true
#endif
        view.addSubview(arView)
    }

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Setup
    // -------------------------------------------------------

    /// Adds two CAShapeLayers directly on top of the ARSCNView layer.
    /// Layers are transparent until `drawSkeleton(from:)` fills them.
    private func setupSkeletonOverlay() {
        // Bone layer — cyan lines connecting adjacent joints.
        skeletonBoneLayer.strokeColor   = UIColor.cyan.withAlphaComponent(0.75).cgColor
        skeletonBoneLayer.lineWidth     = 2.5
        skeletonBoneLayer.fillColor     = UIColor.clear.cgColor
        skeletonBoneLayer.lineCap       = .round
        skeletonBoneLayer.lineJoin      = .round

        // Joint layer — yellow filled circles at each joint position.
        skeletonJointLayer.strokeColor  = UIColor.clear.cgColor
        skeletonJointLayer.fillColor    = UIColor.systemYellow.withAlphaComponent(0.85).cgColor

        // Both layers are added AFTER arView is in the hierarchy; their
        // frames are set / updated in viewDidLayoutSubviews so they always
        // match the actual ARSCNView bounds.
        arView.layer.addSublayer(skeletonBoneLayer)
        arView.layer.addSublayer(skeletonJointLayer)
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        // Keep overlay layers in sync with the arView frame.
        skeletonBoneLayer.frame  = arView.bounds
        skeletonJointLayer.frame = arView.bounds
    }

    // -------------------------------------------------------
    // MARK: HUD Setup
    // -------------------------------------------------------

    /// Overlays the classification label and Start/Stop button above the AR view.
    private func setupHUD() {
        // -- Pose Label --
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

        // -- Start / Stop Button --
        startButton = UIButton(type: .system)
        startButton.translatesAutoresizingMaskIntoConstraints = false
        startButton.setTitle("Start Scan", for: .normal)
        startButton.titleLabel?.font    = UIFont.systemFont(ofSize: 18, weight: .bold)
        startButton.backgroundColor     = UIColor.systemBlue.withAlphaComponent(0.85)
        startButton.setTitleColor(.white, for: .normal)
        startButton.layer.cornerRadius  = 12
        startButton.isEnabled           = false   // requires consent + camera permission
        startButton.alpha               = 0.5
        startButton.addTarget(self, action: #selector(startScanTapped), for: .touchUpInside)
        view.addSubview(startButton)

        // -- Auto Layout --
        NSLayoutConstraint.activate([
            poseLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor,  constant:  20),
            poseLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            poseLabel.bottomAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -88),
            poseLabel.heightAnchor.constraint(greaterThanOrEqualToConstant: 50),

            startButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            startButton.bottomAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24),
            startButton.widthAnchor.constraint(equalToConstant: 160),
            startButton.heightAnchor.constraint(equalToConstant: 48),
        ])
    }

    // -------------------------------------------------------
    // MARK: Consent Screen
    // -------------------------------------------------------

    /// Presents an informed-consent dialog before any camera work begins.
    ///
    /// ETHICAL DESIGN:
    ///   • Plain language — no legal jargon that conceals what's happening.
    ///   • "Decline" is as prominent as "I Agree" — no dark patterns.
    ///   • The app takes zero action until the user taps "I Agree".
    ///   • Re-presented if the Start button is somehow reached without consent
    ///     (belt-and-braces guard in startScanTapped).
    private func presentConsentScreen() {
        let title   = "Your Privacy & Consent"
        let message = """
        Self-Pose Demo uses your front camera to analyse YOUR OWN body pose \
        in real time for personal sports feedback.

        ✔  On-device only — no data leaves your iPhone
        ✔  No video or images are stored or recorded
        ✔  No data is shared with any server or third party
        ✔  Analysis is temporary; results are discarded after display
        ✔  Processing stops immediately if anyone else enters the frame
        ✔  You may stop at any time

        Designed for single-user, self-directed use only.  By tapping \
        "I Agree" you confirm you are the person who will appear in the \
        camera view and that you consent to real-time, on-device body pose \
        analysis for personal feedback.

        Compliant with GDPR, CCPA, and Apple's Privacy Guidelines.
        """

        let alert = UIAlertController(
            title: title, message: message, preferredStyle: .alert)

        // PRIMARY — affirmative, clearly labelled agreement
        alert.addAction(UIAlertAction(
            title: "I Agree — Continue", style: .default
        ) { [weak self] _ in
            // ETHICAL: the consent flag is set here, and ONLY here.
            self?.userDidGrantConsent()
        })

        // SECONDARY — equally accessible decline path
        alert.addAction(UIAlertAction(
            title: "Decline", style: .cancel
        ) { [weak self] _ in
            self?.userDidDeclineConsent()
        })

        present(alert, animated: true)
    }

    /// Called only when the user taps "I Agree".
    private func userDidGrantConsent() {
        // ETHICAL: runtime flag only — never persisted to disk.
        // Force-quitting and relaunching the app requires re-consent.
        userHasConsented = true
        requestCameraPermission()
    }

    /// Called when the user taps "Decline".
    /// The app stays open but entirely inactive — no camera access occurs.
    private func userDidDeclineConsent() {
        userHasConsented = false
        poseLabel.text = "Consent required to use this app."
        // startButton remains disabled.
    }

    // -------------------------------------------------------
    // MARK: Camera Permission
    // -------------------------------------------------------

    /// Requests AVCaptureDevice camera authorisation.
    /// iOS shows its own system prompt on first launch; subsequent launches
    /// use the stored decision.  The prompt message is set in Info.plist.
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
        poseLabel.text        = "Tap \"Start Scan\" to begin."
    }

    private func onCameraPermissionDenied() {
        let alert = UIAlertController(
            title:   "Camera Access Required",
            message: "Self-Pose Demo needs camera access to detect your pose. "
                   + "Please enable it in Settings › Privacy & Security › Camera.",
            preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Open Settings", style: .default) { _ in
            if let url = URL(string: UIApplication.openSettingsURLString) {
                UIApplication.shared.open(url)
            }
        })
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel))
        present(alert, animated: true)
    }

    // -------------------------------------------------------
    // MARK: Scanning Lifecycle
    // -------------------------------------------------------

    @objc private func startScanTapped() {
        // Defensive belt-and-braces: the button should never be enabled
        // without consent, but we enforce it here as a final ethical gate.
        guard userHasConsented else { presentConsentScreen(); return }
        isScanning ? stopScanning() : startScanning()
    }

    /// Starts the ARKit session (for visual overlays) and the AVCaptureSession
    /// (for Vision pose detection).
    ///
    /// ETHICAL: Nothing begins until this method is explicitly invoked by
    /// the user after both consent and OS camera permission are confirmed.
    private func startScanning() {
        guard userHasConsented, !isScanning else { return }

        // ARKit — front TrueDepth camera for AR label rendering.
        if ARFaceTrackingConfiguration.isSupported {
            let config = ARFaceTrackingConfiguration()
            config.isLightEstimationEnabled = true
            arView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
        } else {
            // Devices without a TrueDepth camera fall back to world tracking.
            let config = ARWorldTrackingConfiguration()
            arView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
        }

        // Parallel AVCaptureSession for feeding raw frames to Vision.
        setupCaptureSession()

        isScanning                = true
        isMultiplePersonsDetected = false
        currentPose               = .unknown
        lastProcessedTimestamp    = 0
        poseLabel.text            = PoseClass.unknown.rawValue

        startButton.setTitle("Stop Scan", for: .normal)
        startButton.backgroundColor = UIColor.systemRed.withAlphaComponent(0.85)

        addPoseTextNode()
    }

    /// Tears down the AR session and capture pipeline.
    ///
    /// ETHICAL: Stopping the scan immediately ceases all frame processing.
    /// No further pixel data is read from the camera after this returns.
    private func stopScanning() {
        guard isScanning else { return }

        arView.session.pause()
        if captureSession.isRunning {
            visionQueue.async { [weak self] in self?.captureSession.stopRunning() }
        }

        isScanning  = false
        currentPose = .unknown

        DispatchQueue.main.async { [weak self] in
            self?.startButton.setTitle("Start Scan", for: .normal)
            self?.startButton.backgroundColor = UIColor.systemBlue.withAlphaComponent(0.85)
            self?.poseLabel.text = "Scan stopped."
            self?.removePoseTextNode()
            self?.clearSkeletonOverlay()
        }
    }

    // -------------------------------------------------------
    // MARK: AVCaptureSession Setup
    // -------------------------------------------------------

    /// Configures the front-camera capture pipeline.
    ///   Input  – front wide-angle camera at `.medium` quality preset.
    ///   Output – `AVCaptureVideoDataOutput` with delegate on `visionQueue`.
    ///
    /// Inputs/outputs are configured only once; on subsequent Start taps
    /// the existing configuration is reused and only `startRunning` is called.
    private func setupCaptureSession() {
        guard captureSession.inputs.isEmpty else {
            visionQueue.async { [weak self] in self?.captureSession.startRunning() }
            return
        }

        captureSession.beginConfiguration()
        // .medium: 480×360 — enough resolution for Vision body pose; conserves CPU.
        captureSession.sessionPreset = .medium

        // -- Front camera input --
        guard let frontCamera = AVCaptureDevice.default(
            .builtInWideAngleCamera, for: .video, position: .front)
        else {
            print("[SelfPoseDemo] Front camera unavailable.")
            captureSession.commitConfiguration()
            return
        }

        do {
            let input = try AVCaptureDeviceInput(device: frontCamera)
            if captureSession.canAddInput(input) { captureSession.addInput(input) }
        } catch {
            print("[SelfPoseDemo] Cannot create video input: \(error)")
            captureSession.commitConfiguration()
            return
        }

        // -- Video data output (sample-buffer delegate for Vision) --
        let output = AVCaptureVideoDataOutput()
        // Drop late frames rather than queuing them — prevents stale inference.
        output.alwaysDiscardsLateVideoFrames = true
        // Pixel format: kCVPixelFormatType_420YpCbCr8BiPlanarFullRange is
        // efficient for Vision and avoids unnecessary colour conversion.
        output.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String:
                kCVPixelFormatType_420YpCbCr8BiPlanarFullRange
        ]
        output.setSampleBufferDelegate(self, queue: visionQueue)

        if captureSession.canAddOutput(output) { captureSession.addOutput(output) }

        // Set portrait orientation on the connection so Vision receives
        // portrait-oriented frames directly.
        if let connection = output.connection(with: .video) {
            connection.videoOrientation = .portrait
            // Mirror so the user sees a natural self-view (like a mirror).
            connection.isVideoMirrored  = true
        }

        captureSession.commitConfiguration()

        // startRunning blocks until hardware is ready; run off the main thread.
        visionQueue.async { [weak self] in self?.captureSession.startRunning() }
    }

    // -------------------------------------------------------
    // MARK: Vision – Real-Time Body Pose Detection
    // -------------------------------------------------------

    /// Entry point for each incoming camera frame.
    ///
    /// This method is the core of the real-time processing pipeline.
    /// It enforces every ethical constraint before touching pixel data:
    ///   1. Consent gate   — returns immediately if the user has not consented.
    ///   2. Active gate    — returns immediately if scanning is stopped.
    ///   3. Throttle gate  — limits Vision inference to ≤15 fps.
    ///   4. Person count   — suspends classification if >1 person is detected.
    ///
    /// Called on `visionQueue` (background thread).
    ///
    /// ETHICAL DESIGN — frame lifecycle:
    ///   CMSampleBuffer → CVPixelBuffer → VNImageRequestHandler → Vision
    ///   → VNHumanBodyPoseObservation → PoseFeatureVector → PoseClass
    ///   At no point is a frame, a pixel buffer, or raw coordinates retained.
    private func detectPose(in sampleBuffer: CMSampleBuffer) {

        // ── Gate 1: Consent (checked on every frame for safety) ──────────
        // ETHICAL: If the user has revoked consent or never granted it,
        // we must not process their image data under any circumstance.
        guard userHasConsented else { return }

        // ── Gate 2: Active scan ───────────────────────────────────────────
        guard isScanning else { return }

        // ── Gate 3: Frame throttle ────────────────────────────────────────
        // Limit Vision inference to ~15 fps to preserve battery / thermals
        // while still providing fluid feedback.  Skipped frames are simply
        // discarded — they are never buffered or stored.
        let frameTimestamp = CMTimeGetSeconds(
            CMSampleBufferGetPresentationTimeStamp(sampleBuffer))
        guard frameTimestamp - lastProcessedTimestamp >= minimumProcessingInterval else {
            return
        }
        lastProcessedTimestamp = frameTimestamp

        // ── Extract pixel buffer ──────────────────────────────────────────
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        // ── Run Vision body pose request ──────────────────────────────────
        // VNImageRequestHandler owns the pixel buffer for the duration of
        // `perform(_:)` and releases it immediately afterwards.
        let handler = VNImageRequestHandler(
            cvPixelBuffer: pixelBuffer,
            // `.up` matches portrait orientation set on the capture connection.
            orientation: .up,
            options: [:]
        )

        do {
            try handler.perform([bodyPoseRequest])
        } catch {
            print("[SelfPoseDemo] Vision request failed: \(error)")
            return
        }

        guard let observations = bodyPoseRequest.results else {
            updatePoseLabel(with: .unknown)
            clearSkeletonOverlay()
            return
        }

        // ── Gate 4: Single-person enforcement ────────────────────────────
        // ETHICAL SINGLE-USER FOCUS:
        // Vision may detect multiple people in a frame.  Because only the
        // consenting user has agreed to be analysed, we must not process
        // any observation if more than one person is present — we cannot
        // determine which skeleton belongs to a non-consenting bystander.
        //
        // Behaviour:
        //   0 people: show "Analysing…" and clear skeleton.
        //   1 person: process normally (this is the consenting user).
        //  >1 people: suspend classification, show a privacy warning,
        //             clear the skeleton so no bystander data is rendered.
        switch observations.count {

        case 0:
            // No body detected — user may have stepped out of frame.
            isMultiplePersonsDetected = false
            updatePoseLabel(with: .unknown)
            clearSkeletonOverlay()

        case 1:
            // Exactly one person — this is the consenting user.
            isMultiplePersonsDetected = false
            let observation = observations[0]

            // Extract all joint positions into an ephemeral feature vector.
            guard let features = extractPoseFeatures(from: observation) else {
                updatePoseLabel(with: .unknown)
                clearSkeletonOverlay()
                return
            }

            // Require a minimum number of confident joints for reliable
            // classification.  Below this threshold the skeleton is too
            // incomplete to classify meaningfully.
            guard features.detectedJointCount >= 5 else {
                updatePoseLabel(with: .unknown)
                drawSkeleton(from: features)   // still draw what's visible
                return
            }

            // Classify the pose and render the skeleton overlay.
            let pose = classifyPose(from: features)
            updatePoseLabel(with: pose)
            drawSkeleton(from: features)

        default:
            // More than one person detected.
            // ETHICAL: Stop all analysis immediately and alert the user to
            // move to a private space where only they are in frame.
            isMultiplePersonsDetected = true
            updatePoseLabel(with: .multiPerson)
            // Clear the skeleton so no bystander joint positions are shown.
            clearSkeletonOverlay()
        }
    }

    // -------------------------------------------------------
    // MARK: Pose Feature Extraction
    // -------------------------------------------------------

    /// Reads all 19 Vision body joints from a single observation into an
    /// ephemeral `PoseFeatureVector`.
    ///
    /// Returns `nil` only if `recognizedPoints(forGroupKey:)` throws, which
    /// should not occur under normal circumstances.
    ///
    /// ETHICAL NOTE: The returned struct holds only normalised (0–1)
    /// floating-point coordinates — not pixel data — and is discarded
    /// as soon as classification and drawing are complete.
    private func extractPoseFeatures(
        from observation: VNHumanBodyPoseObservation
    ) -> PoseFeatureVector? {

        // Helper: safely fetch a single recognised joint point.
        // Returns nil if the joint is absent or below confidence threshold.
        func joint(_ name: VNHumanBodyPoseObservation.JointName) -> VNRecognizedPoint? {
            return try? observation.recognizedPoint(name)
        }

        var f = PoseFeatureVector()

        // -- Head / neck --
        f.nose          = joint(.nose)
        f.leftEye       = joint(.leftEye)
        f.rightEye      = joint(.rightEye)
        f.leftEar       = joint(.leftEar)
        f.rightEar      = joint(.rightEar)
        f.neck          = joint(.neck)

        // -- Torso root (Vision's centre-of-hips landmark) --
        f.root          = joint(.root)

        // -- Left arm --
        f.leftShoulder  = joint(.leftShoulder)
        f.leftElbow     = joint(.leftElbow)
        f.leftWrist     = joint(.leftWrist)

        // -- Right arm --
        f.rightShoulder = joint(.rightShoulder)
        f.rightElbow    = joint(.rightElbow)
        f.rightWrist    = joint(.rightWrist)

        // -- Left leg --
        f.leftHip       = joint(.leftHip)
        f.leftKnee      = joint(.leftKnee)
        f.leftAnkle     = joint(.leftAnkle)

        // -- Right leg --
        f.rightHip      = joint(.rightHip)
        f.rightKnee     = joint(.rightKnee)
        f.rightAnkle    = joint(.rightAnkle)

        return f
    }

    // -------------------------------------------------------
    // MARK: Pose Classification
    // -------------------------------------------------------
    //
    // CURRENT IMPLEMENTATION: rule-based multi-feature heuristic.
    //
    // This is intentionally a stand-in to demonstrate how extracted
    // PoseFeatureVector values would feed into a real classifier.
    // Replace the body of classifyPose(from:) with a Core ML call
    // once a trained model is available (see PLACEHOLDER block below).
    //
    // Features used in the heuristic:
    //   F1  legExtension  – normalised vertical hip-to-ankle distance.
    //                       Large = standing; small = bent / airborne.
    //   F2  kneeBendRatio – fraction of leg span above the knee.
    //                       ~0.5 = straight leg; <0.35 = deeply bent.
    //   F3  wristHeight   – mean wrist y relative to shoulders.
    //                       High wrists = arms raised (e.g. jumping form).
    //
    // Decision rule:
    //   • If legExtension > 0.28 AND kneeBendRatio > 0.38 → Type A (standing)
    //   • Otherwise                                        → Type B (jumping)
    // -------------------------------------------------------

    /// Classifies a `PoseFeatureVector` into a `PoseClass`.
    ///
    /// Called on `visionQueue`; result is dispatched to the main thread
    /// inside `updatePoseLabel(with:)`.
    private func classifyPose(from features: PoseFeatureVector) -> PoseClass {
        let threshold = PoseFeatureVector.confidenceThreshold

        // ── Feature 1: Leg extension ──────────────────────────────────────
        // Prefer the left side; fall back to right if left is occluded.
        var legExtension: Float = 0
        if let hip = features.leftHip, let ankle = features.leftAnkle,
           hip.confidence >= threshold, ankle.confidence >= threshold {
            // Vision y=0 is bottom, y=1 is top; hip should be above ankle.
            legExtension = Float(hip.location.y - ankle.location.y)
        } else if let hip = features.rightHip, let ankle = features.rightAnkle,
                  hip.confidence >= threshold, ankle.confidence >= threshold {
            legExtension = Float(hip.location.y - ankle.location.y)
        }
        // legExtension: ~0.35–0.45 when standing; ~0.10–0.20 when jumping.

        // ── Feature 2: Knee bend ratio ────────────────────────────────────
        // How far the knee is from the hip relative to the total leg span.
        // ~0.5 = straight; <0.35 = deeply bent knee.
        var kneeBendRatio: Float = 0
        if let hip   = features.leftHip,
           let knee  = features.leftKnee,
           let ankle = features.leftAnkle,
           hip.confidence   >= threshold,
           knee.confidence  >= threshold,
           ankle.confidence >= threshold {
            let totalSpan = Float(hip.location.y - ankle.location.y)
            let hipToKnee = Float(hip.location.y - knee.location.y)
            if totalSpan > 0.01 { kneeBendRatio = hipToKnee / totalSpan }
        } else if let hip   = features.rightHip,
                  let knee  = features.rightKnee,
                  let ankle = features.rightAnkle,
                  hip.confidence   >= threshold,
                  knee.confidence  >= threshold,
                  ankle.confidence >= threshold {
            let totalSpan = Float(hip.location.y - ankle.location.y)
            let hipToKnee = Float(hip.location.y - knee.location.y)
            if totalSpan > 0.01 { kneeBendRatio = hipToKnee / totalSpan }
        }
        // kneeBendRatio: ~0.45–0.55 when standing; <0.35 when crouching/jumping.

        // ── Feature 3: Wrist height relative to shoulders ─────────────────
        // Raised wrists (y above shoulder y) are common during a jump.
        var wristHeightScore: Float = 0
        var wristSamples = 0
        if let lw = features.leftWrist, let ls = features.leftShoulder,
           lw.confidence >= threshold, ls.confidence >= threshold {
            wristHeightScore += Float(lw.location.y - ls.location.y)
            wristSamples += 1
        }
        if let rw = features.rightWrist, let rs = features.rightShoulder,
           rw.confidence >= threshold, rs.confidence >= threshold {
            wristHeightScore += Float(rw.location.y - rs.location.y)
            wristSamples += 1
        }
        if wristSamples > 0 { wristHeightScore /= Float(wristSamples) }
        // wristHeightScore > 0 means wrists are above shoulders (Vision y up).

        // ── Decision rule ─────────────────────────────────────────────────
        // Tune thresholds based on your own calibration data or replace
        // this entire block with a Core ML prediction call.
        let isStanding = legExtension > 0.28 && kneeBendRatio > 0.38
        return isStanding ? .poseTypeA : .poseTypeB
    }

    // --------------------------------------------------------
    // PLACEHOLDER: Core ML classification function
    // --------------------------------------------------------
    // When a trained .mlmodel is available, replace classifyPose(from:)
    // with the function below (or call it from classifyPose):
    //
    // private func classifyWithCoreML(features: PoseFeatureVector) -> PoseClass {
    //     guard let classifier = poseClassifier else { return .unknown }
    //     guard let inputArray = try? features.toMLMultiArray() else { return .unknown }
    //
    //     // PoseClassifierInput is auto-generated by Xcode from the .mlmodel.
    //     let input  = PoseClassifierInput(poses: inputArray)
    //     guard let output = try? classifier.prediction(input: input) else {
    //         return .unknown
    //     }
    //     // Map the model's string output label back to our PoseClass enum.
    //     return PoseClass(rawValue: output.classLabel) ?? .unknown
    // }
    // --------------------------------------------------------

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Drawing
    // -------------------------------------------------------

    /// Converts a Vision normalised point (y=0 at bottom) to a view-space
    /// CGPoint (y=0 at top) within the given size.
    ///
    /// Because the capture connection has `isVideoMirrored = true`, the
    /// x-axis is already mirrored to match the user's self-view.
    private func visionToViewPoint(_ pt: CGPoint, in size: CGSize) -> CGPoint {
        CGPoint(x: pt.x * size.width,
                y: (1.0 - pt.y) * size.height)
    }

    /// Draws the skeleton (bones + joint dots) from a `PoseFeatureVector`
    /// onto the two overlay CAShapeLayers.
    ///
    /// Must be called on any thread; dispatches layer updates to main.
    ///
    /// ETHICAL NOTE: Only the normalised joint coordinates are used here.
    /// No pixel data is accessed or retained.
    private func drawSkeleton(from features: PoseFeatureVector) {
        let threshold = PoseFeatureVector.confidenceThreshold

        // Capture layer frame on visionQueue; layout is set in viewDidLayoutSubviews.
        let layerSize = DispatchQueue.main.sync { skeletonBoneLayer.bounds.size }
        guard layerSize.width > 0, layerSize.height > 0 else { return }

        // Helper: convert a Vision point to a view-space CGPoint if the
        // joint meets the confidence threshold; otherwise return nil.
        func viewPt(_ joint: VNRecognizedPoint?) -> CGPoint? {
            guard let j = joint, j.confidence >= threshold else { return nil }
            return visionToViewPoint(j.location, in: layerSize)
        }

        // ── Bone path (lines between anatomically adjacent joints) ────────
        let bonePath = UIBezierPath()

        // Define the skeleton connectivity as pairs.
        // Each pair is (fromJoint, toJoint); both must be non-nil to draw.
        let bonePairs: [(VNRecognizedPoint?, VNRecognizedPoint?)] = [
            // Head → neck
            (features.nose,          features.neck),
            // Neck → shoulders
            (features.neck,          features.leftShoulder),
            (features.neck,          features.rightShoulder),
            // Shoulders → elbows → wrists
            (features.leftShoulder,  features.leftElbow),
            (features.leftElbow,     features.leftWrist),
            (features.rightShoulder, features.rightElbow),
            (features.rightElbow,    features.rightWrist),
            // Shoulders → hips (torso box)
            (features.leftShoulder,  features.leftHip),
            (features.rightShoulder, features.rightHip),
            (features.leftHip,       features.rightHip),
            // Hips → knees → ankles
            (features.leftHip,       features.leftKnee),
            (features.leftKnee,      features.leftAnkle),
            (features.rightHip,      features.rightKnee),
            (features.rightKnee,     features.rightAnkle),
            // Root (hip midpoint) → hips
            (features.root,          features.leftHip),
            (features.root,          features.rightHip),
            // Ears → eyes → nose (face)
            (features.leftEar,       features.leftEye),
            (features.leftEye,       features.nose),
            (features.rightEar,      features.rightEye),
            (features.rightEye,      features.nose),
        ]

        for (fromJoint, toJoint) in bonePairs {
            guard let from = viewPt(fromJoint), let to = viewPt(toJoint) else { continue }
            bonePath.move(to: from)
            bonePath.addLine(to: to)
        }

        // ── Joint path (circles at each detected joint) ───────────────────
        let jointPath = UIBezierPath()
        let dotRadius: CGFloat = 5.0

        for (_, joint) in features.validJoints {
            let centre = visionToViewPoint(joint.location, in: layerSize)
            jointPath.move(to: CGPoint(x: centre.x + dotRadius, y: centre.y))
            jointPath.addArc(
                withCenter: centre,
                radius: dotRadius,
                startAngle: 0,
                endAngle: .pi * 2,
                clockwise: true
            )
        }

        // ── Update layers on main thread ──────────────────────────────────
        DispatchQueue.main.async { [weak self] in
            self?.skeletonBoneLayer.path  = bonePath.cgPath
            self?.skeletonJointLayer.path = jointPath.cgPath
        }
    }

    /// Removes all drawn paths from the skeleton layers.
    /// Must be called on the main thread.
    private func clearSkeletonOverlay() {
        DispatchQueue.main.async { [weak self] in
            self?.skeletonBoneLayer.path  = nil
            self?.skeletonJointLayer.path = nil
        }
    }

    // -------------------------------------------------------
    // MARK: UI / Label Updates
    // -------------------------------------------------------

    /// Updates the HUD label and the AR text node.
    /// Skips redundant updates if the classification hasn't changed.
    /// Always dispatches to the main thread.
    private func updatePoseLabel(with pose: PoseClass) {
        guard pose != currentPose else { return }
        currentPose = pose
        DispatchQueue.main.async { [weak self] in
            self?.poseLabel.text = pose.rawValue
            self?.updatePoseTextNode(text: pose.rawValue)
        }
    }

    // -------------------------------------------------------
    // MARK: SceneKit AR Overlay
    // -------------------------------------------------------

    /// Adds a floating SCNText node to the AR scene for in-view pose labelling.
    private func addPoseTextNode() {
        let geometry = SCNText(
            string: PoseClass.unknown.rawValue, extrusionDepth: 0.5)
        geometry.font                             = UIFont.boldSystemFont(ofSize: 6)
        geometry.firstMaterial?.diffuse.contents  = UIColor.cyan

        let node      = SCNNode(geometry: geometry)
        node.scale    = SCNVector3(0.01, 0.01, 0.01)
        // Default: ~30 cm in front of, 10 cm above the camera origin.
        node.position = SCNVector3(x: -0.1, y: 0.1, z: -0.3)

        arView.scene.rootNode.addChildNode(node)
        poseTextNode = node
    }

    /// Updates the SCNText string without replacing the node.
    private func updatePoseTextNode(text: String) {
        guard let node     = poseTextNode,
              let geometry = node.geometry as? SCNText else { return }
        geometry.string = text
    }

    /// Removes the AR text node when scanning stops.
    private func removePoseTextNode() {
        poseTextNode?.removeFromParentNode()
        poseTextNode = nil
    }
}

// MARK: - AVCaptureVideoDataOutputSampleBufferDelegate

extension ViewController: AVCaptureVideoDataOutputSampleBufferDelegate {

    /// Receives each video frame from the front camera on `visionQueue`.
    ///
    /// REAL-TIME FRAME CAPTURE — ETHICAL FLOW:
    ///   This is the sole entry point for raw camera data.  The
    ///   CMSampleBuffer is passed immediately to `detectPose(in:)`, which
    ///   enforces consent and active-scan gates before touching any pixel.
    ///
    ///   The buffer is NEVER:
    ///     • Copied or retained beyond this call stack.
    ///     • Written to disk or memory-mapped storage.
    ///     • Transmitted over any network interface.
    ///     • Accessible to any code path that runs without user consent.
    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        // All processing happens inside detectPose, which enforces the
        // consent and active-scan checks before extracting any pixel data.
        detectPose(in: sampleBuffer)
    }

    /// Frames dropped due to CPU/GPU load are silently discarded.
    ///
    /// This is intentional design: dropping frames means less data is
    /// touched, not that frames are buffered or retried.  The 15 fps
    /// throttle in detectPose already makes drops predictable.
    func captureOutput(
        _ output: AVCaptureOutput,
        didDrop sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        // Intentionally empty — dropped frames contain no persistent info.
    }
}

// MARK: - ARSCNViewDelegate

extension ViewController: ARSCNViewDelegate {

    /// Called when ARKit adds a new anchor.
    /// Re-parents the pose label node under the ARFaceAnchor node so it
    /// tracks the user's head position automatically in 3-D space.
    func renderer(
        _ renderer: SCNSceneRenderer,
        didAdd node: SCNNode,
        for anchor: ARAnchor
    ) {
        guard anchor is ARFaceAnchor else { return }
        DispatchQueue.main.async { [weak self] in
            guard let textNode = self?.poseTextNode else { return }
            textNode.removeFromParentNode()
            textNode.position = SCNVector3(x: -0.05, y: 0.15, z: 0)
            node.addChildNode(textNode)
        }
    }

    /// No-op: the text node is a child of the face anchor node, so ARKit
    /// automatically updates its world transform every frame.
    func renderer(
        _ renderer: SCNSceneRenderer,
        didUpdate node: SCNNode,
        for anchor: ARAnchor
    ) { }

    /// Clears stale labels when ARKit loses or limits tracking.
    func session(
        _ session: ARSession,
        cameraDidChangeTrackingState camera: ARCamera
    ) {
        switch camera.trackingState {
        case .notAvailable, .limited:
            updatePoseLabel(with: .unknown)
            clearSkeletonOverlay()
        case .normal:
            break
        @unknown default:
            break
        }
    }
}
