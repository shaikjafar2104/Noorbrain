package com.noorbrain.carconnect

import android.app.Application
import android.util.Log
import com.noorbrain.carconnect.core.ConnectionStateManager
import com.noorbrain.carconnect.core.ConnectionStateLogger

/**
 * Application class for NoorBrain CarConnect.
 *
 * Initialises connection state management and logging.
 *
 * Phase 2: USB prototype — no bridge device required.
 * The 2019 Toyota RAV4 Entune 3.0 supports Android Auto natively over USB.
 * This app detects and monitors the USB connection.
 */
class CarConnectApp : Application() {

    companion object {
        private const val TAG = "CarConnectApp"
    }

    // Singleton: connection state manager tracks USB + wireless state
    val connectionManager: ConnectionStateManager by lazy {
        ConnectionStateManager(this)
    }

    // Singleton: structured logger for all connection events
    val stateLogger: ConnectionStateLogger by lazy {
        ConnectionStateLogger(this)
    }

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "CarConnect app created — Phase 2 USB Prototype")

        // Initialise connection state
        connectionManager.initialise()
        stateLogger.onAppStart()
    }

    override fun onTerminate() {
        super.onTerminate()
        stateLogger.onAppStop()
    }
}
