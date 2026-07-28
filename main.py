"""
============================================================
Project : NoorBrain
Module  : Main Application
Version : 1.0.0
============================================================
"""

from typing import List
from pathlib import Path
import threading
import time

import cv2
from ai.halo import halo
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

from shared.logger import logger
from shared.config_manager import load_config

from services.camera_client import camera_client
from services.vision_engine import vision_engine
from services.zone_engine import zone_engine
from services.event_engine import event_engine
from services.reminder_rules.routes import router as reminder_rules_router
from services.habit_engine.routes import router as habit_routes
from shared.database import database
from services.system_core.routes import router as system_core_router
from services.system_core.validation import startup_validator
from services.system_core.migrations import migration_manager


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
config = load_config()


# ---------------------------------------------------------
# FastAPI
# ---------------------------------------------------------
from services.media_library.routes import router as media_library_router, api_router as media_library_api_router
from services.dashboard.routes import router as dashboard_router
from services.person_ai.routes import router as person_router
from services.ai_memory.routes import router as ai_memory_router
from services.learning.routes import router as learning_router
from services.system_operations.routes import router as operations_router, configure as configure_operations, start_watchdog, stop_watchdog
from services.qa.routes import router as qa_router
from services.release.routes import router as release_router
from services.scene_intelligence.routes import router as scene_intelligence_router
from services.decision_engine.routes import router as decision_engine_router
from services.ai_assistant.routes import router as ai_assistant_router
from services.sprint7_half1.routes import router as sprint7_half1_router
from services.prediction.routes import router as prediction_router
from services.anomaly.routes import router as anomaly_router
from services.household.routes import router as household_router
from services.reports.routes import router as reports_router
from services.voice_ai.routes import router as voice_ai_router
app = FastAPI(
    title="NoorBrain",
    version="1.0.0"
)
app.include_router(voice_ai_router)

# Sprint 2: Media Library API
app.include_router(media_library_router)
app.include_router(media_library_api_router)


app.include_router(reminder_rules_router)
app.include_router(habit_routes)
app.include_router(dashboard_router)
app.include_router(person_router)
app.include_router(learning_router)
app.include_router(operations_router)
app.include_router(qa_router)
app.include_router(release_router)
app.include_router(sprint7_half1_router)

PROJECT_ROOT = Path(__file__).resolve().parent
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
app.mount(
    "/dashboard-static",
    StaticFiles(directory=str(DASHBOARD_DIR)),
    name="dashboard-static"
)


configure_operations(camera_client, vision_engine)

# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    message: str


class ZoneModel(BaseModel):
    name: str
    x1: int
    y1: int
    x2: int
    y2: int


class VisionSettings(BaseModel):
    confidence: float


# ---------------------------------------------------------
# Startup
# ---------------------------------------------------------
@app.on_event("startup")
def startup():
    migration_result = migration_manager.apply_pending()
    validation_result = startup_validator.run()
    logger.info(f"Migration status: {migration_result}")
    logger.info(f"Startup validation: {validation_result['status']}")
    logger.info("=" * 60)
    logger.info("Starting NoorBrain")
    logger.info("=" * 60)
    
    camera_client.start()
    vision_engine.start()
    logger.info("Vision Snapshot After Start")
    logger.info(vision_engine.snapshot())
    
    start_watchdog()
    logger.info("NoorBrain Ready")


# ---------------------------------------------------------
# Shutdown
# ---------------------------------------------------------
@app.on_event("shutdown")
def shutdown():
    logger.info("=" * 60)
    logger.info("Stopping NoorBrain")
    logger.info("=" * 60)
    
    stop_watchdog()
    vision_engine.stop()
    camera_client.stop()
    
    logger.info("Shutdown Complete")


# ---------------------------------------------------------
# Home
# ---------------------------------------------------------
@app.get("/")
def home():
    return HTMLResponse("""
    <html>
    <head>
        <title>NoorBrain</title>
        <style>
        body{
            background:#101114;
            color:white;
            text-align:center;
            font-family:Arial;
        }
        img{
            width:900px;
            border-radius:12px;
            border:2px solid #00d084;
        }
        a{
            color:#00d084;
            margin:15px;
            text-decoration:none;
            font-weight:bold;
        }
        </style>
    </head>
    <body>
        <h1>NoorBrain</h1>
        <img src="/vision_feed">
        <br><br>
        <a href="/detections">Detections</a>
        <a href="/zones">Zones</a>
        <a href="/camera">Camera</a>
        <a href="/dashboard/zones">Dashboard</a>
    </body>
    </html>
    """)


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "camera": camera_client.snapshot(),
        "vision": vision_engine.snapshot()
    }


# ---------------------------------------------------------
# Camera
# ---------------------------------------------------------
@app.get("/camera")
def camera():
    return camera_client.snapshot()


@app.get("/camera/stats")
def camera_stats():
    return {
        "camera": camera_client.snapshot(),
        "vision": vision_engine.snapshot()
    }


# ---------------------------------------------------------
# Detections
# ---------------------------------------------------------
@app.get("/detections")
def detections():
    people = vision_engine.get_detections()
    return {
        "count": len(people),
        "people": people
    }


# ---------------------------------------------------------
# Zones
# ---------------------------------------------------------
@app.get("/zones")
def zones():
    all_zones = zone_engine.get_all_zones()
    return {
        "count": len(all_zones),
        "zones": all_zones
    }


# ---------------------------------------------------------
# Save Zones
# ---------------------------------------------------------
@app.post("/zones/save")
def save_zones(zones: List[ZoneModel]):
    zone_engine.save_zones([
        zone.model_dump()
        for zone in zones
    ])
    return {
        "status": "saved",
        "count": len(zones)
    }


# ---------------------------------------------------------
# Frame Size
# ---------------------------------------------------------
@app.get("/frame_size")
def frame_size():
    frame = vision_engine.get_frame()
    if frame is None:
        return {
            "width": 1280,
            "height": 720
        }
    height, width = frame.shape[:2]
    return {
        "width": width,
        "height": height
    }


# ---------------------------------------------------------
# Shared MJPEG Encoder
# ---------------------------------------------------------
_jpeg_lock = threading.Lock()
_jpeg_bytes = None
_jpeg_time = 0.0
_jpeg_interval = 1.0 / 8.0


def get_encoded_frame():
    global _jpeg_bytes, _jpeg_time

    now = time.monotonic()

    with _jpeg_lock:
        if (
            _jpeg_bytes is not None
            and now - _jpeg_time < _jpeg_interval
        ):
            return _jpeg_bytes

        frame = vision_engine.get_frame()

        # Keep camera visible while vision is starting or stopped.
        if frame is None:
            frame = camera_client.get_frame()

        if frame is None:
            return None

        success, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 75]
        )

        if not success:
            return None

        _jpeg_bytes = buffer.tobytes()
        _jpeg_time = now

        return _jpeg_bytes


def generate():
    while True:
        jpg = get_encoded_frame()

        if jpg is None:
            time.sleep(0.10)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Cache-Control: no-cache, no-store, must-revalidate\r\n"
            b"Pragma: no-cache\r\n\r\n"
            + jpg
            + b"\r\n"
        )

        # Each browser connection is limited to 8 FPS.
        time.sleep(_jpeg_interval)


# ---------------------------------------------------------
# Vision Feed
# ---------------------------------------------------------
@app.get("/vision_feed")
def vision_feed():
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# ---------------------------------------------------------
# Halo Chat
# ---------------------------------------------------------
@app.post("/halo")
def halo_chat(request: ChatRequest):
    reply = halo.ask(request.message)
    return {
        "success": True,
        "reply": reply
    }




# ---------------------------------------------------------
# NoorBrain AI Studio
# ---------------------------------------------------------
@app.get("/studio", include_in_schema=False)
def studio():
    return FileResponse(DASHBOARD_DIR / "index.html")


# ---------------------------------------------------------
# Event API
# ---------------------------------------------------------
@app.get("/events")
def events(limit: int = 50):
    limit = max(1, min(limit, 500))
    rows = database.recent_events(limit)
    return {
        "count": len(rows),
        "events": [
            {
                "time": row[0],
                "event": row[1],
                "zone": row[2],
                "source": row[3],
                "destination": row[4]
            }
            for row in rows
        ]
    }


# ---------------------------------------------------------
# Runtime Controls
# ---------------------------------------------------------
@app.post("/control/vision/start")
def control_vision_start():
    vision_engine.start()
    return {"success": True, "message": "Vision engine started."}


@app.post("/control/vision/stop")
def control_vision_stop():
    vision_engine.stop()
    return {"success": True, "message": "Vision engine stopped."}


@app.post("/control/vision/restart")
def control_vision_restart():
    def restart_worker():
        vision_engine.stop()
        time.sleep(1)
        vision_engine.start()

    threading.Thread(target=restart_worker, daemon=True).start()
    return {"success": True, "message": "Vision engine is restarting."}


@app.post("/control/camera/reconnect")
def control_camera_reconnect():
    def reconnect_worker():
        camera_client.stop()
        time.sleep(1)
        camera_client.start()

    threading.Thread(target=reconnect_worker, daemon=True).start()
    return {"success": True, "message": "Camera client is reconnecting."}


# ---------------------------------------------------------
# Settings API
# ---------------------------------------------------------
@app.get("/settings/vision")
def get_vision_settings():
    return {
        "model": vision_engine.model_path,
        "confidence": vision_engine.confidence
    }


@app.post("/settings/vision")
def save_vision_settings(settings: VisionSettings):
    if not 0.05 <= settings.confidence <= 0.95:
        return {
            "success": False,
            "message": "Confidence must be between 0.05 and 0.95."
        }

    vision_engine.confidence = float(settings.confidence)
    return {
        "success": True,
        "message": f"Vision confidence set to {vision_engine.confidence:.2f}.",
        "confidence": vision_engine.confidence
    }


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
@app.get("/dashboard/zones")
def dashboard_zones():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Noor AI Studio</title>
<style>
body{
    margin:0;
    background:#101114;
    color:white;
    font-family:Arial;
}
header{
    background:#18191d;
    padding:18px;
    text-align:center;
    font-size:28px;
    font-weight:bold;
}
#container{
    width:940px;
    margin:30px auto;
}
#stage{
    position:relative;
}
#video{
    width:900px;
    display:block;
    border-radius:12px;
    border:2px solid #00d084;
}
#overlay{
    position:absolute;
    left:0;
    top:0;
    cursor:crosshair;
}
#toolbar{
    margin-top:18px;
}
button{
    background:#00d084;
    border:none;
    color:#111;
    padding:10px 18px;
    border-radius:8px;
    cursor:pointer;
    font-weight:bold;
    margin-right:10px;
}
button:hover{
    opacity:.9;
}
button.danger{
    background:#ff4d4d;
    color:white;
}
#zoneList{
    margin-top:20px;
}
.zone{
    background:#1c1d22;
    padding:12px;
    border-radius:8px;
    margin-top:8px;
    display:flex;
    justify-content:space-between;
    align-items:center;
}
</style>
</head>
<body>
<header>Noor AI Studio</header>
<div id="container">
    <div id="stage">
        <img id="video" src="/vision_feed">
        <canvas id="overlay"></canvas>
    </div>
    <div id="toolbar">
        <button onclick="saveZones()">Save Zones</button>
        <button class="danger" onclick="clearZones()">Clear</button>
    </div>
    <div id="zoneList"></div>
</div>

<script>
// ============================================================
// VARIABLES
// ============================================================
let zones = [];
let drawing = false;
let startX = 0;
let startY = 0;
let temp = null;
let actualWidth = 1280;
let actualHeight = 720;
const displayWidth = 900;
let displayHeight = 506;

const video = document.getElementById("video");
const canvas = document.getElementById("overlay");
const ctx = canvas.getContext("2d");

// ============================================================
// CANVAS SETUP
// ============================================================
async function setupCanvas() {
    const response = await fetch("/frame_size");
    const size = await response.json();
    actualWidth = size.width;
    actualHeight = size.height;
    displayHeight = Math.round(
        displayWidth *
        actualHeight /
        actualWidth
    );
    canvas.width = displayWidth;
    canvas.height = displayHeight;
    canvas.style.width = displayWidth + "px";
    canvas.style.height = displayHeight + "px";
}

// ============================================================
// COORDINATE CONVERSION
// ============================================================
function toActual(value, scale) {
    return Math.round(value * scale);
}

function toDisplay(value, scale) {
    return Math.round(value / scale);
}

// ============================================================
// DRAWING
// ============================================================
function redraw() {
    ctx.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );
    for (const zone of zones) {
        drawZone(zone);
    }
    if (temp) {
        drawZone(temp, "#00d084");
    }
}

function drawZone(zone, color = "#ffb400") {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(
        zone.x1,
        zone.y1,
        zone.x2 - zone.x1,
        zone.y2 - zone.y1
    );
    ctx.fillStyle = color;
    ctx.font = "16px Arial";
    ctx.fillText(
        zone.name,
        zone.x1 + 6,
        zone.y1 + 20
    );
}

// ============================================================
// MOUSE EVENTS
// ============================================================
canvas.onmousedown = function(e) {
    const rect = canvas.getBoundingClientRect();
    drawing = true;
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
};

canvas.onmousemove = function(e) {
    if (!drawing) {
        return;
    }
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    temp = {
        name: "",
        x1: Math.min(startX, x),
        y1: Math.min(startY, y),
        x2: Math.max(startX, x),
        y2: Math.max(startY, y)
    };
    redraw();
};

canvas.onmouseup = function() {
    if (!drawing) {
        return;
    }
    drawing = false;
    if (!temp) {
        return;
    }
    const name = prompt("Zone Name");
    if (name) {
        temp.name = name;
        zones.push(temp);
    }
    temp = null;
    redraw();
    renderZoneList();
};

// ============================================================
// ZONE LIST
// ============================================================
function renderZoneList() {
    const container = document.getElementById("zoneList");
    container.innerHTML = "";
    zones.forEach((zone, index) => {
        const item = document.createElement("div");
        item.className = "zone";
        item.innerHTML = `
            <span>${zone.name}</span>
            <button class="danger"
                    onclick="deleteZone(${index})">
                Delete
            </button>
        `;
        container.appendChild(item);
    });
}

// ============================================================
// DELETE
// ============================================================
function deleteZone(index) {
    zones.splice(index, 1);
    redraw();
    renderZoneList();
}

// ============================================================
// CLEAR
// ============================================================
function clearZones() {
    if (!confirm("Delete all zones?")) {
        return;
    }
    zones = [];
    redraw();
    renderZoneList();
}

// ============================================================
// SAVE
// ============================================================
async function saveZones() {
    const sx = actualWidth / displayWidth;
    const sy = actualHeight / displayHeight;
    const payload = zones.map(z => ({
        name: z.name,
        x1: Math.round(z.x1 * sx),
        y1: Math.round(z.y1 * sy),
        x2: Math.round(z.x2 * sx),
        y2: Math.round(z.y2 * sy)
    }));
    const response = await fetch(
        "/zones/save",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        }
    );
    const result = await response.json();
    alert(
        "Saved "
        + result.count +
        " zones."
    );
}

// ============================================================
// LOAD EXISTING ZONES
// ============================================================
async function loadZones() {
    const response = await fetch("/zones");
    const result = await response.json();
    const sx = actualWidth / displayWidth;
    const sy = actualHeight / displayHeight;
    zones = result.zones.map(z => ({
        name: z.name,
        x1: Math.round(z.x1 / sx),
        y1: Math.round(z.y1 / sy),
        x2: Math.round(z.x2 / sx),
        y2: Math.round(z.y2 / sy)
    }));
    redraw();
    renderZoneList();
}

// ============================================================
// STARTUP
// ============================================================
window.onload = async () => {
    await setupCanvas();
    await loadZones();
    redraw();
};
</script>
</body>
</html>
    """)

# Sprint 7.1 AI Memory Engine
app.include_router(ai_memory_router)
app.include_router(system_core_router)
app.include_router(ai_assistant_router)

# Sprint 8.1 Scene Intelligence
app.include_router(scene_intelligence_router)
# Sprint 8.2 Decision Engine
app.include_router(decision_engine_router)

app.include_router(prediction_router)
app.include_router(anomaly_router)
app.include_router(household_router)

app.include_router(reports_router)


# NOORBRAIN HALO BRIDGE
from services.halo_bridge.routes import router as halo_bridge_router
app.include_router(halo_bridge_router)

# NOORBRAIN SPRINT 11 PACK 1 HALF 2
from services.automation.routes import router as automation_devices_router
app.include_router(automation_devices_router)

# SPRINT 11 DEVICES DASHBOARD ASSETS
from services.automation.dashboard_assets import router as devices_dashboard_assets_router
app.include_router(devices_dashboard_assets_router)

# NOORBRAIN SPRINT 11 PACKS 3-4
from services.automation.integration_routes import router as automation_integration_router
app.include_router(automation_integration_router)

# NOORBRAIN SPRINT 11 PACK 5 HALF 1
from services.automation.pack5_routes import router as automation_pack5_router
app.include_router(automation_pack5_router)

# NOORBRAIN SPRINT 11 PACK 5 HALF 2A CHUNKS 1-2
from services.automation.backup_routes import router as automation_backup_router
app.include_router(automation_backup_router)

# NOORBRAIN SPRINT 11 PACK 5 HALF 2B
from services.automation.final_routes import router as automation_final_router
app.include_router(automation_final_router)

# NOORBRAIN SPRINT 12 CORE
from services.sprint12.routes import router as sprint12_router
app.include_router(sprint12_router)

# NOORBRAIN SPRINT 12 PACKS 1-3 HALF 1
from services.sprint12.advanced_routes import router as sprint12_advanced_router
app.include_router(sprint12_advanced_router)

# NOORBRAIN SPRINT 12 PACKS 4-5
from services.sprint12.packs45_routes import router as sprint12_packs45_router
app.include_router(sprint12_packs45_router)

# NOORBRAIN HALO OFFLINE AGENT CORE HALF 1
from services.offline_agent.routes import router as offline_agent_router
app.include_router(offline_agent_router)

# NOORBRAIN ACTIVITY API
from services.activity_engine.routes import router as activity_router
app.include_router(activity_router)

# NOORBRAIN ACTIVITY DASHBOARD ASSET
from services.activity_engine.assets import router as activity_asset_router
app.include_router(activity_asset_router)

# NOORBRAIN FAVICON ROUTE
from services.activity_engine.favicon import router as favicon_router
app.include_router(favicon_router)

# NOORBRAIN V3 PHASE A PACK 1
from services.halo_os.routes import router as halo_os_router
app.include_router(halo_os_router)

# NOORBRAIN V3 PHASE B PACK 1
from services.voice_os.routes import router as voice_os_router
app.include_router(voice_os_router)

# NOORBRAIN V3 PHASE B PACK 3
from services.voice_os.routes_pack3 import router as voice_os_live_router
app.include_router(voice_os_live_router)

# NOORBRAIN V3 PHASE B PACK 4
from services.voice_os.routes_pack4 import router as voice_os_pack4_router
app.include_router(voice_os_pack4_router)

# NOORBRAIN V3 C1.1 HALO RUNTIME MANAGER
from services.halo_runtime.routes import router as halo_runtime_router
app.include_router(halo_runtime_router)

# NOORBRAIN V3 C1.2 HALO AUDIO SERVICE
from services.halo_audio.routes import router as halo_audio_router
app.include_router(halo_audio_router)

# NOORBRAIN V3 C1.3-C1.5 VOICE INTELLIGENCE
from services.halo_voice_intelligence.routes import router as halo_voice_intelligence_router
app.include_router(halo_voice_intelligence_router)

# NOORBRAIN V3 C1.6-C1.7 VOICE RUNTIME
from services.halo_voice_runtime.routes import router as halo_voice_runtime_router
app.include_router(halo_voice_runtime_router)

# NOORBRAIN V3 C2.1-C2.3 CONVERSATION ENGINE
from services.halo_conversation.routes import router as halo_conversation_router
app.include_router(halo_conversation_router)

# NOORBRAIN V3 C2.4-C2.5 ACTION PLANNER
from services.halo_action_planner.routes import router as halo_action_planner_router
app.include_router(halo_action_planner_router)

# NOORBRAIN V3 C3-C6 BUNDLE
from services.smart_home_runtime.routes import router as smart_home_runtime_router
app.include_router(smart_home_runtime_router)
from services.family_ai.routes import router as family_ai_router
app.include_router(family_ai_router)
from services.release_tools.routes import router as release_tools_router
app.include_router(release_tools_router)
from fastapi.staticfiles import StaticFiles as NoorBrainPWAStaticFiles
app.mount("/dashboard-pwa", NoorBrainPWAStaticFiles(directory="dashboard/pwa"), name="dashboard-pwa")

# NOORBRAIN V3 C4 PRODUCTION MOBILE
from fastapi.responses import FileResponse
from services.mobile_companion.routes import router as mobile_companion_router
app.include_router(mobile_companion_router)
@app.get("/mobile", response_class=FileResponse)
def mobile_companion_page():
    return FileResponse("dashboard/mobile/index.html")

# NOORBRAIN V3 D1.1
from services.vision_intelligence.routes import router as vision_intelligence_router
app.include_router(vision_intelligence_router)

# NOORBRAIN V3 D1.2 VISION ZONES
from services.vision_zones.routes import router as vision_zones_router
app.include_router(vision_zones_router)

# NOORBRAIN V3 D1.3
from services.person_presence.routes import router as person_presence_router
app.include_router(person_presence_router)

# NOORBRAIN V3 D1.4 FACE IDENTITY
from services.face_identity.routes import router as face_identity_router
app.include_router(face_identity_router)

# NOORBRAIN V3 D1.5 ACTIVITY INTELLIGENCE
from services.activity_intelligence.routes import router as activity_intelligence_router
app.include_router(activity_intelligence_router)

# NOORBRAIN V3 D2 HALO BRAIN
from services.halo_brain.routes import router as halo_brain_router
app.include_router(halo_brain_router)

# NOORBRAIN V3 D3 HABIT LEARNING
from services.habit_learning.routes import router as habit_learning_router
app.include_router(habit_learning_router)

# NOORBRAIN V3 D4.1-D4.2 SMART AUTOMATION
from services.smart_automation.routes import router as smart_automation_router
app.include_router(smart_automation_router)

# NOORBRAIN V3 D4.3-D4.5 EXECUTION SAFETY ANALYTICS
from services.smart_automation.routes_extension import router as smart_automation_execution_router
app.include_router(smart_automation_execution_router)

# NOORBRAIN P1 PRAYER INTELLIGENCE
from services.prayer_intelligence.routes import router as prayer_intelligence_router
app.include_router(prayer_intelligence_router)

# NOORBRAIN P2 ISLAMIC REMINDER INTELLIGENCE
from services.islamic_reminders.routes import router as islamic_reminders_router
app.include_router(islamic_reminders_router)

# NOORBRAIN P3.1 FAMILY FACE LINKING
from services.family_linking.routes import router as family_linking_router
app.include_router(family_linking_router)

# NOORBRAIN P3.2 PERSONALIZED HALO
from services.personalized_halo.routes import router as personalized_halo_router
app.include_router(personalized_halo_router)

# NOORBRAIN P3.3 MOBILE NOTIFICATIONS
from services.mobile_notifications.routes import router as mobile_notifications_router
app.include_router(mobile_notifications_router)

# NOORBRAIN P3.4-P3.6 FINAL FAMILY MOBILE INTELLIGENCE
from services.mobile_notifications.routes_final import router as mobile_notifications_final_router
app.include_router(mobile_notifications_final_router)
