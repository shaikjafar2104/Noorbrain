from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "dashboard/js/noorbrain-mobile-shell-v126.js").read_text()
MIC = (ROOT / "dashboard/js/halo-mic-final-fix.js").read_text()
MOBILE = (ROOT / "dashboard/mobile/index.html").read_text()
AUTOMATION = (ROOT / "dashboard/js/automation-center-v12.js").read_text()
RULES = (ROOT / "dashboard/js/mobile-rules-v12.js").read_text()
SHELL_CSS = (ROOT / "dashboard/css/noorbrain-mobile-shell-v126.css").read_text()


def test_halo_uses_real_conversation_and_transcription_apis() -> None:
    assert '"/api/halo-conversation/chat"' in SHELL
    assert 'const VOICE_API = "/api/halo-voice"' in MIC
    assert "NoorBrainMobile126.sendHalo(clean)" in MIC
    assert "toggle," in MIC
    assert "Promise.resolve(mic.toggle())" in SHELL


def test_native_microphone_and_tts_bridge_are_wired_to_v126() -> None:
    assert 'type:"noorbrain-native-record-toggle"' in SHELL
    assert 'type:"noorbrain-native-speak"' in SHELL
    assert 'window.NoorBrainMobile126?.sendHalo' in MOBILE
    assert 'document.getElementById("nb126HaloInput")' in MOBILE
    assert '"speechSynthesis" in window' in SHELL


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
