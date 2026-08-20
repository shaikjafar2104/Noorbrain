package com.noorbrain.carconnect.usb

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.os.Parcelable
import android.util.Log
import com.noorbrain.carconnect.core.ConnectionStateLogger
import com.noorbrain.carconnect.core.ConnectionStateManager
import java.io.IOException
import java.util.concurrent.Executors

/**
 * UsbCommunicationService
 *
 * Manages the USB communication channel with a connected device.
 * Phase 2 scope:
 *   - Detect USB permission result
 *   - Attempt to open a basic connection channel
 *   - Log all communication states and errors
 *
 * IMPORTANT: This service does NOT attempt to bypass authentication
 * or interact with vehicle safety systems. It only establishes a
 * standard USB host communication channel for diagnostic/logging purposes.
 */
class UsbCommunicationService(
    private val context: Context,
    private val stateManager: ConnectionStateManager,
    private val logger: ConnectionStateLogger
) {

    private val usbManager: UsbManager? = context.getSystemService(Context.USB_SERVICE) as? UsbManager
    private val executor = Executors.newSingleThreadExecutor()

    // Permission callback receiver
    private val permissionReceiver = object : BroadcastReceiver() {
        override fun onReceive(ctx: Context?, intent: Intent?) {
            val action = intent?.action
            if (UsbManager.ACTION_USB_PERMISSION == action) {
                val granted = intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)
                val device = intent.getParcelableExtra<UsbDevice>(UsbManager.EXTRA_DEVICE)
                if (granted && device != null) {
                    logger.log(ConnectionStateLogger.State.USB_PERMISSION_GRANTED,
                        "Permission granted for: ${device.deviceName}")
                    stateManager.setUsbCommunicating(true)
                    attemptOpenChannel(device)
                } else {
                    logger.log(ConnectionStateLogger.State.USB_PERMISSION_DENIED,
                        "Permission denied for USB device")
                    stateManager.setError("USB permission denied")
                }
            }
        }
    }

    private var permissionIntent: PendingIntent? = null

    init {
        // Register permission receiver
        val filter = IntentFilter(UsbManager.ACTION_USB_PERMISSION)
        val intent = Intent("com.noorbrain.carconnect.USB_PERMISSION")
        permissionIntent = PendingIntent.getBroadcast(
            context, 0, intent, PendingIntent.FLAG_MUTABLE
        )
        context.registerReceiver(permissionReceiver, filter)
    }

    /** Attempt to open a communication channel with the USB device. */
    private fun attemptOpenChannel(device: UsbDevice) {
        if (usbManager == null) {
            logger.log(ConnectionStateLogger.State.USB_COMM_ERROR, "UsbManager not available")
            stateManager.setError("UsbManager unavailable")
            return
        }

        executor.execute {
            try {
                // Step 1: Request permission if not already granted
                if (!usbManager.hasPermission(device)) {
                    logger.log(ConnectionStateLogger.State.USB_PERMISSION_GRANTED,
                        "Requesting permission for device: ${device.deviceName}")
                    usbManager.requestPermission(device, permissionIntent)
                    // Permission result will arrive via the receiver
                    return@execute
                }

                // Step 2: Open the device
                val connection = usbManager.openDevice(device)
                if (connection == null) {
                    logger.log(ConnectionStateLogger.State.USB_COMM_ERROR,
                        "Failed to open USB device: ${device.deviceName}")
                    stateManager.setError("USB open failed")
                    return@execute
                }

                logger.log(ConnectionStateLogger.State.USB_COMM_OPEN,
                    "USB device opened: ${device.deviceName}")

                // Step 3: Enumerate interfaces (diagnostic only — log what's available)
                for (i in 0 until device.interfaceCount) {
                    val intf = device.getInterface(i)
                    logger.log(ConnectionStateLogger.State.USB_COMM_OPEN,
                        "Interface $i: ID=${intf.id}, Class=${intf.interfaceClass}, " +
                        "Name=${intf.name}, Endpoints=${intf.endpointCount}")
                }

                // For Phase 2: We only need to verify the channel opens.
                // Phase 3+ will implement actual protocol communication.
                connection.close()

                logger.log(ConnectionStateLogger.State.USB_COMM_CLOSE,
                    "USB test channel closed: ${device.deviceName}")

            } catch (e: IOException) {
                logger.log(ConnectionStateLogger.State.USB_COMM_ERROR,
                    "IOException: ${e.message}")
                stateManager.setError("USB IOException: ${e.message}")
            } catch (e: Exception) {
                logger.log(ConnectionStateLogger.State.USB_COMM_ERROR,
                    "Unexpected error: ${e.message}")
                stateManager.setError("USB error: ${e.message}")
            }
        }
    }

    /**
     * Check if there are currently connected USB devices and attempt
     * to communicate with any that haven't been seen yet.
     */
    fun scanAndOpen() {
        if (usbManager == null) return

        val devices = usbManager.deviceList
        for (device in devices.values) {
            val hasPermission = usbManager.hasPermission(device)
            if (hasPermission) {
                logger.log(ConnectionStateLogger.State.USB_COMM_OPEN,
                    "Attempting channel for already-permissioned device: ${device.deviceName}")
                attemptOpenChannel(device)
            } else {
                logger.log(ConnectionStateLogger.State.USB_PERMISSION_GRANTED,
                    "Requesting permission for: ${device.deviceName}")
                usbManager.requestPermission(device, permissionIntent)
            }
        }
    }

    /** Clean up — unregister the permission receiver. */
    fun destroy() {
        try {
            context.unregisterReceiver(permissionReceiver)
        } catch (e: IllegalArgumentException) {
            // Already unregistered — safe to ignore
        }
    }
}
