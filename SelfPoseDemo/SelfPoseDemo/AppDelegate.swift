// AppDelegate.swift
// Self-Pose Demo
//
// Standard UIApplicationDelegate entry point.
// No analytics SDKs, crash reporters, or third-party libraries are
// initialised here, consistent with the app's on-device-only data policy.
//
// Copyright © 2025 Self-Pose Demo. Educational use only.

import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        // No third-party SDK initialisation intentionally — see ethical use notice
        // in ViewController.swift.
        return true
    }

    // MARK: UISceneSession Lifecycle

    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        return UISceneConfiguration(
            name: "Default Configuration",
            sessionRole: connectingSceneSession.role
        )
    }

    func application(
        _ application: UIApplication,
        didDiscardSceneSessions sceneSessions: Set<UISceneSession>
    ) { }
}
