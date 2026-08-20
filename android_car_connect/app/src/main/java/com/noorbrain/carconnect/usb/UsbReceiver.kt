package com.noorbrain.carconnect.usb

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbAccessory
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.util.Log
import com.noorbrain.carconnect.core.ConnectionStateLogger
import com.noorbrain.carconnect.core.ConnectionStateManager

/**
 * UsbReceiver
 *
 * BroadcastReceiver that listens for USB device attached/detached events
 * and USB accessory events. Delegates state changes to ConnectionStateManager.
 *
 * Registered in AndroidManifest.xml with intent filters for:
 *   - android.hardware.usb.action.USB_DEVICE_ATTACHED
 *   - android.hardware.usb.action.USB_DEVICE_DETACHED
 *   - android.hardware.usb.action.USB_ACCESSORY_ATTACHED
 *   - android.hardware.usb.action.USB_ACCESSORY_DETACHED
 *
 * Phase 2: Detection only — does NOT attempt to open communication channels
 * or bypass any authentication. Logging is the primary deliverable.
 */
class UsbReceiver : android.content.BroadcastReceiver() {

    companion object {
        private const val TAG = "UsbReceiver"

        /** Intent filter for all USB events this receiver handles. */
        val intentFilter = IntentFilter().apply {
            addAction(UsbManager.ACTION_USB_DEVICE_ATTACHED)
            addAction(UsbManager.ACTION_USB_DEVICE_DETACHED)
            addAction(UsbManager.ACTION_USB_ACCESSORY_ATTACHED)
            addAction(UsbManager.ACTION_USB_ACCESSORY_DETACHED)
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        val logger = getConnectionStateLogger(context)
        val stateManager = getConnectionStateManager(context)
        val action = intent.action

        when (action) {
            UsbManager.ACTION_USB_DEVICE_ATTACHED -> {
                val device = intent.getParcelableExtra<UsbDevice>(UsbManager.EXTRA_DEVICE)
                if (device != null) {
                    Log.i(TAG, "USB device attached: ${device.deviceName}")
                    stateManager.onUsbDeviceAttached(device)
                    logger.log(
                        ConnectionStateLogger.State.USB_ATTACHED,
                        "Device attached: ${device.deviceName}, VID=0x${device.vendorId.toString(16)}, PID=0x${device.productId.toString(16)}"
                    )
                }
            }

            UsbManager.ACTION_USB_DEVICE_DETACHED -> {
                val device = intent.getParcelableExtra<UsbDevice>(UsbManager.EXTRA_DEVICE)
                if (device != null) {
                    Log.i(TAG, "USB device detached: ${device.deviceName}")
                    stateManager.onUsbDeviceDetached(device)
                    logger.log(
                        ConnectionStateLogger.State.USB_DETACHED,
                        "Device detached: ${device.deviceName}, VID=0x${device.vendorId.toString(16)}, PID=0x${device.productId.toString(16)}"
                    )
                }
            }

            UsbManager.ACTION_USB_ACCESSORY_ATTACHED -> {
                val accessory =
                    intent.getParcelableExtra<UsbAccessory>(UsbManager.EXTRA_ACCESSORY)
                if (accessory != null) {
                    Log.i(TAG, "USB accessory attached: ${accessory.manufacturer} ${accessory.model}")
                    stateManager.onUsbAccessoryAttached(accessory)
                    logger.log(
                        ConnectionStateLogger.State.USB_ACCESSORY_ATTACHED,
                        "Accessory: ${accessory.manufacturer}, model=${accessory.model}"
                    )
                }
            }

            UsbManager.ACTION_USB_ACCESSORY_DETACHED -> {
                val accessory =
                    intent.getParcelableExtra<UsbAccessory>(UsbManager.EXTRA_ACCESSORY)
                if (accessory != null) {
                    Log.i(TAG, "USB accessory detached: ${accessory.manufacturer} ${accessory.model}")
                    stateManager.onUsbAccessoryDetached(accessory)
                    logger.log(
                        ConnectionStateLogger.State.USB_ACCESSORY_DETACHED,
                        "Accessory: ${accessory.manufacturer}, model=${accessory.model}"
                    )
                }
            }

            else -> {
                Log.w(TAG, "Unknown USB action: $action")
            }
        }
    }

    /** Get the ConnectionStateManager from the Application context. */
    private fun getConnectionStateManager(context: Context): ConnectionStateManager {
        val app = context.applicationContext as? com.noorbrain.carconnect.CarConnectApp
        return app?.connectionManager ?: ConnectionStateManager(context)
    }

    /** Get the ConnectionStateLogger from the Application context. */
    private fun getConnectionStateLogger(context: Context): ConnectionStateLogger {
        val app = context.applicationContext as? com.noorbrain.carconnect.CarConnectApp
        return app?.stateLogger ?: ConnectionStateLogger(context)
    }
}
