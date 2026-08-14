from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOBILE = (ROOT / "dashboard/js/noorbrain-mobile-shell-v126.js").read_text()
DESKTOP = (ROOT / "dashboard/js/web-clean-navigation-v12.js").read_text()
MEDIA = (ROOT / "dashboard/js/media-library.js").read_text()
MIC = (ROOT / "dashboard/js/halo-mic-final-fix.js").read_text()
UNIFIED = (ROOT / "dashboard/js/unified-product-ui.js").read_text()
WORKER = (ROOT / "dashboard/pwa/sw.js").read_text()


def test_mobile_management_pages_use_real_routes() -> None:
    required = {
        "/api/devices",
        "/api/mobile-v2/cameras",
        "/api/vision-zones/zones",
        "/api/media",
        "/api/islamic-intelligence-v12/rules",
        "/api/prayer-intelligence/settings",
        "/api/mobile-notifications",
        "/api/family-intelligence-v11",
        "/api/plugin-platform-v13",
        "/api/habit-learning",
    }
    assert all(route in MOBILE for route in required)
    for action in ("device", "zone", "media", "family", "plugin"):
        assert f"data-v126-{action}-delete" in MOBILE
    assert 'data-v126-islamic-rule-action="delete"' in MOBILE
    assert 'action:"family"' in MOBILE
    assert 'action:"plugins"' in MOBILE
    assert 'action:"habits"' in MOBILE
    assert 'action:"notifications"' in MOBILE


def test_desktop_product_router_isolates_dedicated_pages() -> None:
    for page in (
        "devices",
        "habit-learning",
        "prayer-intelligence",
        "islamic-rules",
        "family",
        "plugins",
        "mobile-notifications",
    ):
        assert f'["{page}",' in DESKTOP
    assert "isolateRoutedContent();" in DESKTOP
    assert 'child.classList.contains("page")' in DESKTOP
    assert 'window.NoorAutomationCenterV12.open(automationTabs[page])' in DESKTOP
    assert "Desktop uses routed product pages" in UNIFIED


def test_media_edit_and_preview_contract() -> None:
    assert 'class MediaUpdateRequest(BaseModel)' in (
        ROOT / "services/media_library/routes.py"
    ).read_text()
    assert '@api_router.patch("/{media_id}")' in (
        ROOT / "services/media_library/routes.py"
    ).read_text()
    assert "async function saveEditMedia" in MEDIA
    assert 'method: "PATCH"' in MEDIA
    assert "new Audio(" in MEDIA
    assert "islamic_type" in MEDIA


def test_halo_supports_apk_relay_and_direct_capacitor_with_recovery() -> None:
    for event in (
        "MIC_REQUEST",
        "NATIVE_START_SENT",
        "NATIVE_START_ACK",
        "RECORDING_STARTED",
        "STOP_REQUEST",
        "NATIVE_AUDIO_RECEIVED",
        "TRANSCRIBE_START",
        "TRANSCRIBE_RESULT",
        "CHAT_START",
        "CHAT_RESULT",
        "TTS_SENT",
        "VOICE_IDLE",
        "VOICE_ERROR",
    ):
        assert event in MIC
    assert 'transport: "parent-relay"' in MIC
    assert 'transport: "capacitor-direct"' in MIC
    assert "NATIVE_START_TIMEOUT_MS = 15000" in MIC
    assert "PROCESSING_TIMEOUT_MS = 45000" in MIC


def test_pwa_cache_references_audio_intercom_finish_assets() -> None:
    assert 'CACHE_NAME = "noorbrain-v126-audio-intercom-finish-1"' in WORKER
    assert "v=20260813-audio-intercom" in WORKER
