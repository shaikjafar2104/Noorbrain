package com.noorbrain.carconnect.core

import android.content.Context
import android.util.Log
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * ConnectionStateLogger
 *
 * Persists all connection-related state transitions to a local log file
 * and emits them to logcat. This is the "logging/debugging system" required
 * by Phase 2.
 *
 * Log file location:
 *   <app_storage_dir>/noorbrain_carconnect_logs/connection_log.txt
 *
 * Each entry is a single line:
 *   YYYY-MM-DD HH:MM:SS.mmm | STATE | message
 */
class ConnectionStateLogger(private val context: Context) {

    enum class State {
        APP_START,
        APP_STOP,
        USB_ATTACHED,
        USB_DETACHED,
        USB_DEVICE_FOUND,
        USB_DEVICE_NOT_FOUND,
        USB_ACCESSORY_ATTACHED,
        USB_ACCESSORY_DETACHED,
        USB_COMM_OPEN,
        USB_COMM_CLOSE,
        USB_COMM_ERROR,
        USB_PERMISSION_GRANTED,
        USB_PERMISSION_DENIED,
        BT_DISCOVERY_START,
        BT_DISCOVERY_FOUND,
        BT_PAIRING,
        BT_CONNECTED,
        BT_DISCONNECTED,
        WIFI_SCAN_START,
        WIFI_SCAN_RESULT,
        WIFI_CONNECTING,
        WIFI_CONNECTED,
        WIFI_DISCONNECTED,
        CONNECTION_ESTABLISHED,
        CONNECTION_LOST,
        BRIDGE_DETECTED,
        BRIDGE_NOT_DETECTED,
        PROJECTION_START,
        PROJECTION_STOP,
        DRIVE_MODE_ENTER,
        DRIVE_MODE_EXIT,
        NOTIFICATION_RECEIVED,
        VOICE_COMMAND,
        CALL_INCOMING,
        CALL_ENDED,
        ERROR
    }

    private val logDir: File = File(context.filesDir, "noorbrain_carconnect_logs")
    private val logFile: File = File(logDir, "connection_log.txt")
    private val dateFmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)
    private val executor = Executors.newSingleThreadExecutor()
    private val isInitialised = AtomicBoolean(false)

    init {
        logDir.mkdirs()
    }

    /** Write a structured log entry to both logcat and the log file. */
    fun log(state: State, message: String) {
        val timestamp = dateFmt.format(Date())
        val line = String.format("%s | %-22s | %s", timestamp, state, message)

        // Logcat
        Log.d("ConnectionState", "[$state] $message")

        // File (background thread)
        if (isInitialised.compareAndSet(false, true) || logFile.exists()) {
            executor.execute {
                try {
                    logFile.appendText("$line\n")
                } catch (e: Exception) {
                    Log.e("ConnectionStateLogger", "Failed to write log: ${e.message}")
                }
            }
        }
    }

    /** Return the current log file contents. Called from UI (background thread). */
    fun readLogs(): String {
        return try {
            logFile.readText(Charsets.UTF_8)
        } catch (e: Exception) {
            "Log file not available: ${e.message}"
        }
    }

    /** Clear the log file. */
    fun clearLogs() {
        executor.execute {
            try {
                if (logFile.exists()) logFile.writeText("")
            } catch (e: Exception) {
                Log.e("ConnectionStateLogger", "Failed to clear log: ${e.message}")
            }
        }
    }

    fun onAppStart() {
        log(State.APP_START, "CarConnect app started")
    }

    fun onAppStop() {
        log(State.APP_STOP, "CarConnect app stopped")
    }

    /** Return the path to the log file as a string for UI display. */
    fun getLogPath(): String = logFile.absolutePath
}
