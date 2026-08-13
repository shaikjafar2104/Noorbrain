from pathlib import Path
import json
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "dashboard/js/noorbrain-mobile-shell-v126.js").read_text()
MIC = (ROOT / "dashboard/js/halo-mic-final-fix.js").read_text()
MOBILE = (ROOT / "dashboard/mobile/index.html").read_text()
AUTOMATION = (ROOT / "dashboard/js/automation-center-v12.js").read_text()
RULES = (ROOT / "dashboard/js/mobile-rules-v12.js").read_text()
SHELL_CSS = (ROOT / "dashboard/css/noorbrain-mobile-shell-v126.css").read_text()
SETTINGS = (ROOT / "dashboard/js/mobile-noor-settings-v11.js").read_text()
PRODUCT_DASHBOARD = (ROOT / "dashboard/js/product-dashboard-v12.js").read_text()
CONTROL_MAP = json.loads((ROOT / "tests/v126_functional_map.json").read_text())
with zipfile.ZipFile(ROOT / "NoorBrainMobile-PERMANENT-MIC-FIX.apk") as archive:
    APK_APP = archive.read("assets/public/app.js").decode("utf-8")


def test_halo_uses_real_conversation_and_transcription_apis() -> None:
    assert '"/api/halo-conversation/chat"' in SHELL
    assert 'const VOICE_API = "/api/halo-voice"' in MIC
    assert "NoorBrainMobile126.sendHalo(clean)" in MIC
    assert "toggle," in MIC
    assert "Promise.resolve(mic.toggle(" in SHELL


def test_native_microphone_and_webview_tts_fallback_are_wired_to_v126() -> None:
    assert 'type: "noorbrain-native-record-toggle"' in MIC
    assert 'type: "noorbrain-native-speak"' not in APK_APP
    assert 'window.NoorBrainMobile126.sendHalo(clean)' in MIC
    assert '"speechSynthesis" in window' in SHELL


def test_halo_voice_has_one_guarded_state_machine_and_recovery_timers() -> None:
    assert 'state.mode !== "idle"' in MIC
    assert 'RECORDING_TIMEOUT_MS = 12000' in MIC
    assert 'PROCESSING_TIMEOUT_MS = 45000' in MIC
    assert 'stopNative("automatic timeout")' in MIC
    assert 'state.nativeTranscriptHandled' in MIC
    assert 'window.addEventListener("message", handleNativeMessage)' in MIC
    assert 'window.addEventListener("message", async event =>' not in MOBILE


def test_halo_tts_is_single_webview_fallback_and_failure_safe() -> None:
    assert 'window.speechSynthesis.cancel()' in SHELL
    assert 'window.speechSynthesis.speak(utterance)' in SHELL
    assert 'V126_HALO_TTS_ERROR' in SHELL
    assert 'type:"noorbrain-native-speak"' not in SHELL
    assert 'type: "noorbrain-native-speak"' not in APK_APP


def test_product_dashboard_uses_registered_activity_route() -> None:
    assert 'json("/api/activity/activities?limit=20")' in PRODUCT_DASHBOARD
    assert 'json("/api/activity/events")' not in PRODUCT_DASHBOARD


def test_v126_visible_features_use_registered_real_routes() -> None:
    required = {
        '"/api/activity/activities?limit=20"',
        '"/api/vision-zones/zones"',
        '"/api/devices"',
        '"/api/automation/scenes"',
        '"/api/automation/routines"',
        '"/api/smart-automation/rules"',
        '"/api/prayer-intelligence/times"',
        '"/api/media"',
        '"/reminder-rules"',
        '"/api/mobile-notifications"',
    }
    assert required <= set(SHELL.splitlines()) or all(item in SHELL for item in required)


def test_device_and_islamic_rule_payloads_match_backend_models() -> None:
    assert 'device_type:type||"other"' in SHELL
    assert 'method:"PATCH"' in SHELL
    assert "body:JSON.stringify({enabled})" in SHELL


def test_protected_native_pages_and_pre_a42_handlers_remain_active() -> None:
    assert "openV126Camera();" in SHELL
    assert "openV126Activity();" in SHELL
    assert "openV126Zones();" in SHELL
    assert "openV126Devices();" in SHELL
    assert "openV126Scenes();" in SHELL
    assert "openV126Routines();" in SHELL
    assert 'action:"islamic-calendar"' not in SHELL


def test_v126_opens_existing_product_automation_and_reminder_surfaces() -> None:
    assert 'window.NoorAutomationCenterV12.open("smart")' in SHELL
    assert 'window.NoorAutomationCenterV12.open("scenes")' in SHELL
    assert 'window.NoorAutomationCenterV12.open("routines")' in SHELL
    assert "window.NoorMobileRulesV12.open()" in SHELL
    assert ":not(#nbAutomationCenterV12)" in SHELL_CSS
    assert ":not(#nbRulesV12)" in SHELL_CSS


def test_product_controls_use_real_mutation_contracts() -> None:
    assert 'method: editing ? "PUT" : "POST"' in RULES
    assert 'method: "PATCH"' in RULES
    assert "body: JSON.stringify({enabled:!rule.enabled})" in RULES
    assert 'if (target === "new")' in RULES
    assert 'item?.id || "new"' in AUTOMATION
    assert 'data-action="toggle"' in AUTOMATION
    assert "executionFailure(result,state.tab)" in AUTOMATION
    assert "Add a HALO speech action before saving this rule." in AUTOMATION


def test_every_mapped_v126_control_has_real_wiring_and_ui_result() -> None:
    controls = CONTROL_MAP["controls"]
    assert len(controls) >= 35
    assert {item["page"] for item in controls} == {
        "global", "bottom-nav", "home", "automation", "halo", "islamic", "more"
    }
    for item in controls:
        assert item["control"]
        assert item["event"] in SHELL
        action_marker = item["action"].split(".")[-1]
        assert (
            item["action"] in SHELL
            or item["action"] in MIC
            or action_marker in SHELL
            or action_marker in MIC
        )
        assert item["result"]
        if item["backend"]:
            for backend in item["backend"].split(";"):
                assert (ROOT / backend.strip()).is_file()
        if item["api"]:
            for raw_path in item["api"].split(";"):
                path = raw_path.strip().split()[-1]
                marker = path.split("/{", 1)[0]
                assert (
                    marker in SHELL
                    or marker in MIC
                    or marker in AUTOMATION
                    or marker in RULES
                    or marker in SETTINGS
                    or marker in APK_APP
                )
