// SceneDelegate.swift
// Self-Pose Demo
//
// UIWindowSceneDelegate that sets ViewController as the root.
// No scene state is persisted between sessions, which ensures
// that camera/AR state is never inadvertently restored.
//
// Copyright © 2025 Self-Pose Demo. Educational use only.

import UIKit

class SceneDelegate: UIResponder, UIWindowSceneDelegate {

    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }

        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = ViewController()
        self.window = window
        window.makeKeyAndVisible()
    }

    // MARK: Scene Lifecycle

    func sceneDidDisconnect(_ scene: UIScene) {
        // Called when the scene is released. If scanning was active it has
        // already been stopped via viewWillDisappear in ViewController.
    }

    func sceneDidBecomeActive(_ scene: UIScene) { }
    func sceneWillResignActive(_ scene: UIScene) { }
    func sceneWillEnterForeground(_ scene: UIScene) { }
    func sceneDidEnterBackground(_ scene: UIScene) { }
}
