package com.noorbrain.carconnect.core

import android.content.Context
import android.hardware.usb.UsbAccessory
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.util.Log
import androidx.core.content.getSystemService
import com.noorbrain.carconnect.CarConnectApp
import java.util.concurrent.atomic.AtomicBoolean

/**
 * ConnectionStateManager
 *
 * Tracks the current state of USB, Bluetooth, and Wi-Fi connections.
 * Acts as the central state hub that the UI and background services read from.
 *
 * Phase 2 scope: USB connection detection only.
 * Phases 3-5 will extend this for Bluetooth/Wi-Fi/bridge management.
 */
class ConnectionStateManager(private val context: Context) {

    data class UsbDeviceInfo(
        val deviceId: Int,
        val vendorId: Int,
        val productId: Int,
        val deviceName: String,
        val manufacturerName: String?,
        val productName: String?,
        val interfaceCount: Int
    ) {
        /** Format as a human-readable string for logging. */
        override fun toString(): String {
            return "USB Device{id=$deviceId, VID=0x${vendorId.toString(16)}, " +
                "PID=0x${productId.toString(16)}, name='$deviceName', " +
                "manufacturer='$manufacturerName', product='$productName', " +
                "interfaces=$interfaceCount}"
        }
    }

    /** Observable state for the UI */
    data class ConnectionState(
        val usbConnected: Boolean = false,
        val usbDevice: UsbDeviceInfo? = null,
        val accessoryConnected: Boolean = false,
        val bluetoothConnected: Boolean = false,
        val wifiConnected: Boolean = false,
        val bridgeActive: Boolean = false,
        val connectionMode: ConnectionMode = ConnectionMode.DISCONNECTED,
        val lastError: String? = null
    )

    enum class ConnectionMode {
        DISCONNECTED,
        USB_CONNECTED,
        USB_COMMUNICATING,
        BT_DISCOVERING,
        BT_CONNECTED,
        WIFI_CONNECTED,
        BRIDGE_ACTIVE
    }

    private val stateLogger = (context.applicationContext as? CarConnectApp)?.stateLogger
        ?: ConnectionStateLogger(context)

    private val isInitialised = AtomicBoolean(false)

    // Current state — simple mutable holder (thread-safe enough for Phase 2)
    @Volatile
    private var currentState: ConnectionState = ConnectionState()

    /** Initialise the state manager. Reads current USB state on startup. */
    fun initialise() {
        if (isInitialised.compareAndSet(false, true)) {
            Log.i("ConnectionStateManager", "Initialising connection state manager")
            scanExistingUsbDevices()
        }
    }

    /** Returns a copy of the current state. */
    fun getCurrentState(): ConnectionState = currentState

    /** Check if USB host mode is available on this device. */
    fun isUsbHostSupported(): Boolean {
        val usbManager = context.getSystemService<UsbManager>()
        return usbManager != null
    }

    /** Scan for currently-connected USB devices. */
    fun scanUsbDevices(): List<UsbDeviceInfo> {
        val usbManager = context.getSystemService<UsbManager>() ?: return emptyList()
        val result = mutableListOf<UsbDeviceInfo>()

        val deviceList = usbManager.deviceList
        for (device in deviceList.values) {
            val info = parseUsbDevice(device)
            result.add(info)
            stateLogger.log(ConnectionStateLogger.State.USB_DEVICE_FOUND, info.toString())
            Log.d("ConnectionStateManager", "Found USB device: $info")
        }

        if (result.isEmpty()) {
            stateLogger.log(ConnectionStateLogger.State.USB_DEVICE_NOT_FOUND, "No USB devices connected")
        }

        return result
    }

    /** Parse a UsbDevice into UsbDeviceInfo. */
    private fun parseUsbDevice(device: UsbDevice): UsbDeviceInfo {
        return UsbDeviceInfo(
            deviceId = device.deviceId,
            vendorId = device.vendorId,
            productId = device.productId,
            deviceName = device.deviceName,
            manufacturerName = device.getManufacturerName(),
            productName = device.getProductName(),
            interfaceCount = device.interfaceCount
        )
    }

    /** Called when a USB device is attached. Updates state and logs. */
    fun onUsbDeviceAttached(device: UsbDevice) {
        val info = parseUsbDevice(device)
        currentState = currentState.copy(
            usbConnected = true,
            usbDevice = info,
            connectionMode = ConnectionMode.USB_CONNECTED
        )
        stateLogger.log(ConnectionStateLogger.State.USB_ATTACHED, info.toString())
        stateLogger.log(ConnectionStateLogger.State.USB_DEVICE_FOUND, info.toString())
    }

    /** Called when a USB device is detached. Updates state and logs. */
    fun onUsbDeviceDetached(device: UsbDevice) {
        if (currentState.usbDevice?.deviceId == device.deviceId ||
            currentState.usbDevice?.vendorId == device.vendorId &&
            currentState.usbDevice?.productId == device.productId) {

            stateLogger.log(
                ConnectionStateLogger.State.USB_DETACHED,
                "USB device detached: ${device.deviceName} (VID=0x${device.vendorId.toString(16)}, PID=0x${device.productId.toString(16)})"
            )

            currentState = currentState.copy(
                usbConnected = false,
                usbDevice = null,
                connectionMode = if (currentState.bluetoothConnected) {
                    ConnectionMode.BT_CONNECTED
                } else {
                    ConnectionMode.DISCONNECTED
                }
            )
        }
    }

    /** Called when a USB accessory is attached. */
    fun onUsbAccessoryAttached(accessory: UsbAccessory) {
        stateLogger.log(
            ConnectionStateLogger.State.USB_ACCESSORY_ATTACHED,
            "USB Accessory attached: ${accessory.manufacturer}, model=${accessory.model}"
        )
        currentState = currentState.copy(
            accessoryConnected = true,
            connectionMode = ConnectionMode.USB_CONNECTED
        )
    }

    /** Called when a USB accessory is detached. */
    fun onUsbAccessoryDetached(accessory: UsbAccessory) {
        stateLogger.log(
            ConnectionStateLogger.State.USB_ACCESSORY_DETACHED,
            "USB Accessory detached: ${accessory.manufacturer}, model=${accessory.model}"
        )
        currentState = currentState.copy(
            accessoryConnected = false,
            connectionMode = if (currentState.usbConnected) {
                ConnectionMode.USB_CONNECTED
            } else {
                ConnectionMode.DISCONNECTED
            }
        )
    }

    /** Record a communication state change. */
    fun setUsbCommunicating(isCommunicating: Boolean) {
        if (isCommunicating) {
            stateLogger.log(ConnectionStateLogger.State.USB_COMM_OPEN, "USB communication channel opened")
            currentState = currentState.copy(connectionMode = ConnectionMode.USB_COMMUNICATING)
        } else {
            stateLogger.log(ConnectionStateLogger.State.USB_COMM_CLOSE, "USB communication channel closed")
            currentState = currentState.copy(
                connectionMode = if (currentState.usbConnected) {
                    ConnectionMode.USB_CONNECTED
                } else {
                    ConnectionMode.DISCONNECTED
                }
            )
        }
    }

    /** Record an error. */
    fun setError(error: String) {
        stateLogger.log(ConnectionStateLogger.State.ERROR, error)
        currentState = currentState.copy(lastError = error)
    }

    /** Clear the last error. */
    fun clearError() {
        currentState = currentState.copy(lastError = null)
    }

    /** Log that a bridge device was found during BLE discovery. */
    fun logBridgeFound(name: String, address: String, rssi: Int) {
        stateLogger.log(
            ConnectionStateLogger.State.BRIDGE_DETECTED,
            "Bridge found: $name ($address), RSSI=$rssi"
        )
        currentState = currentState.copy(bridgeActive = true)
    }

    /** Scan for any existing USB devices on startup. */
    private fun scanExistingUsbDevices() {
        val usbManager = context.getSystemService<UsbManager>()
        if (usbManager == null) {
            stateLogger.log(ConnectionStateLogger.State.ERROR, "UsbManager not available")
            return
        }

        val deviceList = usbManager.deviceList
        if (deviceList.isNotEmpty()) {
            Log.d("ConnectionStateManager", "Found ${deviceList.size} existing USB device(s) on startup")
            for (device in deviceList.values) {
                onUsbDeviceAttached(device)
            }
        } else {
            stateLogger.log(ConnectionStateLogger.State.USB_DEVICE_NOT_FOUND, "No USB devices on startup scan")
        }

        // Check for existing accessories
        val accessories = usbManager.accessoryList
        if (!accessories.isNullOrEmpty()) {
            Log.d("ConnectionStateManager", "Found ${accessories.size} existing USB accessory(ies) on startup")
            for (accessory in accessories) {
                onUsbAccessoryAttached(accessory)
            }
        }
    }
}
