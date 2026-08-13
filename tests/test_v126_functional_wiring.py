from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "dashboard/js/noorbrain-mobile-shell-v126.js").read_text()
MIC = (ROOT / "dashboard/js/halo-mic-final-fix.js").read_text()
MOBILE = (ROOT / "dashboard/mobile/index.html").read_text()


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
