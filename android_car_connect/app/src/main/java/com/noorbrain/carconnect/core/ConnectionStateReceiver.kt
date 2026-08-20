package com.noorbrain.carconnect.core

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.util.Log
import android.hardware.usb.UsbManager

/**
 * ConnectionStateReceiver
 *
 * A lightweight BroadcastReceiver that monitors general connectivity state
 * changes (USB, network) and logs them. This is used for Phase 2+ monitoring.
 */
class ConnectionStateReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "ConnectionStateReceiver"

        fun getIntentFilter(): IntentFilter {
            return IntentFilter().apply {
                addAction(Intent.ACTION_MEDIA_MOUNTED)
                addAction(Intent.ACTION_MEDIA_UNMOUNTED)
                addAction(Intent.ACTION_BATTERY_CHANGED)
                addAction(UsbManager.ACTION_USB_STATE)
            }
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action
        val logger = getConnectionStateLogger(context)

        when (action) {
            UsbManager.ACTION_USB_STATE -> {
                val connected = intent.getBooleanExtra(UsbManager.USB_CONNECTED, false)
                if (connected) {
                    logger.log(ConnectionStateLogger.State.CONNECTION_ESTABLISHED, "USB state: connected")
                } else {
                    logger.log(ConnectionStateLogger.State.CONNECTION_LOST, "USB state: disconnected")
                }
            }

            Intent.ACTION_MEDIA_MOUNTED -> {
                logger.log(ConnectionStateLogger.State.CONNECTION_ESTABLISHED, "Media mounted: ${intent.data}")
            }

            Intent.ACTION_MEDIA_UNMOUNTED -> {
                logger.log(ConnectionStateLogger.State.CONNECTION_LOST, "Media unmounted: ${intent.data}")
            }

            Intent.ACTION_BATTERY_CHANGED -> {
                val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
                val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
                val percent = if (level >= 0 && scale > 0) (level * 100) / scale else -1
                if (percent >= 0) {
                    logger.log(ConnectionStateLogger.State.CONNECTION_ESTABLISHED, "Battery: ${percent}%")
                }
            }

            else -> {
                Log.d(TAG, "Received action: $action")
            }
        }
    }

    private fun getConnectionStateLogger(context: Context): ConnectionStateLogger {
        val app = context.applicationContext as? CarConnectApp
        return app?.stateLogger ?: ConnectionStateLogger(context)
    }
}
