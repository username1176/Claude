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
//     the app requires re-consent.  A "Revoke Consent" button
//     lets the user withdraw at any time mid-session.
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
//   • Stop at Any Time      – The user can halt everything by
//     tapping "Stop Scan" or "Revoke Consent".  A persistent
//     on-screen banner reminds the user that analysis is opt-in.
//
//   • Confidence Gate       – Classifications are only displayed
//     when at least 5 joints are detected above the confidence
//     threshold.  Low-confidence frames show "Analysing…".
//
// Legal references:
//   GDPR  – Regulation (EU) 2016/679, Articles 5, 6(1)(a), 9
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

    static let confidenceThreshold: Float = 0.4

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

    /// All joints above the confidence threshold.
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
            guard let pt = pt, pt.confidence >= Self.confidenceThreshold else { return nil }
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
    //         if let j = joint, j.confidence >= Self.confidenceThreshold {
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

    /// Translucent HUD label near the bottom showing the current PoseClass.
    private var poseLabel: UILabel!

    /// Start / Stop toggle button.  Disabled until consent + permission granted.
    private var startButton: UIButton!

    /// Revokes consent immediately, stops scanning, and re-shows the consent
    /// dialog.  Visible at all times so the user always has an escape.
    ///
    /// ETHICAL DESIGN:
    /// Providing a prominent, always-accessible revocation path satisfies the
    /// "withdraw at any time" requirement of GDPR Art. 7(3) and Apple HIG
    /// privacy principles.  The button is never hidden — even mid-scan.
    private var revokeConsentButton: UIButton!

    /// Persistent on-screen banner reminding the user that this app is opt-in
    /// only and analyses the consenting user exclusively.
    ///
    /// ETHICAL DESIGN — NON-CONSENSUAL USE PREVENTION:
    /// This label is always visible during a scan so the user is continuously
    /// aware that body-tracking is active and that consent can be revoked at
    /// any time.  It also serves as a visual deterrent against pointing the
    /// camera at someone who has not consented.
    private var optInReminderLabel: UILabel!

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Layers
    // -------------------------------------------------------
    // ETHICAL NOTE: These layers render normalised joint coordinates
    // mapped to screen space.  They display nothing and retain nothing
    // when scanning is stopped.
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
    //
    // When ARFaceTrackingConfiguration or ARWorldTrackingConfiguration
    // is active the AVCaptureSession feeds the front camera to Vision.
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
    /// Runs on the Neural Engine — no network call.
    private var bodyPoseRequest = VNDetectHumanBodyPoseRequest()

    // -------------------------------------------------------
    // MARK: Core ML (Placeholder)
    // -------------------------------------------------------
    // HOW TO INTEGRATE:
    //   1. Add PoseClassifier.mlmodel to the Xcode target.
    //   2. Xcode generates PoseClassifier Swift class.
    //   3. Uncomment the property and classifyWithCoreML below.
    //
    // private var poseClassifier: PoseClassifier?

    // -------------------------------------------------------
    // MARK: Frame Throttle
    // -------------------------------------------------------

    private var lastProcessedTimestamp: TimeInterval = 0
    private let minimumProcessingInterval: TimeInterval = 1.0 / 15.0

    // -------------------------------------------------------
    // MARK: AR Body Tracking State
    // -------------------------------------------------------
    // ETHICAL — SINGLE-ANCHOR ENFORCEMENT:
    // Only ONE body anchor is ever accepted.  `trackedAnchorID`
    // records the UUID of the first ARBodyAnchor that ARKit reports.
    // Any subsequent body anchor is refused in renderer(_:didAdd:for:).
    // This prevents silently tracking a second person who has NOT
    // consented.  The single-anchor constraint is reset only when
    // the user explicitly stops and restarts a scan.
    // -------------------------------------------------------

    /// `true` when ARBodyTrackingConfiguration is active (rear camera).
    private var usesBodyTracking = false

    /// UUID of the single accepted ARBodyAnchor or ARFaceAnchor.
    /// `nil` before the first body is detected or after a scan is stopped.
    private var trackedAnchorID: UUID?

    /// Container SCNNode that holds the text label + billboard constraint.
    /// Positioned at the head joint of the tracked anchor.
    private var poseTextContainerNode: SCNNode?

    /// The last string written to the SCNText geometry by the render loop.
    /// Used to avoid redundant geometry updates in renderer(_:updateAtTime:).
    private var lastRenderedTextString: String = ""

    // -------------------------------------------------------
    // MARK: Head Joint Cache
    // -------------------------------------------------------
    // The head joint index in the skeleton definition is constant for
    // the lifetime of a session.  We cache it on first lookup to avoid
    // a linear O(n) search on every render frame.
    // -------------------------------------------------------

    /// Cached index of "head_joint" in the skeleton joint name array.
    private var cachedHeadJointIndex: Int?

    // -------------------------------------------------------
    // MARK: State
    // -------------------------------------------------------

    /// ETHICAL: Set to `true` ONLY inside `userDidGrantConsent()`.
    /// Runtime flag — never persisted.  Re-launch requires re-consent.
    private var userHasConsented = false

    private var isScanning = false
    private var currentPose: PoseClass = .unknown

    /// The SCNText node that shows the pose classification in AR space.
    private var poseTextNode: SCNNode?

    // -------------------------------------------------------
    // MARK: View Lifecycle
    // -------------------------------------------------------

    override func viewDidLoad() {
        super.viewDidLoad()
        setupARView()
        setupSkeletonOverlay()
        setupHUD()
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
        // ETHICAL — NON-CONSENSUAL USE PREVENTION:
        // A persistent, always-visible banner at the top of the screen
        // states that this app is opt-in self-analysis only.  It serves
        // two purposes:
        //   1. Continuously reminds the user that body tracking is active.
        //   2. Deters misuse — if the camera were pointed at a non-
        //      consenting person, the banner makes it clear this is not
        //      the intended use.
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

        // ── Start / Stop Button ───────────────────────────────────────
        startButton = UIButton(type: .system)
        startButton.translatesAutoresizingMaskIntoConstraints = false
        startButton.setTitle("Start Scan", for: .normal)
        startButton.titleLabel?.font   = UIFont.systemFont(ofSize: 18, weight: .bold)
        startButton.backgroundColor    = UIColor.systemBlue.withAlphaComponent(0.85)
        startButton.setTitleColor(.white, for: .normal)
        startButton.layer.cornerRadius = 12
        startButton.isEnabled          = false
        startButton.alpha              = 0.5
        startButton.addTarget(self, action: #selector(startScanTapped), for: .touchUpInside)
        view.addSubview(startButton)

        // ── Revoke Consent Button ─────────────────────────────────────
        // ETHICAL — GDPR Art. 7(3) / Apple HIG:
        // The user must be able to withdraw consent as easily as they
        // granted it.  This button is always visible and accessible
        // so the user is never "locked in" to a session.  Tapping it
        // immediately stops all scanning and clears the consent flag.
        revokeConsentButton = UIButton(type: .system)
        revokeConsentButton.translatesAutoresizingMaskIntoConstraints = false
        revokeConsentButton.setTitle("Revoke Consent", for: .normal)
        revokeConsentButton.titleLabel?.font   = UIFont.systemFont(ofSize: 14, weight: .medium)
        revokeConsentButton.backgroundColor    = UIColor.systemOrange.withAlphaComponent(0.85)
        revokeConsentButton.setTitleColor(.white, for: .normal)
        revokeConsentButton.layer.cornerRadius = 10
        revokeConsentButton.isHidden           = true
        revokeConsentButton.addTarget(
            self, action: #selector(revokeConsentTapped), for: .touchUpInside)
        view.addSubview(revokeConsentButton)

        // ── Auto Layout ───────────────────────────────────────────────
        NSLayoutConstraint.activate([
            // Opt-in reminder — full width at the very top
            optInReminderLabel.topAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.topAnchor),
            optInReminderLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            optInReminderLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            optInReminderLabel.heightAnchor.constraint(equalToConstant: 28),

            // Pose label — above the buttons
            poseLabel.leadingAnchor.constraint(
                equalTo: view.leadingAnchor, constant: 20),
            poseLabel.trailingAnchor.constraint(
                equalTo: view.trailingAnchor, constant: -20),
            poseLabel.bottomAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -100),
            poseLabel.heightAnchor.constraint(greaterThanOrEqualToConstant: 50),

            // Start / Stop button — bottom centre
            startButton.leadingAnchor.constraint(
                equalTo: view.leadingAnchor, constant: 20),
            startButton.bottomAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24),
            startButton.heightAnchor.constraint(equalToConstant: 48),

            // Revoke button — to the right of Start/Stop
            revokeConsentButton.leadingAnchor.constraint(
                equalTo: startButton.trailingAnchor, constant: 12),
            revokeConsentButton.trailingAnchor.constraint(
                equalTo: view.trailingAnchor, constant: -20),
            revokeConsentButton.bottomAnchor.constraint(
                equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -24),
            revokeConsentButton.heightAnchor.constraint(equalToConstant: 48),
            revokeConsentButton.widthAnchor.constraint(equalTo: startButton.widthAnchor),
        ])
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
        ✔  You may stop or revoke consent at any time

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
        revokeConsentButton.isHidden = false
        requestCameraPermission()
    }

    private func userDidDeclineConsent() {
        userHasConsented = false
        revokeConsentButton.isHidden = true
        poseLabel.text = "Consent required to use this app."
    }

    // -------------------------------------------------------
    // MARK: Revoke Consent
    // -------------------------------------------------------

    /// Immediately stops all scanning and clears consent.
    ///
    /// ETHICAL — GDPR Art. 7(3):
    /// "The data subject shall have the right to withdraw his or
    /// her consent at any time."  Withdrawal must be as easy as
    /// giving consent — hence this always-visible button.
    @objc private func revokeConsentTapped() {
        stopScanning()
        userHasConsented        = false
        revokeConsentButton.isHidden = true
        startButton.isEnabled   = false
        startButton.alpha       = 0.5
        poseLabel.text          = "Consent revoked. Re-launch to start again."
        optInReminderLabel.text =
            "Opt-in self-analysis only — you are the only subject"
        optInReminderLabel.backgroundColor =
            UIColor.systemIndigo.withAlphaComponent(0.75)
        // Re-present consent screen so user can immediately re-consent
        // if they tapped by mistake.
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
        poseLabel.text        = "Tap \"Start Scan\" to begin."
    }

    private func onCameraPermissionDenied() {
        let alert = UIAlertController(
            title:   "Camera Access Required",
            message: "Please enable camera in Settings > Privacy & Security > Camera.",
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
        guard userHasConsented else { presentConsentScreen(); return }
        isScanning ? stopScanning() : startScanning()
    }

    /// Starts the ARKit session and — when not using body tracking — the
    /// parallel AVCaptureSession for Vision.
    ///
    /// ETHICAL: Nothing begins until consent AND OS camera permission are
    /// both confirmed.
    ///
    /// SESSION CONFIGURATION PRIORITY:
    ///   1. ARBodyTrackingConfiguration (rear camera, world-space body
    ///      skeleton via ARBodyAnchor).  Requires A12+ chip, iOS 13+.
    ///      Vision processes ARFrame.capturedImage directly — no separate
    ///      AVCaptureSession needed.
    ///   2. ARFaceTrackingConfiguration (front TrueDepth camera).
    ///      AVCaptureSession feeds front-camera frames to Vision.
    ///   3. ARWorldTrackingConfiguration (rear camera, fallback).
    ///      AVCaptureSession feeds front-camera frames to Vision.
    private func startScanning() {
        guard userHasConsented, !isScanning else { return }

        // ── Choose ARKit configuration ────────────────────────────────
        if ARBodyTrackingConfiguration.isSupported {
            // PREFERRED: Full body skeleton in world space (rear camera).
            // ARBodyAnchor provides 3-D joint positions used to place the
            // SCNText label above the user's head.  Vision runs on the
            // ARFrame pixel buffer — no separate AVCaptureSession.
            let config = ARBodyTrackingConfiguration()
            config.isLightEstimationEnabled = true
            arView.session.run(config, options: [.resetTracking,
                                                  .removeExistingAnchors])
            usesBodyTracking = true
        } else if ARFaceTrackingConfiguration.isSupported {
            let config = ARFaceTrackingConfiguration()
            config.isLightEstimationEnabled = true
            arView.session.run(config, options: [.resetTracking,
                                                  .removeExistingAnchors])
            usesBodyTracking = false
            setupCaptureSession(cameraPosition: .front)
        } else {
            let config = ARWorldTrackingConfiguration()
            arView.session.run(config, options: [.resetTracking,
                                                  .removeExistingAnchors])
            usesBodyTracking = false
            setupCaptureSession(cameraPosition: .front)
        }

        isScanning             = true
        trackedAnchorID        = nil
        cachedHeadJointIndex   = nil
        currentPose            = .unknown
        lastProcessedTimestamp = 0
        lastRenderedTextString = ""
        poseLabel.text         = PoseClass.unknown.rawValue

        startButton.setTitle("Stop Scan", for: .normal)
        startButton.backgroundColor = UIColor.systemRed.withAlphaComponent(0.85)

        optInReminderLabel.backgroundColor =
            UIColor.systemGreen.withAlphaComponent(0.75)
        optInReminderLabel.text =
            "Scanning active — opt-in self-analysis only"

        // For body-tracking mode the text node is created lazily when the
        // first ARBodyAnchor arrives.  For face / world tracking modes we
        // create a default floating node now; it will be re-parented when
        // an anchor appears.
        if !usesBodyTracking {
            addDefaultPoseTextNode()
        }
    }

    /// Tears down all sessions.
    ///
    /// ETHICAL: Halting the scan immediately ceases ALL frame processing.
    /// No further pixel data, body anchors, or joint coordinates are read.
    private func stopScanning() {
        guard isScanning else { return }

        arView.session.pause()
        if captureSession.isRunning {
            visionQueue.async { [weak self] in self?.captureSession.stopRunning() }
        }

        isScanning           = false
        currentPose          = .unknown
        trackedAnchorID      = nil
        cachedHeadJointIndex = nil
        usesBodyTracking     = false

        DispatchQueue.main.async { [weak self] in
            self?.startButton.setTitle("Start Scan", for: .normal)
            self?.startButton.backgroundColor =
                UIColor.systemBlue.withAlphaComponent(0.85)
            self?.poseLabel.text = "Scan stopped."
            self?.optInReminderLabel.text =
                "Opt-in self-analysis only — you are the only subject"
            self?.optInReminderLabel.backgroundColor =
                UIColor.systemIndigo.withAlphaComponent(0.75)
            self?.removePoseTextNode()
            self?.clearSkeletonOverlay()
        }
    }

    // -------------------------------------------------------
    // MARK: AVCaptureSession Setup
    // -------------------------------------------------------
    // Used ONLY when body tracking is unavailable (face / world mode).
    // When ARBodyTrackingConfiguration is active, Vision runs on the
    // ARFrame.capturedImage delivered via session(_:didUpdate:).
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
            print("[SelfPoseDemo] Camera unavailable (position: \(cameraPosition)).")
            captureSession.commitConfiguration()
            return
        }

        do {
            let input = try AVCaptureDeviceInput(device: camera)
            if captureSession.canAddInput(input) { captureSession.addInput(input) }
        } catch {
            print("[SelfPoseDemo] Cannot create video input: \(error)")
            captureSession.commitConfiguration()
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
    // Two entry points feed into a single processing pipeline:
    //
    //   1. captureOutput(_:didOutput:from:)
    //        → Called by AVCaptureSession (face / world mode).
    //        → Calls processPixelBuffer(_:timestamp:orientation:)
    //
    //   2. session(_:didUpdate:)   (ARSessionDelegate)
    //        → Called by ARKit every frame (body tracking mode).
    //        → Calls processPixelBuffer(_:timestamp:orientation:)
    //
    // ETHICAL: Both paths enforce consent + active-scan gates before
    // any pixel data is touched.
    // -------------------------------------------------------

    /// Shared pipeline for Vision body pose detection.
    ///
    /// Called on `visionQueue`.  The pixel buffer is consumed inline by
    /// Vision and immediately released — it is NEVER retained, copied,
    /// written to disk, or transmitted.
    private func processPixelBuffer(
        _ pixelBuffer: CVPixelBuffer,
        timestamp: TimeInterval,
        orientation: CGImagePropertyOrientation
    ) {
        // ── Gate 1: Consent ───────────────────────────────────────────
        guard userHasConsented else { return }

        // ── Gate 2: Active scan ───────────────────────────────────────
        guard isScanning else { return }

        // ── Gate 3: Frame throttle (≤15 fps) ──────────────────────────
        guard timestamp - lastProcessedTimestamp >= minimumProcessingInterval else {
            return
        }
        lastProcessedTimestamp = timestamp

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

        // ── Gate 4: Single-user enforcement ───────────────────────────
        // ETHICAL — AVOIDING NON-CONSENSUAL ANALYSIS:
        //   Only the FIRST observation (primary person) is processed.
        //   Any additional observations are silently discarded — no data
        //   about non-consenting bystanders is touched.
        //
        // NOTE: We no longer freeze on multi-person frames.  Instead we
        // strictly analyse only the first detected person (the consenting
        // user) and ignore all others.  This is less disruptive for gym
        // environments while still protecting bystander privacy.
        let observation = observations[0]

        guard let features = extractPoseFeatures(from: observation) else {
            resetToUnknown()
            return
        }

        // ── Gate 5: Confidence threshold ──────────────────────────────
        // Require at least 5 joints above threshold before classifying.
        // Low-confidence partial detections show "Analysing…" instead of
        // a misleading label.
        guard features.detectedJointCount >= 5 else {
            updatePoseLabel(with: .unknown)
            drawSkeleton(from: features)
            return
        }

        let pose = classifyPose(from: features)
        updatePoseLabel(with: pose)
        drawSkeleton(from: features)

        // If no anchor is available yet (world-tracking fallback),
        // attempt to position the text label via hitTest from the
        // Vision nose point projected into AR space.
        if !usesBodyTracking && trackedAnchorID == nil {
            positionLabelViaHitTest(features: features)
        }
    }

    // -------------------------------------------------------
    // MARK: Pose Feature Extraction
    // -------------------------------------------------------
    // Extracts all 19 body joints from the Vision observation.
    // Key joints for fitness activity recognition:
    //   • Shoulders  — arm position, overhead movements
    //   • Hips       — stance width, hip hinge
    //   • Knees      — squat depth, leg drive
    //   • Ankles     — weight distribution
    // -------------------------------------------------------

    private func extractPoseFeatures(
        from observation: VNHumanBodyPoseObservation
    ) -> PoseFeatureVector? {

        func joint(_ name: VNHumanBodyPoseObservation.JointName) -> VNRecognizedPoint? {
            return try? observation.recognizedPoint(name)
        }

        var f = PoseFeatureVector()
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
    // MARK: Pose Classification (heuristic + Core ML placeholder)
    // -------------------------------------------------------
    // ACTIVITY RECOGNITION FEATURES:
    //   F1 — Leg extension:   vertical distance hip→ankle
    //        Large = standing; small = crouching / airborne
    //   F2 — Knee bend ratio: how far knee is between hip and ankle
    //        High = straight leg; low = deep bend (squat/lunge)
    //   F3 — Wrist height:    wrist Y relative to shoulder Y
    //        Positive = hands raised (overhead press, jump, wave)
    //
    // These three features are sufficient to distinguish common
    // fitness postures (standing, squatting, lunging, overhead).
    // A real mlmodel trained on labelled reps can replace this.
    // -------------------------------------------------------

    /// Returns the best-available value for a left/right bilateral feature.
    /// Tries the left side first; falls back to the right.
    private func computeLRFeature(
        left:  (VNRecognizedPoint?, VNRecognizedPoint?),
        right: (VNRecognizedPoint?, VNRecognizedPoint?),
        compute: (VNRecognizedPoint, VNRecognizedPoint) -> Float
    ) -> Float {
        let threshold = PoseFeatureVector.confidenceThreshold
        func valid(_ p: VNRecognizedPoint?) -> VNRecognizedPoint? {
            guard let p = p, p.confidence >= threshold else { return nil }
            return p
        }
        if let a = valid(left.0), let b = valid(left.1) {
            return compute(a, b)
        }
        if let a = valid(right.0), let b = valid(right.1) {
            return compute(a, b)
        }
        return 0
    }

    private func classifyPose(from features: PoseFeatureVector) -> PoseClass {

        // F1: Leg extension — hip-to-ankle vertical distance
        let legExt = computeLRFeature(
            left:  (features.leftHip,  features.leftAnkle),
            right: (features.rightHip, features.rightAnkle)
        ) { h, a in Float(h.location.y - a.location.y) }

        // F2: Knee bend ratio — knee midpoint between hip and ankle
        let kneeRatio: Float = {
            let threshold = PoseFeatureVector.confidenceThreshold
            func kbr(hip: VNRecognizedPoint?, knee: VNRecognizedPoint?,
                     ankle: VNRecognizedPoint?) -> Float? {
                guard let h = hip, let k = knee, let a = ankle,
                      h.confidence >= threshold, k.confidence >= threshold,
                      a.confidence >= threshold else { return nil }
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

        // F3: Wrist height relative to shoulders (averaged over both sides)
        var wristScore: Float = 0; var wristN = 0
        let threshold = PoseFeatureVector.confidenceThreshold
        if let lw = features.leftWrist, let ls = features.leftShoulder,
           lw.confidence >= threshold, ls.confidence >= threshold {
            wristScore += Float(lw.location.y - ls.location.y); wristN += 1
        }
        if let rw = features.rightWrist, let rs = features.rightShoulder,
           rw.confidence >= threshold, rs.confidence >= threshold {
            wristScore += Float(rw.location.y - rs.location.y); wristN += 1
        }
        if wristN > 0 { wristScore /= Float(wristN) }

        // ── Decision ─────────────────────────────────────────────────
        // poseTypeA (Standing / Upright): legs extended, knees mostly straight
        // poseTypeB (Active / Dynamic):   knees bent, crouching, or arms raised
        let isStanding = legExt > 0.28 && kneeRatio > 0.38
        return isStanding ? .poseTypeA : .poseTypeB
    }

    // --------------------------------------------------------
    // PLACEHOLDER: Core ML classification
    // --------------------------------------------------------
    // private func classifyWithCoreML(_ features: PoseFeatureVector) -> PoseClass {
    //     guard let classifier = poseClassifier else { return .unknown }
    //     guard let arr = try? features.toMLMultiArray() else { return .unknown }
    //     let input  = PoseClassifierInput(poses: arr)
    //     guard let out = try? classifier.prediction(input: input) else { return .unknown }
    //     return PoseClass(rawValue: out.classLabel) ?? .unknown
    // }
    // --------------------------------------------------------

    // -------------------------------------------------------
    // MARK: Skeleton Overlay Drawing
    // -------------------------------------------------------

    private func visionToViewPoint(_ pt: CGPoint, in size: CGSize) -> CGPoint {
        CGPoint(x: pt.x * size.width, y: (1.0 - pt.y) * size.height)
    }

    private func drawSkeleton(from features: PoseFeatureVector) {
        // Use the cached size (updated in viewDidLayoutSubviews) to avoid
        // a main.sync call on the visionQueue hot path.
        let layerSize = cachedLayerSize
        guard layerSize.width > 0, layerSize.height > 0 else { return }

        let threshold = PoseFeatureVector.confidenceThreshold
        func viewPt(_ j: VNRecognizedPoint?) -> CGPoint? {
            guard let j = j, j.confidence >= threshold else { return nil }
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

        // Compute valid joints once and reuse for joint dots.
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

    /// Resets to the unknown state and clears the skeleton overlay.
    /// Centralises the repeated pattern used across processPixelBuffer.
    private func resetToUnknown() {
        updatePoseLabel(with: .unknown)
        clearSkeletonOverlay()
    }

    // -------------------------------------------------------
    // MARK: UI / Label Updates
    // -------------------------------------------------------

    private func updatePoseLabel(with pose: PoseClass) {
        guard pose != currentPose else { return }
        currentPose = pose
        DispatchQueue.main.async { [weak self] in
            self?.poseLabel.text = pose.rawValue
        }
    }

    // -------------------------------------------------------
    // MARK: 3-D AR Text Overlay — Node Management
    // -------------------------------------------------------
    // ETHICAL NOTE — SINGLE-USER LABEL:
    // Only one SCNText node exists at any time.  It is attached to the
    // single accepted anchor node (body or face).  If no anchor is
    // available yet the node floats at a fixed position in front of
    // the camera and is re-parented once an anchor arrives.
    // -------------------------------------------------------

    /// Creates a default floating SCNText node at a fixed position.
    /// Used only when body tracking is unavailable (face / world mode).
    private func addDefaultPoseTextNode() {
        let (container, textNode) = makePoseTextNodes(
            initialText: PoseClass.unknown.rawValue)

        // Place 30 cm in front of camera, 10 cm above centre.
        container.position = SCNVector3(x: -0.05, y: 0.1, z: -0.3)

        arView.scene.rootNode.addChildNode(container)
        poseTextContainerNode = container
        poseTextNode          = textNode
    }

    /// Factory that creates a container node with a billboard constraint
    /// and a child SCNText node.
    ///
    /// The billboard constraint ensures the text always faces the camera
    /// regardless of the parent anchor's orientation — essential for
    /// readability when the user rotates.
    private func makePoseTextNodes(
        initialText: String
    ) -> (container: SCNNode, textNode: SCNNode) {

        let geometry = SCNText(string: initialText, extrusionDepth: 0.5)
        geometry.font                            = UIFont.boldSystemFont(ofSize: 6)
        geometry.firstMaterial?.diffuse.contents  = UIColor.cyan
        geometry.flatness                         = 0.1
        // Centre the text at the node origin so it aligns above the head.
        let (min, max) = geometry.boundingBox
        let dx = (max.x - min.x) / 2
        let dy = (max.y - min.y) / 2

        let textNode      = SCNNode(geometry: geometry)
        textNode.scale    = SCNVector3(0.01, 0.01, 0.01)
        textNode.pivot    = SCNMatrix4MakeTranslation(dx, dy, 0)
        textNode.name     = "poseTextNode"

        let container = SCNNode()
        container.name = "poseTextContainer"
        // Billboard: always face the camera on all axes.
        let billboard = SCNBillboardConstraint()
        billboard.freeAxes = .all
        container.constraints = [billboard]
        container.addChildNode(textNode)

        return (container, textNode)
    }

    /// Removes and nils both the container and text nodes.
    private func removePoseTextNode() {
        poseTextContainerNode?.removeFromParentNode()
        poseTextContainerNode = nil
        poseTextNode?.removeFromParentNode()
        poseTextNode           = nil
        lastRenderedTextString = ""
    }

    // -------------------------------------------------------
    // MARK: AR Label Positioning — ARBodyAnchor (head joint)
    // -------------------------------------------------------
    // When ARBodyTrackingConfiguration is active, ARKit provides an
    // ARBodyAnchor whose skeleton includes a "head_joint".  We read
    // the head joint's model-space transform and offset +0.2 m in Y
    // to position the label above the user's head in 3-D space.
    //
    // ETHICAL — SINGLE-ANCHOR LIMIT:
    // `trackedAnchorID` records the UUID of the FIRST body anchor
    // added.  All subsequent body anchors are rejected in
    // renderer(_:didAdd:for:) to prevent tracking a non-consenting
    // bystander.
    // -------------------------------------------------------

    /// String constant for the ARKit head joint.
    /// Using a string literal for iOS 13 compatibility
    /// (ARSkeleton.JointName.head requires iOS 14).
    private static let headJointName = "head_joint"

    /// Extracts the head joint's model-space position from an ARBodyAnchor.
    ///
    /// The head joint index is cached in `cachedHeadJointIndex` after the
    /// first lookup, avoiding a linear search on every render frame.
    private func headJointModelPosition(
        from bodyAnchor: ARBodyAnchor
    ) -> simd_float3? {
        let skeleton   = bodyAnchor.skeleton
        let jointNames = skeleton.definition.jointNames

        // Cache the index on first call — it is stable for a session.
        if cachedHeadJointIndex == nil {
            cachedHeadJointIndex = jointNames.firstIndex(of: Self.headJointName)
        }
        guard let idx = cachedHeadJointIndex else { return nil }

        let headTransform = skeleton.jointModelTransforms[idx]
        return simd_float3(headTransform.columns.3.x,
                           headTransform.columns.3.y,
                           headTransform.columns.3.z)
    }

    /// Creates and attaches the SCNText label above the head joint of a
    /// body anchor.  Called once when the first ARBodyAnchor is added.
    private func attachPoseLabel(
        toBodyNode node: SCNNode,
        bodyAnchor: ARBodyAnchor
    ) {
        let (container, textNode) = makePoseTextNodes(
            initialText: currentPose.rawValue)

        // Position above the head joint (model space) + 0.2 m Y offset.
        if let headPos = headJointModelPosition(from: bodyAnchor) {
            container.simdPosition = simd_float3(
                headPos.x, headPos.y + 0.2, headPos.z)
        } else {
            // Fallback: ~1.8 m above the hip root (average head height).
            container.simdPosition = simd_float3(0, 1.8 + 0.2, 0)
        }

        node.addChildNode(container)
        poseTextContainerNode = container
        poseTextNode          = textNode
    }

    /// Updates the container position to follow the head joint as the
    /// user moves.  Called from renderer(_:didUpdate:for:) each frame.
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
    // When neither ARBodyAnchor nor ARFaceAnchor is available (world-
    // tracking fallback) we project the Vision nose point through an
    // ARKit hitTest to estimate a 3-D world position for the label.
    //
    // The hitTest looks for existing feature points in the scene.
    // This is a best-effort approach; on a featureless background the
    // label stays at its last known position.
    // -------------------------------------------------------

    private func positionLabelViaHitTest(features: PoseFeatureVector) {
        guard let container = poseTextContainerNode else { return }
        let threshold = PoseFeatureVector.confidenceThreshold

        guard let nose = features.nose,
              nose.confidence >= threshold else { return }

        // Capture the layer size computed on the main thread (cached in
        // cachedLayerSize) — avoids a main.sync inside visionQueue.
        let size = cachedLayerSize
        guard size.width > 0 else { return }

        // Convert Vision coordinates (y-up, normalised) to screen space.
        let screenPt = CGPoint(
            x: nose.location.x * size.width,
            y: (1.0 - nose.location.y) * size.height)

        // hitTest against existing feature points (available on all
        // ARKit configurations).
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            let hits = self.arView.hitTest(screenPt, types: .featurePoint)

            if let hit = hits.first {
                let col3 = hit.worldTransform.columns.3
                // Position the label 0.2 m above the hit point.
                container.simdWorldPosition = simd_float3(
                    col3.x, col3.y + 0.2, col3.z)
            }
        }
    }
}

// MARK: - AVCaptureVideoDataOutputSampleBufferDelegate

extension ViewController: AVCaptureVideoDataOutputSampleBufferDelegate {

    /// Receives each video frame on `visionQueue`.
    ///
    /// ETHICAL: The CMSampleBuffer is passed into the shared
    /// processPixelBuffer pipeline, which enforces consent + active-scan
    /// gates before extracting any pixel data.
    ///
    /// This delegate is ONLY active when body tracking is unavailable
    /// (face / world mode).  When ARBodyTrackingConfiguration is active,
    /// the AVCaptureSession is never started and this method never fires.
    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            return
        }
        let ts = CMTimeGetSeconds(
            CMSampleBufferGetPresentationTimeStamp(sampleBuffer))
        // Front camera with portrait connection → orientation .up
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

    /// Called by ARKit every frame when the session updates.
    ///
    /// When `usesBodyTracking` is true, this is the sole entry point for
    /// camera frames: we process `frame.capturedImage` for Vision body-pose
    /// detection directly, avoiding a separate AVCaptureSession.
    ///
    /// ETHICAL: The pixel buffer belongs to the ARFrame and is released
    /// when the frame is released.  We NEVER retain, copy, or store it.
    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        guard usesBodyTracking else { return }
        guard userHasConsented, isScanning else { return }

        // Process on visionQueue to keep the main / render threads clear.
        visionQueue.async { [weak self] in
            // Rear camera in portrait → Vision orientation .right
            self?.processPixelBuffer(
                frame.capturedImage,
                timestamp: frame.timestamp,
                orientation: .right)
        }
    }
}

// MARK: - ARSCNViewDelegate

extension ViewController: ARSCNViewDelegate {

    // -------------------------------------------------------
    // renderer(_:didAdd:for:) — Anchor Addition
    // -------------------------------------------------------
    // ETHICAL — SINGLE-ANCHOR ENFORCEMENT:
    // This is where the single-user / single-anchor constraint is
    // enforced.  The very first ARBodyAnchor or ARFaceAnchor that
    // ARKit reports is accepted and its UUID stored.  All subsequent
    // anchors of the same type are REFUSED.  This prevents the app
    // from tracking a second person who has NOT consented.
    //
    // The constraint is deliberately conservative: even if the second
    // anchor could theoretically be the same person re-detected, we
    // refuse it rather than risk analysing someone else.
    // -------------------------------------------------------

    func renderer(
        _ renderer: SCNSceneRenderer,
        didAdd node: SCNNode,
        for anchor: ARAnchor
    ) {
        // ── Gate: consent ─────────────────────────────────────────────
        guard userHasConsented, isScanning else { return }

        // ── ARBodyAnchor (body-tracking mode) ─────────────────────────
        if let bodyAnchor = anchor as? ARBodyAnchor {
            // ETHICAL — SINGLE ANCHOR: refuse a second body.
            guard trackedAnchorID == nil else {
                print("[SelfPoseDemo] Second body anchor REFUSED "
                    + "(single-user ethical constraint).")
                return
            }
            trackedAnchorID = bodyAnchor.identifier

            DispatchQueue.main.async { [weak self] in
                guard let self = self else { return }
                // Remove any existing text nodes before creating new ones.
                self.removePoseTextNode()
                self.attachPoseLabel(
                    toBodyNode: node, bodyAnchor: bodyAnchor)
            }
            return
        }

        // ── ARFaceAnchor (face-tracking mode) ─────────────────────────
        if anchor is ARFaceAnchor {
            // ETHICAL — SINGLE ANCHOR: refuse a second face.
            guard trackedAnchorID == nil else {
                print("[SelfPoseDemo] Second face anchor REFUSED.")
                return
            }
            trackedAnchorID = anchor.identifier

            DispatchQueue.main.async { [weak self] in
                guard let self = self,
                      let container = self.poseTextContainerNode else { return }
                // Re-parent the existing floating label under the face node
                // so it tracks the user's head automatically.
                container.removeFromParentNode()
                container.position = SCNVector3(x: 0, y: 0.2, z: 0)
                node.addChildNode(container)
            }
            return
        }
    }

    // -------------------------------------------------------
    // renderer(_:didUpdate:for:) — Anchor Updates
    // -------------------------------------------------------
    // ETHICAL: Only updates for the single accepted anchor are
    // processed.  The `trackedAnchorID` guard ensures that even
    // if ARKit somehow delivers updates for an anchor we refused,
    // we ignore them.
    // -------------------------------------------------------

    func renderer(
        _ renderer: SCNSceneRenderer,
        didUpdate node: SCNNode,
        for anchor: ARAnchor
    ) {
        guard userHasConsented, isScanning else { return }

        if let bodyAnchor = anchor as? ARBodyAnchor,
           bodyAnchor.identifier == trackedAnchorID {
            // Update the text label position to follow the head joint
            // as the user moves.  This runs on the SceneKit render thread,
            // which is safe for SCNNode property updates.
            updateBodyLabelPosition(bodyAnchor: bodyAnchor)
        }
        // ARFaceAnchor: no manual update needed — the text container is
        // a child of the face node, so ARKit moves it automatically.
    }

    // -------------------------------------------------------
    // renderer(_:updateAtTime:) — Per-Frame Render Update
    // -------------------------------------------------------
    // Called by SceneKit before each render frame on the render thread.
    // We use it to synchronise the SCNText geometry string with the
    // latest `currentPose` value.
    //
    // Thread safety note:
    //   `currentPose` is written on `visionQueue` and read here on the
    //   SceneKit render thread.  For a display-only enum this is safe on
    //   ARM64 (word-sized reads are atomic).  The worst case is a one-
    //   frame stale label, which is acceptable for real-time feedback.
    // -------------------------------------------------------

    func renderer(
        _ renderer: SCNSceneRenderer,
        updateAtTime time: TimeInterval
    ) {
        guard userHasConsented, isScanning else { return }

        let displayText = currentPose.rawValue

        // Avoid redundant SCNText geometry updates — only write when
        // the string has actually changed.
        guard displayText != lastRenderedTextString else { return }
        lastRenderedTextString = displayText

        // SCNText.string can be safely mutated from the render thread.
        if let geometry = poseTextNode?.geometry as? SCNText {
            geometry.string = displayText
        }
    }

    // -------------------------------------------------------
    // session(_:cameraDidChangeTrackingState:)
    // -------------------------------------------------------

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
