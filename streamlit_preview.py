"""
streamlit_preview.py — Self-Pose Demo · Interactive Web Preview
===============================================================
Run with:
    pip install streamlit
    streamlit run streamlit_preview.py
"""

import random
import time
import math
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Self-Pose Demo — iOS AR Preview",
    page_icon="🦴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared colour tokens (match the iOS app) ─────────────────────────────────
CYAN   = "#32D7EC"
DARK   = "#0C0C18"
CARD   = "#13132A"
AMBER  = "#FFB347"
GREEN  = "#34C759"
RED    = "#FF3B30"
GRAY   = "#8E8E93"
WHITE  = "#F2F2F7"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── root ── */
  :root {{
    --cyan:{CYAN}; --dark:{DARK}; --card:{CARD};
    --amber:{AMBER}; --green:{GREEN}; --red:{RED}; --white:{WHITE};
  }}
  .stApp {{ background:{DARK}; color:{WHITE}; }}

  /* ── sidebar ── */
  section[data-testid="stSidebar"] {{
    background:{CARD} !important;
    border-right:1px solid rgba(50,215,236,0.15);
  }}
  section[data-testid="stSidebar"] * {{ color:{WHITE} !important; }}

  /* ── tab bar ── */
  .stTabs [data-baseweb="tab-list"] {{
    gap:4px; background:transparent;
    border-bottom:1px solid rgba(50,215,236,0.2);
  }}
  .stTabs [data-baseweb="tab"] {{
    background:transparent; color:{GRAY}; font-size:13px;
    border-radius:8px 8px 0 0; padding:6px 14px;
  }}
  .stTabs [aria-selected="true"] {{
    background:rgba(50,215,236,0.12) !important;
    color:{CYAN} !important; border-bottom:2px solid {CYAN};
  }}

  /* ── metric cards ── */
  div[data-testid="stMetric"] {{
    background:{CARD}; border-radius:12px; padding:14px;
    border:1px solid rgba(50,215,236,0.15);
  }}
  div[data-testid="stMetricValue"] {{ color:{CYAN} !important; }}

  /* ── code blocks ── */
  .stCode {{ font-size:12px; }}

  /* ── expanders ── */
  .streamlit-expanderHeader {{
    background:{CARD} !important; border-radius:8px;
    color:{WHITE} !important;
  }}

  /* ── phone frame helpers ── */
  .phone-screen {{
    background:{DARK};
    border:2.5px solid rgba(255,255,255,0.12);
    border-radius:40px;
    padding:28px 18px 22px;
    max-width:340px;
    margin:auto;
    position:relative;
    box-shadow:0 0 60px rgba(50,215,236,0.08);
  }}
  .phone-notch {{
    width:100px; height:22px; background:#111;
    border-radius:0 0 14px 14px;
    margin:-28px auto 16px;
  }}
  .phone-bar {{
    width:100px; height:4px;
    background:rgba(255,255,255,0.25);
    border-radius:2px; margin:14px auto 0;
  }}

  /* ── status badges ── */
  .badge {{
    display:inline-block; padding:2px 8px;
    border-radius:99px; font-size:11px; font-weight:600;
  }}
  .badge-green {{ background:rgba(52,199,89,0.18); color:{GREEN}; }}
  .badge-cyan  {{ background:rgba(50,215,236,0.18); color:{CYAN}; }}
  .badge-amber {{ background:rgba(255,179,71,0.18); color:{AMBER}; }}
  .badge-red   {{ background:rgba(255,59,48,0.18);  color:{RED}; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding-bottom:12px;">
      <div style="font-size:36px;">🦴</div>
      <div style="font-size:20px;font-weight:700;color:{CYAN}">Self-Pose Demo</div>
      <div style="font-size:12px;color:{GRAY};margin-top:4px;">iOS 17 · ARKit · On-Device AI</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"<div style='font-size:11px;color:{GRAY};text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px'>Project</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-size:13px;line-height:2'>
    <span style='color:{CYAN}'>✦</span> iOS 17+ / A12 Bionic+<br>
    <span style='color:{CYAN}'>✦</span> ARKit · ARBodyTracking<br>
    <span style='color:{CYAN}'>✦</span> Vision · Core ML<br>
    <span style='color:{CYAN}'>✦</span> On-device only · No network<br>
    <span style='color:{CYAN}'>✦</span> GDPR · BIPA · CCPA compliant
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"<div style='font-size:11px;color:{GRAY};text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px'>File Tree</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='font-family:monospace;font-size:11.5px;line-height:1.8;color:{WHITE}'>
    SelfPoseDemo/<br>
    ├── <span style='color:{CYAN}'>SelfPoseDemo.xcodeproj/</span><br>
    │   └── project.pbxproj<br>
    └── <span style='color:{CYAN}'>SelfPoseDemo/</span><br>
    &nbsp;&nbsp;&nbsp;&nbsp;├── AppDelegate.swift<br>
    &nbsp;&nbsp;&nbsp;&nbsp;├── SceneDelegate.swift<br>
    &nbsp;&nbsp;&nbsp;&nbsp;├── <span style='color:{AMBER}'>ViewController.swift</span><br>
    &nbsp;&nbsp;&nbsp;&nbsp;├── Info.plist<br>
    &nbsp;&nbsp;&nbsp;&nbsp;├── <span style='color:{GREEN}'>LaunchScreen.storyboard</span><br>
    &nbsp;&nbsp;&nbsp;&nbsp;├── <span style='color:{GREEN}'>PrivacyInfo.xcprivacy</span><br>
    &nbsp;&nbsp;&nbsp;&nbsp;└── <span style='color:{GREEN}'>Assets.xcassets/</span><br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├── AppIcon.appiconset/<br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── AccentColor.colorset/
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"<span class='badge badge-green'>v1.0 · production-ready structure</span>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "📱 App Preview",
    "🤖 Live Pose Demo",
    "📋 Project Structure",
    "📄 Source Files",
    "🧪 Testing Guide",
    "⚖️ Ethical Notes",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — APP PREVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown(f"<h2 style='color:{CYAN};margin-bottom:4px'>App Preview</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{GRAY}'>Visual mockup of the launch screen and main AR HUD</p>", unsafe_allow_html=True)

    col_launch, col_hud = st.columns(2, gap="large")

    with col_launch:
        st.markdown(f"<div style='text-align:center;margin-bottom:8px;font-size:12px;color:{GRAY}'>LAUNCH SCREEN</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="phone-screen">
          <div class="phone-notch"></div>

          <!-- status bar -->
          <div style="display:flex;justify-content:space-between;font-size:10px;
                      color:rgba(255,255,255,0.5);padding:0 8px 18px;">
            <span>9:41</span><span>●●●  WiFi  🔋</span>
          </div>

          <!-- centred title block -->
          <div style="text-align:center;padding:40px 0 30px;">
            <div style="font-size:32px;font-weight:700;color:{WHITE};
                        letter-spacing:-0.5px;line-height:1.1">
              Self-Pose<br>Demo
            </div>
            <div style="font-size:14px;color:{CYAN};margin-top:10px;
                        letter-spacing:.06em">
              Personal Fitness · On-Device AI
            </div>
            <div style="width:80px;height:1px;background:rgba(255,255,255,0.15);
                        margin:18px auto;"></div>
          </div>

          <!-- spacer -->
          <div style="height:60px"></div>

          <!-- privacy footer -->
          <div style="text-align:center;font-size:10px;color:{GRAY};
                      padding:0 12px 4px;line-height:1.5">
            Requires explicit consent ·<br>For personal self-analysis only
          </div>
          <div class="phone-bar"></div>
        </div>
        """, unsafe_allow_html=True)

    with col_hud:
        st.markdown(f"<div style='text-align:center;margin-bottom:8px;font-size:12px;color:{GRAY}'>MAIN AR HUD (SCANNING ACTIVE)</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="phone-screen">
          <div class="phone-notch"></div>

          <!-- opt-in banner -->
          <div style="background:rgba(50,215,236,0.12);border:1px solid rgba(50,215,236,0.3);
                      border-radius:8px;padding:6px 10px;margin-bottom:8px;
                      font-size:10px;color:{CYAN};text-align:center">
            ✓ Self-analysis active · You consented · Tap Stop to end
          </div>

          <!-- camera area -->
          <div style="background:rgba(30,30,60,0.8);border-radius:16px;
                      height:300px;position:relative;overflow:hidden;
                      border:1px solid rgba(255,255,255,0.08)">

            <!-- skeleton stick figure -->
            <svg width="100%" height="100%" viewBox="0 0 240 300"
                 style="position:absolute;top:0;left:0">
              <!-- bones -->
              <line x1="120" y1="60"  x2="120" y2="100" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="120" y1="100" x2="90"  y2="130" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="120" y1="100" x2="150" y2="130" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="90"  y1="130" x2="80"  y2="170" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="150" y1="130" x2="160" y2="170" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="80"  y1="170" x2="78"  y2="205" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="160" y1="170" x2="162" y2="205" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="120" y1="100" x2="120" y2="180" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="120" y1="180" x2="100" y2="240" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="120" y1="180" x2="140" y2="240" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="100" y1="240" x2="98"  y2="280" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <line x1="140" y1="240" x2="142" y2="280" stroke="{CYAN}" stroke-width="2.5" opacity=".85"/>
              <!-- joints -->
              <circle cx="120" cy="55"  r="5" fill="{CYAN}"/>
              <circle cx="120" cy="100" r="5" fill="{CYAN}"/>
              <circle cx="90"  cy="130" r="4" fill="{CYAN}"/>
              <circle cx="150" cy="130" r="4" fill="{CYAN}"/>
              <circle cx="80"  cy="170" r="4" fill="{CYAN}"/>
              <circle cx="160" cy="170" r="4" fill="{CYAN}"/>
              <circle cx="78"  cy="205" r="4" fill="{CYAN}"/>
              <circle cx="162" cy="205" r="4" fill="{CYAN}"/>
              <circle cx="120" cy="180" r="5" fill="{CYAN}"/>
              <circle cx="100" cy="240" r="4" fill="{CYAN}"/>
              <circle cx="140" cy="240" r="4" fill="{CYAN}"/>
              <circle cx="98"  cy="280" r="4" fill="{CYAN}"/>
              <circle cx="142" cy="280" r="4" fill="{CYAN}"/>
              <!-- AR text label -->
              <rect x="60" y="10" width="120" height="30" rx="6"
                    fill="rgba(0,0,0,0.7)" stroke="{CYAN}" stroke-width="1"/>
              <text x="120" y="30" text-anchor="middle"
                    font-size="11" fill="{CYAN}" font-family="monospace">
                Standing / Upright  87%
              </text>
            </svg>

            <!-- scanning indicator -->
            <div style="position:absolute;top:8px;right:10px;
                        background:rgba(50,215,236,0.15);
                        border:1px solid rgba(50,215,236,0.5);
                        border-radius:8px;padding:4px 8px;
                        font-size:10px;color:{CYAN}">
              ⬤ SCANNING
            </div>
          </div>

          <!-- pose label HUD -->
          <div style="background:rgba(0,0,0,0.7);border:1px solid rgba(50,215,236,0.3);
                      border-radius:10px;padding:8px 14px;margin-top:8px;
                      text-align:center;font-size:13px;font-weight:600;color:{CYAN}">
            Standing / Upright&nbsp;&nbsp;87%&nbsp;&nbsp;<span style="color:{AMBER}">[DEMO]</span>
          </div>

          <!-- button row -->
          <div style="display:flex;gap:8px;margin-top:8px">
            <div style="flex:2;background:rgba(255,59,48,0.15);
                        border:1px solid rgba(255,59,48,0.4);
                        border-radius:10px;padding:8px;text-align:center;
                        font-size:12px;color:{RED}">■ Stop</div>
            <div style="flex:1.5;background:rgba(50,215,236,0.12);
                        border:1px solid rgba(50,215,236,0.3);
                        border-radius:10px;padding:8px;text-align:center;
                        font-size:12px;color:{CYAN}">⏸ Pause</div>
            <div style="flex:1;background:rgba(255,255,255,0.06);
                        border:1px solid rgba(255,255,255,0.15);
                        border-radius:10px;padding:8px;text-align:center;
                        font-size:12px;color:{WHITE}">⚙</div>
          </div>

          <div class="phone-bar"></div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Settings panel preview
    st.markdown(f"<h3 style='color:{WHITE}'>Settings Panel</h3>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:{CARD};border-radius:16px;padding:20px 24px;
                border:1px solid rgba(50,215,236,0.15);max-width:480px">
      <div style="font-size:15px;font-weight:600;color:{WHITE};margin-bottom:16px">
        ⚙ Settings
      </div>
      <div style="font-size:12px;color:{GRAY};margin-bottom:4px">Detection Sensitivity</div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
        <div style="flex:1;height:4px;background:linear-gradient(to right, {CYAN} 60%, rgba(255,255,255,0.1) 60%);
                    border-radius:2px"></div>
        <span style="font-size:12px;color:{CYAN};width:50px">Medium</span>
      </div>
      <div style="font-size:10px;color:{GRAY};margin-bottom:14px">
        ← Balanced &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Precise →
      </div>
      <div style="font-size:12px;color:{GRAY};margin-bottom:4px">Live FPS</div>
      <div style="font-size:20px;font-weight:700;color:{CYAN};margin-bottom:14px">28 fps</div>
      <div style="background:rgba(255,59,48,0.1);border:1px solid rgba(255,59,48,0.3);
                  border-radius:10px;padding:10px 14px;text-align:center;
                  font-size:13px;color:{RED}">
        Revoke Consent &amp; Stop
      </div>
      <div style="font-size:10px;color:{GRAY};text-align:center;margin-top:10px;line-height:1.6">
        You may withdraw consent at any time.<br>
        All analysis stops immediately.  No data is retained.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LIVE POSE DEMO
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown(f"<h2 style='color:{CYAN}'>Interactive Pose Classifier Demo</h2>", unsafe_allow_html=True)
    st.markdown(
        "Simulate the on-device Vision + Core ML pipeline. "
        "Adjust joint confidence and sensitivity to see how the classifier responds. "
        f"<span class='badge badge-amber'>[DEMO] — synthetic values only</span>",
        unsafe_allow_html=True,
    )
    st.write("")

    # ── controls ────────────────────────────────────────────────────────────
    col_ctrl, col_result = st.columns([1, 1], gap="large")

    with col_ctrl:
        st.markdown(f"<div style='font-size:13px;color:{GRAY};margin-bottom:12px'>SIMULATION CONTROLS</div>", unsafe_allow_html=True)

        pose_type = st.selectbox(
            "Simulated pose",
            ["Standing / Upright", "Active / Dynamic", "Random (auto-switch)"],
        )

        joint_conf = st.slider(
            "Average joint confidence", 0.0, 1.0, 0.72, 0.01,
            help="Simulates how confident Vision is about each detected joint (0–1).",
        )

        sensitivity = st.slider(
            "Detection sensitivity threshold", 0.1, 0.9, 0.4, 0.05,
            help="Mirrors the in-app slider. Classifications are suppressed below this threshold.",
        )

        joints_visible = st.slider(
            "Joints detected (of 19)", 0, 19, 14,
            help="Simulates partial occlusion or poor lighting.",
        )

        run_stream = st.toggle("Stream frames (simulate live AR)", value=False)

    with col_result:
        st.markdown(f"<div style='font-size:13px;color:{GRAY};margin-bottom:12px'>CLASSIFICATION OUTPUT</div>", unsafe_allow_html=True)

        # Compute simulated result
        overall_conf = (joints_visible / 19.0) * joint_conf
        suppressed   = overall_conf < sensitivity

        if suppressed:
            pose_label   = "Analysing…"
            confidence   = 0.0
            badge_color  = GRAY
            badge_class  = "badge-amber"
        else:
            if pose_type == "Random (auto-switch)":
                pose_label  = random.choice(["Standing / Upright", "Active / Dynamic"])
            else:
                pose_label = pose_type
            confidence  = min(1.0, overall_conf + random.gauss(0, 0.03))
            badge_color = GREEN
            badge_class = "badge-green"

        confidence_pct = int(confidence * 100)

        # ── HUD card ─────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="background:{CARD};border-radius:14px;padding:20px 24px;
                    border:1px solid rgba(50,215,236,0.2)">
          <div style="font-size:12px;color:{GRAY};margin-bottom:6px">POSE CLASSIFICATION</div>
          <div style="font-size:22px;font-weight:700;color:{badge_color};line-height:1.2">
            {pose_label}
          </div>
          {"<div style='font-size:28px;font-weight:800;color:" + CYAN + ";margin-top:6px'>" + str(confidence_pct) + "%</div>" if not suppressed else ""}
          <div style="margin-top:8px">
            <span class="badge badge-amber" style="font-size:10px">[DEMO] synthetic</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        # ── skeleton diagram ─────────────────────────────────────────────
        # generate joint positions with confidence > threshold highlighted
        joints = [
            ("nose",14,20), ("neck",14,35), ("lShoulder",8,42), ("rShoulder",20,42),
            ("lElbow",5,56), ("rElbow",23,56), ("lWrist",3,68), ("rWrist",25,68),
            ("root",14,58), ("lHip",10,65), ("rHip",18,65),
            ("lKnee",9,78), ("rKnee",19,78), ("lAnkle",8,90), ("rAnkle",20,90),
        ]

        active = set()
        for i, (name, _, _) in enumerate(joints):
            if i < joints_visible:
                active.add(name)

        bones = [
            ("nose","neck"), ("neck","lShoulder"), ("neck","rShoulder"),
            ("lShoulder","lElbow"), ("lElbow","lWrist"),
            ("rShoulder","rElbow"), ("rElbow","rWrist"),
            ("neck","root"), ("root","lHip"), ("root","rHip"),
            ("lHip","lKnee"), ("lKnee","lAnkle"),
            ("rHip","rKnee"), ("rKnee","rAnkle"),
        ]

        jmap = {n: (x, y) for n, x, y in joints}

        scale = 5  # each unit → 5px, grid is 28×100 → 140×500px → scale down

        svg_lines = []
        svg_circles = []

        for a, b in bones:
            if a in active and b in active:
                ax, ay = jmap[a]
                bx, by = jmap[b]
                color = CYAN
            else:
                ax, ay = jmap.get(a, (0, 0))
                bx, by = jmap.get(b, (0, 0))
                color = "rgba(255,255,255,0.12)"
            svg_lines.append(
                f'<line x1="{ax*scale}" y1="{ay*scale}" '
                f'x2="{bx*scale}" y2="{by*scale}" '
                f'stroke="{color}" stroke-width="2.5"/>'
            )

        for name, x, y in joints:
            fill = CYAN if name in active else "rgba(255,255,255,0.12)"
            svg_circles.append(
                f'<circle cx="{x*scale}" cy="{y*scale}" r="4" fill="{fill}"/>'
            )

        svg_content = "\n".join(svg_lines + svg_circles)
        svg_w = 28 * scale
        svg_h = 95 * scale

        st.markdown(f"""
        <div style="background:{CARD};border-radius:14px;padding:16px;
                    border:1px solid rgba(50,215,236,0.12);text-align:center">
          <div style="font-size:12px;color:{GRAY};margin-bottom:8px">
            SKELETON OVERLAY ({joints_visible}/19 joints active)
          </div>
          <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}"
               style="max-height:260px;width:auto">
            {svg_content}
          </svg>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── metrics row ──────────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Joints detected", f"{joints_visible} / 19")
    m2.metric("Overall confidence", f"{overall_conf:.0%}")
    m3.metric("Threshold", f"{sensitivity:.0%}")
    m4.metric("Status", "SUPPRESSED" if suppressed else "CLASSIFIED")

    # ── frame stream ─────────────────────────────────────────────────────────
    if run_stream:
        st.write("")
        st.markdown(f"<div style='color:{CYAN};font-size:13px'>Streaming simulated frames…</div>", unsafe_allow_html=True)
        stream_placeholder = st.empty()
        prog = st.progress(0)
        for frame_i in range(60):
            jitter_conf  = max(0, min(1, joint_conf + random.gauss(0, 0.05)))
            jitter_joints = max(0, min(19, joints_visible + random.randint(-2, 2)))
            oc = (jitter_joints / 19.0) * jitter_conf
            sup = oc < sensitivity
            if sup:
                lbl, pct = "Analysing…", 0
            else:
                lbl = "Standing / Upright" if random.random() > 0.3 else "Active / Dynamic"
                pct = int(min(1.0, oc + random.gauss(0, 0.02)) * 100)
            prog.progress((frame_i + 1) / 60)
            stream_placeholder.markdown(
                f"Frame **{frame_i+1}** · "
                f"Joints: **{jitter_joints}/19** · "
                f"Conf: **{jitter_conf:.2f}** · "
                f"→ **{lbl}** {'`' + str(pct) + '%`' if not sup else ''}",
            )
            time.sleep(0.05)
        stream_placeholder.markdown(f"**Stream complete** — 60 simulated frames processed.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PROJECT STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown(f"<h2 style='color:{CYAN}'>Complete Project Structure</h2>", unsafe_allow_html=True)

    files = [
        ("SelfPoseDemo.xcodeproj/project.pbxproj", "Xcode project file — wires Swift sources, frameworks, Assets.xcassets, LaunchScreen.storyboard, and PrivacyInfo.xcprivacy into build phases.",
         ["PBXBuildFile", "PBXFileReference", "PBXFrameworksBuildPhase", "PBXResourcesBuildPhase", "PBXSourcesBuildPhase", "XCBuildConfiguration"]),

        ("SelfPoseDemo/AppDelegate.swift", "Standard UIApplicationDelegate entry point. No third-party SDKs or analytics are initialised here.",
         ["@main", "UIApplicationDelegate", "UISceneSession"]),

        ("SelfPoseDemo/SceneDelegate.swift", "Creates the UIWindow and installs ViewController as root. No custom configuration needed.",
         ["UIWindowSceneDelegate", "UIWindow", "ViewController()"]),

        ("SelfPoseDemo/ViewController.swift", "Primary 2,200-line file containing the full ARKit + Vision + HUD pipeline.",
         ["ARSCNViewDelegate", "ARSessionDelegate", "AVCaptureVideoDataOutputSampleBufferDelegate",
          "PoseClass", "PoseFeatureVector", "ClassificationResult",
          "consentDialog()", "buildUI()", "startARSession()", "runVisionPipeline()",
          "drawSkeleton()", "mockClassifyPose()", "settingsPanel", "revokeConsent()"]),

        ("SelfPoseDemo/Info.plist", "App metadata, privacy usage descriptions (GDPR/BIPA/CCPA), UIRequiredDeviceCapabilities (arkit + arm64), UILaunchStoryboardName, ITSAppUsesNonExemptEncryption.",
         ["NSCameraUsageDescription", "UIRequiredDeviceCapabilities", "UILaunchStoryboardName",
          "ITSAppUsesNonExemptEncryption", "NSHumanReadableCopyright"]),

        ("SelfPoseDemo/LaunchScreen.storyboard", "Dark splash screen with centred app name, cyan tagline, and privacy footer. Auto Layout only; no images.",
         ["UILabel (name)", "UILabel (tagline)", "UILabel (privacy footer)", "safe-area constraints"]),

        ("SelfPoseDemo/PrivacyInfo.xcprivacy", "Apple Privacy Manifest (required Spring 2024+). Declares zero data collection, zero tracking, zero Required Reason API usage.",
         ["NSPrivacyTracking = false", "NSPrivacyTrackingDomains = []",
          "NSPrivacyCollectedDataTypes = []", "NSPrivacyAccessedAPITypes = []"]),

        ("SelfPoseDemo/Assets.xcassets/AppIcon.appiconset/Contents.json", "Universal 1024×1024 app icon slot. Drop AppIcon.png here before App Store submission.",
         ["universal platform:ios size:1024x1024"]),

        ("SelfPoseDemo/Assets.xcassets/AccentColor.colorset/Contents.json", "Cyan #32D7EC accent — light + dark mode variants matching the skeleton overlay.",
         ["sRGB (0.196, 0.843, 0.925)", "dark-mode variant"]),
    ]

    for fname, desc, keys in files:
        is_new = any(x in fname for x in ["LaunchScreen", "PrivacyInfo", "Assets", "AccentColor"])
        badge  = f"<span class='badge badge-green' style='margin-left:6px'>NEW</span>" if is_new else ""
        with st.expander(f"📄 {fname}{badge}", expanded=False):
            st.markdown(f"<p style='color:{GRAY}'>{desc}</p>", unsafe_allow_html=True)
            st.markdown("**Key symbols / keys**")
            cols = st.columns(min(len(keys), 3))
            for i, k in enumerate(keys):
                cols[i % 3].markdown(f"`{k}`")

    st.divider()
    st.markdown(f"""
    <div style="background:{CARD};border-radius:12px;padding:16px 20px;
                border:1px solid rgba(50,215,236,0.15)">
      <div style="font-size:13px;font-weight:600;color:{WHITE};margin-bottom:8px">
        A12 Bionic Guarantee
      </div>
      <div style="font-size:13px;color:{GRAY};line-height:1.7">
        <code>IPHONEOS_DEPLOYMENT_TARGET = 17.0</code> is set in both
        Debug and Release configurations.  iOS 17's minimum supported device
        is iPhone XR (A12 Bionic), so every install target has the Neural Engine
        required for <code>ARBodyTrackingConfiguration</code> and fast Core ML
        inference.  The code additionally calls
        <code>ARBodyTrackingConfiguration.isSupported</code> at runtime for
        graceful fallback to face tracking on unexpected hardware.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SOURCE FILES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown(f"<h2 style='color:{CYAN}'>Source Files</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{GRAY}'>Key excerpts — open the file in Xcode to see the full source.</p>", unsafe_allow_html=True)

    src_tab = st.selectbox("File", [
        "AppDelegate.swift",
        "SceneDelegate.swift",
        "ViewController.swift — PoseClass & ClassificationResult",
        "ViewController.swift — PoseFeatureVector",
        "ViewController.swift — ViewController (key sections)",
        "Info.plist (key privacy keys)",
        "LaunchScreen.storyboard (excerpt)",
        "PrivacyInfo.xcprivacy",
        "Assets.xcassets/AppIcon.appiconset/Contents.json",
        "Assets.xcassets/AccentColor.colorset/Contents.json",
    ])

    snippets = {
        "AppDelegate.swift": (
            "swift",
            """// AppDelegate.swift — Self-Pose Demo
// No third-party SDK initialisation.
import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        // No analytics / crash reporter by design — on-device-only policy
        return true
    }

    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        UISceneConfiguration(
            name: "Default Configuration",
            sessionRole: connectingSceneSession.role
        )
    }
}"""
        ),
        "SceneDelegate.swift": (
            "swift",
            """// SceneDelegate.swift — Self-Pose Demo
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
        window.makeKeyAndVisible()
        self.window = window
    }
}"""
        ),
        "ViewController.swift — PoseClass & ClassificationResult": (
            "swift",
            """// MARK: - PoseClass
enum PoseClass: String {
    case poseTypeA = "Standing / Upright"
    case poseTypeB = "Active / Dynamic"
    case unknown   = "Analysing…"
}

// MARK: - ClassificationResult
struct ClassificationResult {
    let pose:       PoseClass
    /// 0.0–1.0. Synthetic when isMock == true.
    let confidence: Float
    /// true  → mockClassifyPose (no real ML model loaded)
    /// false → live Core ML model
    let isMock:     Bool

    var displayText: String {
        guard pose != .unknown else { return pose.rawValue }
        let pct = Int(confidence * 100)
        return isMock
            ? "\\(pose.rawValue)  \\(pct)%  [DEMO]"
            : "\\(pose.rawValue)  \\(pct)%"
    }

    static let unknown = ClassificationResult(
        pose: .unknown, confidence: 0, isMock: false)
}"""
        ),
        "ViewController.swift — PoseFeatureVector": (
            "swift",
            """// MARK: - PoseFeatureVector
// Ephemeral per-frame snapshot. Never written to disk.
struct PoseFeatureVector {
    var confidenceThreshold: Float = 0.4

    // Head / neck
    var nose: VNRecognizedPoint?
    var leftEye: VNRecognizedPoint?, rightEye: VNRecognizedPoint?
    var leftEar: VNRecognizedPoint?, rightEar: VNRecognizedPoint?
    var neck: VNRecognizedPoint?
    var root: VNRecognizedPoint?

    // Arms
    var leftShoulder: VNRecognizedPoint?, rightShoulder: VNRecognizedPoint?
    var leftElbow: VNRecognizedPoint?,    rightElbow: VNRecognizedPoint?
    var leftWrist: VNRecognizedPoint?,    rightWrist: VNRecognizedPoint?

    // Legs
    var leftHip: VNRecognizedPoint?,  rightHip: VNRecognizedPoint?
    var leftKnee: VNRecognizedPoint?, rightKnee: VNRecognizedPoint?
    var leftAnkle: VNRecognizedPoint?, rightAnkle: VNRecognizedPoint?

    var validJoints: [(name: String, point: VNRecognizedPoint)] { ... }
    var detectedJointCount: Int { validJoints.count }
    var overallConfidence:  Float { Float(detectedJointCount) / 19.0 }
}"""
        ),
        "ViewController.swift — ViewController (key sections)": (
            "swift",
            """class ViewController: UIViewController {

    // ── UI ──────────────────────────────────────────────────────────
    private var arView: ARSCNView!
    private var optInReminderLabel: UILabel!  // always-visible consent banner
    private var scanningIndicatorLabel: UILabel!
    private var poseLabel: UILabel!
    private var startButton: UIButton!
    private var pauseButton: UIButton!
    private var settingsButton: UIButton!

    // ── Settings Panel ──────────────────────────────────────────────
    private var settingsPanel: UIView!
    private var confidenceSlider: UISlider!
    private var fpsBadgeLabel: UILabel!
    private var settingsPanelBottomConstraint: NSLayoutConstraint!

    // ── Skeleton Layers ──────────────────────────────────────────────
    private let skeletonBoneLayer  = CAShapeLayer()
    private let skeletonJointLayer = CAShapeLayer()

    // ── State ────────────────────────────────────────────────────────
    private var userHasConsented    = false  // GATE — never persisted
    private var isScanningActive    = false
    private var isPaused            = false
    private var isMockClassifierActive = true   // flip when .mlmodel added
    private var anchorAccepted      = false  // single-anchor enforcement

    // ── Queues ───────────────────────────────────────────────────────
    private let visionQueue = DispatchQueue(
        label: "com.selfposedemo.visionQueue", qos: .userInitiated)

    // viewDidLoad → shows consent dialog; no camera/ARKit until consent
    override func viewDidLoad() {
        super.viewDidLoad()
        buildUI()
        showConsentDialog()  // must be first
    }

    // MARK: - Consent
    private func showConsentDialog() { ... }  // full informed-consent alert
    @objc private func revokeConsent()  { ... }  // GDPR Art. 7(3)

    // MARK: - ARKit
    private func startARSession()  { ... }  // ARBodyTracking or face fallback
    private func stopARSession()   { ... }

    // MARK: - Vision Pipeline
    private func runVisionPipeline(pixelBuffer: CVPixelBuffer) { ... }

    // MARK: - Classification
    private func mockClassifyPose(_ fv: PoseFeatureVector)
                -> ClassificationResult { ... }  // [DEMO] synthetic

    // MARK: - Skeleton Drawing
    private func drawSkeleton(_ fv: PoseFeatureVector,
                               in size: CGSize) { ... }
    private func visionToViewPoint(_ pt: VNRecognizedPoint,
                                   in size: CGSize) -> CGPoint { ... }

    // MARK: - ARSCNViewDelegate (3-D label)
    func renderer(_ renderer: any SCNSceneRenderer,
                  didAdd node: SCNNode,
                  for anchor: ARAnchor) { ... }

    // MARK: - ARSessionDelegate (single-anchor enforcement)
    func session(_ session: ARSession,
                 didAdd anchors: [ARAnchor]) {
        for anchor in anchors where anchor is ARBodyAnchor {
            guard !anchorAccepted else {
                session.remove(anchor: anchor)  // refuse second body
                return
            }
            anchorAccepted = true
        }
    }
}"""
        ),
        "Info.plist (key privacy keys)": (
            "xml",
            """<key>NSCameraUsageDescription</key>
<string>Self-Pose Demo uses your camera to analyse YOUR OWN body pose
in real time for personal fitness feedback. All processing runs locally
on this device using Apple's Vision and ARKit frameworks — no video,
images, joint coordinates, or any other data are stored, transmitted,
or shared. The camera is active only while you are scanning and only
after you have explicitly agreed to participate. You may revoke access
at any time in Settings › Privacy &amp; Security › Camera.</string>

<key>UILaunchStoryboardName</key>
<string>LaunchScreen</string>

<key>UIRequiredDeviceCapabilities</key>
<array>
    <string>arkit</string>           <!-- A9+ chip, motion co-processor -->
    <string>arm64</string>           <!-- A12+ via iOS 17 deployment target -->
    <string>front-facing-camera</string>
</array>

<key>ITSAppUsesNonExemptEncryption</key>
<false/>

<key>NSHumanReadableCopyright</key>
<string>© 2025 Self-Pose Demo. Educational and research use only.
Personal, consenting self-analysis only — not for analysing others.</string>"""
        ),
        "LaunchScreen.storyboard (excerpt)": (
            "xml",
            """<!-- LaunchScreen.storyboard — dark splash, no images, pure Auto Layout -->
<!-- App name label — centred with -30pt vertical offset -->
<label text="Self-Pose Demo" textAlignment="center"
    translatesAutoresizingMaskIntoConstraints="NO" id="LS-lbl-name">
  <fontDescription type="boldSystem" pointSize="38"/>
  <color key="textColor" red="1" green="1" blue="1" alpha="1"/>
</label>

<!-- Tagline — cyan -->
<label text="Personal Fitness · On-Device AI" textAlignment="center"
    translatesAutoresizingMaskIntoConstraints="NO" id="LS-lbl-tag">
  <fontDescription type="system" pointSize="18"/>
  <color key="textColor" red="0.196" green="0.843" blue="0.925" alpha="1"/>
</label>

<!-- Privacy footer — pinned to safe-area bottom -->
<!-- GDPR Art. 13 early transparency notice -->
<label text="Requires explicit consent · For personal self-analysis only"
    translatesAutoresizingMaskIntoConstraints="NO" id="LS-lbl-priv">
  <fontDescription type="system" pointSize="13"/>
  <color key="textColor" red="0.55" green="0.55" blue="0.57" alpha="1"/>
</label>

<!-- Background: near-black #0C0C18 — avoids white flash on launch -->
<color key="backgroundColor"
    red="0.047" green="0.047" blue="0.094" alpha="1"/>"""
        ),
        "PrivacyInfo.xcprivacy": (
            "xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<!-- Apple Privacy Manifest — required for App Store since Spring 2024 -->
<plist version="1.0">
<dict>
    <!-- No cross-app/web tracking -->
    <key>NSPrivacyTracking</key>
    <false/>

    <!-- No network requests -->
    <key>NSPrivacyTrackingDomains</key>
    <array/>

    <!-- No data collected or stored.
         Body-pose coords are ephemeral (per CVPixelBuffer lifecycle).
         Only PoseClass enum survives inference — never written to disk. -->
    <key>NSPrivacyCollectedDataTypes</key>
    <array/>

    <!-- No Required Reason APIs used:
         no UserDefaults, no file timestamps, no disk space,
         no system boot time, no active keyboards. -->
    <key>NSPrivacyAccessedAPITypes</key>
    <array/>
</dict>
</plist>"""
        ),
        "Assets.xcassets/AppIcon.appiconset/Contents.json": (
            "json",
            """{
  "images": [
    {
      "idiom":    "universal",
      "platform": "ios",
      "size":     "1024x1024"
    }
  ],
  "info": {
    "author":  "xcode",
    "version": 1
  }
}
/* Drop AppIcon.png (1024×1024 px, no alpha, no rounded corners) here.
   Xcode generates all required sizes automatically.
   Suggested design: dark background #0C0C18,
   white stick figure, cyan (#32D7EC) joint dots. */"""
        ),
        "Assets.xcassets/AccentColor.colorset/Contents.json": (
            "json",
            """{
  "colors": [
    {
      "color": {
        "color-space": "srgb",
        "components": { "alpha":"1", "red":"0.196", "green":"0.843", "blue":"0.925" }
      },
      "idiom": "universal"
    },
    {
      "appearances": [{ "appearance":"luminosity", "value":"dark" }],
      "color": {
        "color-space": "srgb",
        "components": { "alpha":"1", "red":"0.196", "green":"0.843", "blue":"0.925" }
      },
      "idiom": "universal"
    }
  ],
  "info": { "author":"xcode", "version":1 }
}
/* Cyan #32D7EC (R:50 G:214 B:236 in 0–255).
   Used for: skeleton overlay, scanning indicator, accent controls. */"""
        ),
    }

    if src_tab in snippets:
        lang, code = snippets[src_tab]
        st.code(code, language=lang)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — TESTING GUIDE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown(f"<h2 style='color:{CYAN}'>Testing Guide</h2>", unsafe_allow_html=True)

    st.markdown(f"<h3 style='color:{WHITE}'>Simulator</h3>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:{CARD};border-radius:12px;padding:16px 20px;
                border-left:3px solid {AMBER};margin-bottom:16px">
      <span class="badge badge-amber">Limitation</span>
      <span style="font-size:13px;color:{GRAY};margin-left:8px">
        The Xcode Simulator has no real camera and cannot run
        <code>ARBodyTrackingConfiguration</code>.  Use it only for UI flow.
      </span>
    </div>
    """, unsafe_allow_html=True)

    sim_steps = [
        ("Xcode → Product → Destination", "Choose **iPhone 15 Pro (iOS 17.x) Simulator**"),
        ("Build & Run", "Press ⌘R — the app launches and shows the LaunchScreen"),
        ("Consent dialog", "Tap **I Agree** — camera permission appears (simulator grants automatically)"),
        ("Start Scan", "Tap **Start Scan** — scanning indicator pulses, ARKit initialises"),
        ("Pose label", "Shows **Analysing…** because no camera = no Vision observations (expected)"),
        ("Settings panel", "Tap ⚙ → slide sensitivity, observe FPS badge, tap Revoke Consent"),
        ("Pause / Resume", "Tap ⏸ to freeze overlay; ▶ to resume"),
        ("Dark / Light mode", "Simulator → Features → Toggle Appearance — all elements adapt"),
    ]

    for i, (title, detail) in enumerate(sim_steps, 1):
        st.markdown(f"""
        <div style="display:flex;gap:12px;margin-bottom:10px;align-items:flex-start">
          <div style="min-width:26px;height:26px;border-radius:50%;
                      background:rgba(50,215,236,0.18);
                      color:{CYAN};font-size:12px;font-weight:700;
                      display:flex;align-items:center;justify-content:center">
            {i}
          </div>
          <div>
            <div style="font-size:13px;font-weight:600;color:{WHITE}">{title}</div>
            <div style="font-size:12px;color:{GRAY};margin-top:2px">{detail}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"<h3 style='color:{WHITE}'>Physical Device (recommended)</h3>", unsafe_allow_html=True)

    phys_steps = [
        ("Connect", "USB-C cable: iPhone XR, XS, 11, 12, 13, 14, 15 series (all have A12+)"),
        ("Trust", "Trust the Mac on the device; unlock the device"),
        ("Signing", "Xcode → SelfPoseDemo target → Signing & Capabilities → set your Team"),
        ("Destination", "Product → Destination → [Your iPhone]"),
        ("Run", "⌘R — app installs and opens"),
        ("Camera permission", "Tap **I Agree** in the consent dialog, then **Allow** in the system sheet"),
        ("Stand back", "Stand **1–2 m** from the device, ensure your full body is visible"),
        ("Skeleton appears", "Cyan skeleton overlay should appear within 1–2 s"),
        ("Pose label", "Bottom HUD shows the classification + confidence percentage"),
    ]

    for i, (title, detail) in enumerate(phys_steps, 1):
        st.markdown(f"""
        <div style="display:flex;gap:12px;margin-bottom:10px;align-items:flex-start">
          <div style="min-width:26px;height:26px;border-radius:50%;
                      background:rgba(52,199,89,0.18);
                      color:{GREEN};font-size:12px;font-weight:700;
                      display:flex;align-items:center;justify-content:center">
            {i}
          </div>
          <div>
            <div style="font-size:13px;font-weight:600;color:{WHITE}">{title}</div>
            <div style="font-size:12px;color:{GRAY};margin-top:2px">{detail}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"<h3 style='color:{WHITE}'>Debugging Common Issues</h3>", unsafe_allow_html=True)

    issues = [
        ("Skeleton overlay drifts / misaligned",
         "Vision uses normalised y-up coordinates; UIKit uses y-down",
         f"<code>visionToViewPoint</code> applies <code>(1 - y)</code> flip — verify this is present in <code>ViewController.swift</code>",
         "amber"),
        ("AR text floats in wrong 3-D position",
         "ARBodyAnchor joint transforms are in the anchor's local space",
         "The label node is a child of the anchor's SCNNode — parent transform applies automatically. No fix needed unless re-parented.",
         "amber"),
        ("Low classification accuracy / always 'Analysing…'",
         "Sensitivity threshold too high, or too few joints detected",
         "Open Settings → slide toward Balanced. Ensure even front lighting. Stay 1–2 m from device.",
         "amber"),
        ("[DEMO] badge never disappears",
         "isMockClassifierActive = true (no real .mlmodel loaded)",
         "Add a trained PoseClassifier.mlmodel and set isMockClassifierActive = false in ViewController.swift",
         "cyan"),
        ("App crashes immediately on device",
         "Device below A12 or iOS below 17",
         "UIRequiredDeviceCapabilities prevents install, but test with ARBodyTrackingConfiguration.isSupported runtime check.",
         "red"),
        ("cameraDidChangeTrackingState: .limited",
         "Insufficient ambient light or very fast motion",
         "Move to a brighter area. Hold device still for 2 s during initialisation.",
         "amber"),
        ("Second person's skeleton appears",
         "Only one ARBodyAnchor should be accepted",
         "session(_:didAdd:) checks anchorAccepted — if a second ARBodyAnchor arrives it is immediately removed.",
         "red"),
        ("Launch screen appears white for a moment",
         "Storyboard backgroundColor not dark enough",
         "LaunchScreen.storyboard sets background to #0C0C18 — rebuild DerivedData if white flash persists.",
         "amber"),
    ]

    for symptom, cause, fix, color in issues:
        st.markdown(f"""
        <div style="background:{CARD};border-radius:10px;padding:14px 16px;
                    margin-bottom:10px;border-left:3px solid var(--{color}, {CYAN})">
          <div style="font-size:13px;font-weight:600;color:{WHITE}">{symptom}</div>
          <div style="font-size:12px;color:{GRAY};margin-top:4px">
            <b>Cause:</b> {cause}
          </div>
          <div style="font-size:12px;color:{GRAY};margin-top:2px">
            <b>Fix:</b> {fix}
          </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ETHICAL NOTES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown(f"<h2 style='color:{CYAN}'>Ethical Use Notice</h2>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:rgba(50,215,236,0.06);border:1px solid rgba(50,215,236,0.25);
                border-radius:14px;padding:20px 24px;margin-bottom:20px">
      <div style="font-size:14px;font-weight:700;color:{CYAN};margin-bottom:8px">
        ⚖ This app is for personal, consenting self-analysis only
      </div>
      <div style="font-size:13px;color:{GRAY};line-height:1.8">
        Self-Pose Demo is designed and architected so that body-pose analysis
        <strong style="color:{WHITE}">cannot silently occur</strong> — every code path
        is gated behind <code>userHasConsented</code>, a runtime-only boolean that
        resets on every launch.  The consenting user must be the only person
        in the camera's field of view at the time they tap <em>I Agree</em>.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Legal compliance grid ─────────────────────────────────────────────
    laws = [
        ("🇺🇸 BIPA", "Illinois 740 ILCS 14/15(b)",
         "Written informed notice before collecting biometric data. Satisfied by: consent dialog with explicit 'I Agree' tap; privacy description in NSCameraUsageDescription; privacy footer on launch screen."),
        ("🇪🇺 GDPR", "EU 2016/679 Art. 5, 6(1)(a), 7(3), 9",
         "Lawful basis = explicit consent (Art. 6(1)(a)). Art. 9 special category (biometric). Right to withdraw (Art. 7(3)) = Revoke Consent button. Art. 13 transparency = launch screen + consent dialog + Info.plist string."),
        ("🇺🇸 CCPA", "California Civil Code §1798.100",
         "Right to know before collection. Satisfied by consent dialog and NSCameraUsageDescription. No 'selling' or 'sharing' of biometric data — all processing is on-device ephemeral."),
        ("🍎 App Store", "Review Guideline §5.1.1",
         "NSCameraUsageDescription is honest, specific, non-coercive. No network requests. Privacy manifest (PrivacyInfo.xcprivacy) declares zero data collection. ITSAppUsesNonExemptEncryption = false for BIS compliance."),
    ]

    for law, ref, detail in laws:
        st.markdown(f"""
        <div style="background:{CARD};border-radius:12px;padding:16px 20px;
                    margin-bottom:12px;border:1px solid rgba(255,255,255,0.07)">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
            <span style="font-size:18px">{law.split()[0]}</span>
            <span style="font-size:14px;font-weight:700;color:{WHITE}">{law[2:]}</span>
            <span style="font-size:11px;color:{GRAY}">{ref}</span>
          </div>
          <div style="font-size:12px;color:{GRAY};line-height:1.7">{detail}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Architectural safeguards ──────────────────────────────────────────
    st.markdown(f"<h3 style='color:{WHITE}'>Architectural Privacy Safeguards</h3>", unsafe_allow_html=True)

    safeguards = [
        ("Explicit Opt-In Gate", f"<code>userHasConsented = false</code> on launch. No camera, ARKit, or Vision work occurs until the user taps <em>I Agree</em>. The flag is never persisted — re-launching requires re-consent.", GREEN),
        ("Single-Anchor Enforcement", "If ARKit adds a second <code>ARBodyAnchor</code>, the app calls <code>session.remove(anchor:)</code> immediately. Only the first, consenting user's skeleton is ever tracked.", CYAN),
        ("Single-Observer Processing", "If Vision detects more than one person in a frame, only the first observation is used. All others are silently discarded with no processing.", CYAN),
        ("No Persistence", "No frames, images, joint coordinates, feature vectors, or classification results are ever written to disk, UserDefaults, iCloud, or any other store.", GREEN),
        ("No Network", "No pixel data, pose data, or any derivative is transmitted. ATS is at strict default. PrivacyInfo.xcprivacy declares zero tracking domains.", GREEN),
        ("Ephemeral CVPixelBuffers", "Each camera frame is consumed inline by Vision and released with the ARFrame. Only a <code>PoseClass</code> enum value (2 bytes) survives past inference.", CYAN),
        ("Revoke Consent (GDPR Art. 7(3))", "The Settings panel always offers a Revoke Consent button. Tapping it stops all processing immediately and resets <code>userHasConsented = false</code>.", AMBER),
        ("[DEMO] Badge", "Mock confidence values are clearly marked <code>[DEMO]</code> in both the 2-D HUD label and the 3-D AR text node, preventing synthetic data from being mistaken for real AI measurements.", AMBER),
    ]

    for title, detail, color in safeguards:
        st.markdown(f"""
        <div style="display:flex;gap:12px;margin-bottom:12px;align-items:flex-start">
          <div style="min-width:8px;height:8px;border-radius:50%;
                      background:{color};margin-top:6px;flex-shrink:0"></div>
          <div>
            <div style="font-size:13px;font-weight:600;color:{WHITE}">{title}</div>
            <div style="font-size:12px;color:{GRAY};margin-top:2px;line-height:1.6">{detail}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.markdown(f"""
    <div style="background:rgba(255,59,48,0.07);border:1px solid rgba(255,59,48,0.2);
                border-radius:12px;padding:16px 20px">
      <div style="font-size:13px;font-weight:700;color:{RED};margin-bottom:8px">
        Prohibited Uses
      </div>
      <ul style="font-size:12px;color:{GRAY};line-height:2;margin:0;padding-left:20px">
        <li>Analysing any person who has not explicitly consented</li>
        <li>Recording, storing, or transmitting body-pose data</li>
        <li>Deploying in a public space where bystanders could be captured</li>
        <li>Using mock [DEMO] confidence values as real AI measurements in research, clinical, or commercial contexts</li>
        <li>Any clinical diagnosis, injury-risk assessment, or safety-critical decision</li>
        <li>Discrimination based on detected body pose or movement pattern</li>
      </ul>
    </div>
    """, unsafe_allow_html=True)
