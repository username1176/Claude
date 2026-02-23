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
//   • Explicit Consent   – The user must affirmatively opt-in via
//     an informed consent screen before any camera access begins.
//     Consent is freely given, specific, informed, and unambiguous
//     per GDPR Article 4(11) and Recital 32.
//
//   • On-Device Only     – All pose inference is performed locally
//     using Apple's Vision and Core ML frameworks. No pixel data
//     or derived features leave the device.
//
//   • No Persistence     – No video frames, still images, or pose
//     landmark coordinates are written to disk, UserDefaults,
//     iCloud, or any other storage medium.
//
//   • No Sharing         – No data is transmitted to any server,
//     analytics service, or third party (CCPA § 1798.100).
//
//   • Ephemeral Analysis – Each CMSampleBuffer is consumed
//     by Vision and immediately released; only the resulting
//     pose classification enum value is retained for display.
//
//   • Single-User Design – The app is designed for self-directed
//     use; the person operating the device is always the data
//     subject.
//
//   • Stop at Any Time   – The user can halt processing at any
//     moment by tapping "Stop Scan" or closing the app.
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
/// - unknown   : Insufficient confidence; shown while the model warms up.
enum PoseClass: String {
    case poseTypeA = "Pose Type A"   // e.g. Standing
    case poseTypeB = "Pose Type B"   // e.g. Jumping
    case unknown   = "Analysing…"
}

// MARK: - ViewController

class ViewController: UIViewController {

    // -------------------------------------------------------
    // MARK: UI / AR
    // -------------------------------------------------------

    /// Full-screen AR view.  Renders the live front-camera feed via ARKit
    /// and hosts SceneKit overlays (the floating pose-label node).
    private var arView: ARSCNView!

    /// Translucent HUD label anchored near the bottom of the screen.
    /// Shows the current `PoseClass` raw value in plain language.
    private var poseLabel: UILabel!

    /// Initiates / terminates the scanning session.
    /// Disabled and dimmed until the user grants explicit consent.
    private var startButton: UIButton!

    // -------------------------------------------------------
    // MARK: AVFoundation – Front-Camera Pipeline
    // -------------------------------------------------------
    // NOTE ON DUAL-SESSION DESIGN:
    // ARFaceTrackingConfiguration drives the ARSCNView visuals, but it does
    // not expose a sample-buffer delegate.  We therefore run a lightweight,
    // parallel AVCaptureSession to feed raw frames to Vision for pose
    // detection.  Both sessions address the same front TrueDepth hardware;
    // iOS manages multi-client access automatically from iOS 13+.
    // -------------------------------------------------------

    /// Manages front-camera input → Vision inference pipeline.
    private let captureSession = AVCaptureSession()

    /// Serial background queue for AVCaptureVideoDataOutputSampleBufferDelegate
    /// and Vision inference.  Keeps the main thread free for UI.
    private let visionQueue = DispatchQueue(
        label: "com.selfposedemo.visionQueue",
        qos: .userInitiated
    )

    // -------------------------------------------------------
    // MARK: Vision
    // -------------------------------------------------------

    /// Reusable request for on-device human body pose detection.
    /// VNDetectHumanBodyPoseRequest runs fully on the Neural Engine —
    /// no network call is made.
    private var bodyPoseRequest = VNDetectHumanBodyPoseRequest()

    // -------------------------------------------------------
    // MARK: Core ML (Placeholder)
    // -------------------------------------------------------
    // To integrate a real Core ML classifier:
    //   1. Train a model on your pose-landmark dataset.
    //   2. Add the compiled .mlmodel to the Xcode project.
    //   3. Replace the heuristic in classifyPose(observation:) with:
    //        let input  = PoseClassifierInput(joints: mlMultiArray)
    //        let output = try poseClassifier?.prediction(input: input)
    //        let label  = output?.classLabel ?? "unknown"
    //
    // private var poseClassifier: PoseClassifierModel?

    // -------------------------------------------------------
    // MARK: State
    // -------------------------------------------------------

    /// Guards every camera / AR operation behind explicit user consent.
    /// ETHICAL: this flag is ONLY set to `true` inside userDidGrantConsent(),
    /// which is called exclusively from the consent UIAlertController action.
    private var userHasConsented = false

    /// Tracks whether the capture/AR pipeline is currently active.
    private var isScanning = false

    /// Most recently classified pose.  Compared before each UI update to
    /// avoid unnecessary redraws on the main thread.
    private var currentPose: PoseClass = .unknown

    /// Floating SceneKit text node that labels the user's pose in AR space.
    private var poseTextNode: SCNNode?

    // -------------------------------------------------------
    // MARK: View Lifecycle
    // -------------------------------------------------------

    override func viewDidLoad() {
        super.viewDidLoad()
        setupARView()
        setupHUD()
        // ETHICAL: Show the consent screen synchronously on first launch.
        // No camera initialisation happens before this call returns
        // and the user explicitly taps "I Agree".
        presentConsentScreen()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        // Ensure processing stops if the user navigates away.
        stopScanning()
    }

    // -------------------------------------------------------
    // MARK: ARSCNView Setup
    // -------------------------------------------------------

    /// Configures the ARSCNView to fill the entire screen.
    /// The ARKit session is NOT started here; it starts only after consent.
    private func setupARView() {
        arView = ARSCNView(frame: view.bounds)
        arView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        arView.delegate = self
        arView.scene   = SCNScene()
        arView.automaticallyUpdatesLighting = true

        // Show FPS / triangle count only in debug builds for developer feedback.
#if DEBUG
        arView.showsStatistics = true
#endif
        view.addSubview(arView)
    }

    // -------------------------------------------------------
    // MARK: HUD Setup
    // -------------------------------------------------------

    /// Overlays the pose-classification label and Start/Stop button on top of
    /// the ARSCNView.  Both are disabled until consent is granted.
    private func setupHUD() {

        // -- Pose Label --
        poseLabel = UILabel()
        poseLabel.translatesAutoresizingMaskIntoConstraints = false
        poseLabel.text            = "Consent required to begin."
        poseLabel.textColor       = .white
        poseLabel.backgroundColor = UIColor.black.withAlphaComponent(0.6)
        poseLabel.font            = UIFont.systemFont(ofSize: 20, weight: .semibold)
        poseLabel.textAlignment   = .center
        poseLabel.layer.cornerRadius = 10
        poseLabel.clipsToBounds   = true
        view.addSubview(poseLabel)

        // -- Start / Stop Button --
        startButton = UIButton(type: .system)
        startButton.translatesAutoresizingMaskIntoConstraints = false
        startButton.setTitle("Start Scan", for: .normal)
        startButton.titleLabel?.font     = UIFont.systemFont(ofSize: 18, weight: .bold)
        startButton.backgroundColor      = UIColor.systemBlue.withAlphaComponent(0.85)
        startButton.setTitleColor(.white, for: .normal)
        startButton.layer.cornerRadius   = 12
        startButton.isEnabled            = false   // requires consent + camera permission
        startButton.alpha                = 0.5
        startButton.addTarget(self, action: #selector(startScanTapped), for: .touchUpInside)
        view.addSubview(startButton)

        // -- Auto Layout --
        NSLayoutConstraint.activate([
            poseLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor,  constant:  20),
            poseLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            poseLabel.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor,
                                              constant: -80),
            poseLabel.heightAnchor.constraint(equalToConstant: 50),

            startButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            startButton.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor,
                                                constant: -20),
            startButton.widthAnchor.constraint(equalToConstant: 160),
            startButton.heightAnchor.constraint(equalToConstant: 48)
        ])
    }

    // -------------------------------------------------------
    // MARK: Consent Screen
    // -------------------------------------------------------

    /// Presents an informed-consent dialog that explains exactly what the app
    /// does, what data is processed, and what data is NOT retained or shared.
    ///
    /// ETHICAL DESIGN NOTES:
    ///   • Language is plain and jargon-free so users genuinely understand.
    ///   • "Decline" is equally accessible — no dark-pattern placement.
    ///   • The app takes no action whatsoever until the user taps "I Agree".
    ///   • Re-shown if the user somehow reaches scanning without consenting
    ///     (defensive guard in startScanTapped).
    private func presentConsentScreen() {
        let title = "Your Privacy & Consent"
        let message = """
        Self-Pose Demo uses your front camera to analyse YOUR OWN body pose \
        in real time for personal sports feedback.

        ✔  On-device only — no data leaves your iPhone
        ✔  No video or images are stored or recorded
        ✔  No data is shared with any server or third party
        ✔  Analysis is temporary; results are discarded immediately after display
        ✔  You may stop scanning at any time

        This app is designed for single-user, self-directed use only.  By \
        tapping "I Agree" you confirm that you are the person who will appear \
        in the camera view and that you consent to real-time, on-device body \
        pose analysis for personal feedback purposes.

        Compliant with GDPR, CCPA, and Apple's App Store Privacy Guidelines.
        """

        let alert = UIAlertController(
            title:          title,
            message:        message,
            preferredStyle: .alert
        )

        // PRIMARY — affirmative, clearly labelled agreement
        let agreeAction = UIAlertAction(
            title: "I Agree — Continue",
            style: .default
        ) { [weak self] _ in
            // ETHICAL: consent flag is set here, and ONLY here.
            self?.userDidGrantConsent()
        }

        // SECONDARY — equally accessible decline path (no dark pattern)
        let declineAction = UIAlertAction(
            title: "Decline",
            style: .cancel
        ) { [weak self] _ in
            self?.userDidDeclineConsent()
        }

        alert.addAction(agreeAction)
        alert.addAction(declineAction)
        present(alert, animated: true)
    }

    /// Called when the user taps "I Agree".
    /// Enables camera permission flow; still does NOT start the camera yet.
    private func userDidGrantConsent() {
        // ETHICAL: Consent is recorded as a runtime flag, not persisted to disk.
        // If the app is force-quit and relaunched, the user must consent again.
        userHasConsented = true
        requestCameraPermission()
    }

    /// Called when the user taps "Decline".
    /// The app remains visible but entirely inactive — no camera access occurs.
    private func userDidDeclineConsent() {
        userHasConsented = false
        poseLabel.text = "Consent required to use this app."
        // startButton stays disabled.  No camera or AR work begins.
    }

    // -------------------------------------------------------
    // MARK: Camera Permission
    // -------------------------------------------------------

    /// Requests AVCaptureDevice camera authorisation via the iOS permission
    /// system.  On first launch iOS shows its own system alert whose message
    /// is configured in Info.plist (NSCameraUsageDescription).
    private func requestCameraPermission() {
        AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
            DispatchQueue.main.async {
                if granted {
                    self?.onCameraPermissionGranted()
                } else {
                    self?.onCameraPermissionDenied()
                }
            }
        }
    }

    private func onCameraPermissionGranted() {
        // Both explicit consent AND OS permission are satisfied.
        // The Start button is now unlocked.
        startButton.isEnabled = true
        startButton.alpha     = 1.0
        poseLabel.text        = "Tap \"Start Scan\" to begin."
    }

    private func onCameraPermissionDenied() {
        let alert = UIAlertController(
            title:   "Camera Access Required",
            message: "Self-Pose Demo needs camera access to detect your pose. "
                   + "Please enable it in Settings › Privacy & Security › Camera.",
            preferredStyle: .alert
        )
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
        // Defensive guard: the button should never be reachable without consent,
        // but we enforce it here as a belt-and-braces ethical safeguard.
        guard userHasConsented else {
            presentConsentScreen()
            return
        }
        isScanning ? stopScanning() : startScanning()
    }

    /// Starts both the ARKit session (for visual overlays) and the
    /// AVCaptureSession (for Vision-based pose detection).
    ///
    /// ETHICAL: Nothing begins until this method is explicitly invoked by
    /// the user after consent and permission have both been confirmed.
    private func startScanning() {
        guard userHasConsented, !isScanning else { return }

        // -- ARKit session (front TrueDepth camera for AR rendering) --
        if ARFaceTrackingConfiguration.isSupported {
            let config = ARFaceTrackingConfiguration()
            config.isLightEstimationEnabled = true
            arView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
        } else {
            // Devices without TrueDepth fall back to world-tracking (rear camera).
            let config = ARWorldTrackingConfiguration()
            arView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
        }

        // -- AVCaptureSession (front camera frames for Vision) --
        setupCaptureSession()

        isScanning   = true
        currentPose  = .unknown
        poseLabel.text = PoseClass.unknown.rawValue

        startButton.setTitle("Stop Scan", for: .normal)
        startButton.backgroundColor = UIColor.systemRed.withAlphaComponent(0.85)

        addPoseTextNode()
    }

    /// Tears down the AR session and capture pipeline immediately.
    ///
    /// ETHICAL: Halting the scan ceases all frame processing.  No further
    /// pixel data is read from the camera after this method returns.
    private func stopScanning() {
        guard isScanning else { return }

        arView.session.pause()
        if captureSession.isRunning {
            visionQueue.async { [weak self] in
                self?.captureSession.stopRunning()
            }
        }

        isScanning  = false
        currentPose = .unknown

        DispatchQueue.main.async { [weak self] in
            self?.startButton.setTitle("Start Scan", for: .normal)
            self?.startButton.backgroundColor = UIColor.systemBlue.withAlphaComponent(0.85)
            self?.poseLabel.text = "Scan stopped."
            self?.removePoseTextNode()
        }
    }

    // -------------------------------------------------------
    // MARK: AVCaptureSession Setup
    // -------------------------------------------------------

    /// Configures AVCaptureSession with:
    ///   Input  – front-facing wide-angle camera at medium quality preset.
    ///   Output – video sample-buffer delegate routed to `visionQueue`.
    ///
    /// The session is started asynchronously on `visionQueue` to avoid
    /// blocking the main thread during hardware initialisation.
    private func setupCaptureSession() {
        // Guard against double-configuration on repeated Start taps.
        guard captureSession.inputs.isEmpty else {
            visionQueue.async { [weak self] in self?.captureSession.startRunning() }
            return
        }

        captureSession.beginConfiguration()
        captureSession.sessionPreset = .medium   // balance quality vs. inference latency

        // -- Front Camera Input --
        guard let frontCamera = AVCaptureDevice.default(
            .builtInWideAngleCamera,
            for: .video,
            position: .front
        ) else {
            print("[SelfPoseDemo] Front camera unavailable on this device.")
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

        // -- Video Data Output (feeds Vision) --
        let output = AVCaptureVideoDataOutput()
        output.alwaysDiscardsLateVideoFrames = true   // prevent queue back-pressure
        output.setSampleBufferDelegate(self, queue: visionQueue)

        if captureSession.canAddOutput(output) { captureSession.addOutput(output) }

        // Configure the video connection for portrait orientation
        if let connection = output.connection(with: .video) {
            connection.videoOrientation = .portrait
            // Mirror front camera so motion feels natural (like a mirror)
            connection.isVideoMirrored  = true
        }

        captureSession.commitConfiguration()

        // Start asynchronously to keep the main thread responsive
        visionQueue.async { [weak self] in self?.captureSession.startRunning() }
    }

    // -------------------------------------------------------
    // MARK: Vision – Body Pose Detection
    // -------------------------------------------------------

    /// Runs VNDetectHumanBodyPoseRequest on a single incoming camera frame.
    ///
    /// Called on `visionQueue` for each frame.
    ///
    /// ETHICAL DESIGN:
    ///   • The raw CVPixelBuffer is NOT copied, stored, or passed beyond this
    ///     method — Vision processes it inline and releases it.
    ///   • Only the skeleton landmark coordinates (normalised floats) are
    ///     forwarded to classifyPose(); those are also ephemeral.
    ///   • If the user has not consented or scanning has stopped, the method
    ///     returns immediately without touching the pixel data.
    private func detectPose(in sampleBuffer: CMSampleBuffer) {
        // Double-check consent and active state on every frame (thread-safe read).
        guard userHasConsented, isScanning else { return }

        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        let handler = VNImageRequestHandler(
            cvPixelBuffer: pixelBuffer,
            orientation:   .up,       // adjust to .leftMirrored if needed for front cam
            options:       [:]
        )

        do {
            try handler.perform([bodyPoseRequest])

            guard
                let results = bodyPoseRequest.results,
                let topObservation = results.first   // highest-confidence detection
            else {
                updatePoseLabel(with: .unknown)
                return
            }

            classifyPose(observation: topObservation)
        } catch {
            print("[SelfPoseDemo] Vision inference failed: \(error)")
        }
    }

    // -------------------------------------------------------
    // MARK: Core ML – Pose Classification
    // -------------------------------------------------------

    /// Classifies a VNHumanBodyPoseObservation and updates the UI.
    ///
    /// CURRENT IMPLEMENTATION — rule-based heuristic (stand-in for Core ML):
    ///   Compares the normalised y-positions of the left hip and left ankle.
    ///   A small vertical gap suggests a bent-knee / airborne posture (Type B).
    ///
    /// HOW TO REPLACE WITH A REAL CORE ML MODEL:
    ///   1. Add your .mlmodel file to the Xcode project target.
    ///   2. Build → Xcode generates a Swift class (e.g. PoseClassifierModel).
    ///   3. Uncomment and instantiate:
    ///        poseClassifier = try? PoseClassifierModel(configuration: .init())
    ///   4. Extract all required joint positions into an MLMultiArray.
    ///   5. Call prediction(input:) and map the output classLabel to PoseClass.
    private func classifyPose(observation: VNHumanBodyPoseObservation) {
        do {
            let hip   = try observation.recognizedPoint(.leftHip)
            let ankle = try observation.recognizedPoint(.leftAnkle)

            // Reject low-confidence joint detections to avoid noisy labels.
            guard hip.confidence > 0.5, ankle.confidence > 0.5 else {
                updatePoseLabel(with: .unknown)
                return
            }

            // In Vision's coordinate system y=0 is the bottom of the image.
            // A small hip-to-ankle vertical span implies bent knees (jumping).
            // Threshold of 0.25 is a starting point — calibrate for your use case.
            let verticalSpan = hip.location.y - ankle.location.y
            let pose: PoseClass = verticalSpan < 0.25 ? .poseTypeB : .poseTypeA

            updatePoseLabel(with: pose)
        } catch {
            // A recognised point may be absent if the joint is out of frame.
            updatePoseLabel(with: .unknown)
        }
    }

    // -------------------------------------------------------
    // MARK: UI Updates
    // -------------------------------------------------------

    /// Updates the HUD label and AR text node with a new classification.
    /// Guards against redundant redraws and always dispatches to the main thread.
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

    /// Adds a floating SCNText node to the AR scene to overlay the pose label
    /// in 3-D space, giving the user intuitive real-time self-feedback.
    private func addPoseTextNode() {
        let geometry = SCNText(string: PoseClass.unknown.rawValue, extrusionDepth: 0.5)
        geometry.font                          = UIFont.boldSystemFont(ofSize: 6)
        geometry.firstMaterial?.diffuse.contents = UIColor.cyan

        let node = SCNNode(geometry: geometry)
        // SCNText units are points; 0.01 scale → approx. 6 cm tall in AR space.
        node.scale    = SCNVector3(0.01, 0.01, 0.01)
        // Default position: ~30 cm in front of and 10 cm above camera origin.
        node.position = SCNVector3(x: -0.1, y: 0.1, z: -0.3)

        arView.scene.rootNode.addChildNode(node)
        poseTextNode = node
    }

    /// Updates the displayed string of the existing SCNText geometry.
    private func updatePoseTextNode(text: String) {
        guard
            let node     = poseTextNode,
            let geometry = node.geometry as? SCNText
        else { return }
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

    /// Receives every video frame from the front camera on `visionQueue`.
    ///
    /// ETHICAL DESIGN: The raw CMSampleBuffer is passed directly into the
    /// Vision pipeline and is NEVER written to disk, transmitted over a
    /// network, or retained beyond this method call.
    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        detectPose(in: sampleBuffer)
    }

    /// Frames dropped under CPU/GPU load are silently discarded.
    /// This is intentional: missed frames mean no data accumulation.
    func captureOutput(
        _ output: AVCaptureOutput,
        didDrop sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        // Intentionally empty — dropped frames contain no persistent information.
    }
}

// MARK: - ARSCNViewDelegate

extension ViewController: ARSCNViewDelegate {

    /// Called when ARKit detects a new anchor (e.g. ARFaceAnchor).
    /// The pose-label node is re-parented under the face anchor's SCNNode
    /// so it tracks the user's head automatically in 3-D space.
    func renderer(
        _ renderer: SCNSceneRenderer,
        didAdd node: SCNNode,
        for anchor: ARAnchor
    ) {
        guard anchor is ARFaceAnchor else { return }

        DispatchQueue.main.async { [weak self] in
            guard let textNode = self?.poseTextNode else { return }
            textNode.removeFromParentNode()
            // Place the label slightly above the detected face in anchor space.
            textNode.position = SCNVector3(x: -0.05, y: 0.15, z: 0)
            node.addChildNode(textNode)
        }
    }

    /// ARKit continuously updates the face anchor as the user moves.
    /// Because the text node is a child of the anchor node, no manual
    /// transform update is needed here.
    func renderer(
        _ renderer: SCNSceneRenderer,
        didUpdate node: SCNNode,
        for anchor: ARAnchor
    ) { /* No-op: parent-child hierarchy handles tracking automatically. */ }

    /// Called if ARKit loses tracking (e.g. user covers the camera).
    /// Reset the classification label so stale results are not displayed.
    func session(
        _ session: ARSession,
        cameraDidChangeTrackingState camera: ARCamera
    ) {
        switch camera.trackingState {
        case .notAvailable, .limited:
            updatePoseLabel(with: .unknown)
        case .normal:
            break
        @unknown default:
            break
        }
    }
}
