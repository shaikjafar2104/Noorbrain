package com.noorbrain.carconnect.wireless

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.le.*
import android.content.Context
import android.content.Intent
import android.net.wifi.WifiConfiguration
import android.net.wifi.WifiManager
import android.net.wifi.p2p.WifiP2pConfig
import android.net.wifi.p2p.WifiP2pDevice
import android.net.wifi.p2p.WifiP2pManager
import android.os.Looper
import android.os.Parcelable
import android.util.Log
import androidx.core.content.getSystemService
import com.noorbrain.carconnect.core.ConnectionStateManager
import com.noorbrain.carconnect.core.ConnectionStateLogger
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * WirelessConnectionManager
 *
 * Phase 3: Handles Bluetooth LE discovery/pairing and Wi-Fi Direct
 * connection establishment for wireless connection to the RAV4
 * via an external bridge device.
 *
 * ⚠️ EXPERIMENTAL — This phase requires the bridge device hardware
 * (Raspberry Pi Zero 2W) to be set up and running.
 *
 * Architecture:
 *   Phone (Wi-Fi Direct) → Bridge Device (Pi Zero 2W) → RAV4 USB
 */
@SuppressLint("MissingPermission")
class WirelessConnectionManager(
    private val context: Context,
    private val stateManager: ConnectionStateManager,
    private val logger: ConnectionStateLogger
) {

    companion object {
        private const val TAG = "WirelessConnectionManager"

        // BLE service UUID for bridge discovery
        val BRIDGE_SERVICE_UUID: UUID = UUID.fromString("0000aade-0000-1000-8000-00805f9b34fb")

        // Bridge device name prefix
        private const val BRIDGE_NAME_PREFIX = "RAV4-CarConnect-Bridge"

        // Wi-Fi Direct network details
        private const val WIFI_DIRECT_GROUP_OWNER = "RAV4-Bridge"
        private const val WIFI_DIRECT_PASSWORD = "carconnect123"
    }

    private val bluetoothManager = context.getSystemService<BluetoothManager>()
    private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager?.adapter

    private val wifiManager: WifiManager = context.applicationContext.getSystemService()
    private val wifiP2pManager = context.getSystemService<WifiP2pManager>()

    private val executor = Executors.newCachedThreadPool()
    private val isScanning = AtomicBoolean(false)

    // Track discovered bridge devices
    private val discoveredBridges: MutableMap<String, BridgeDeviceInfo> = mutableMapOf()
    private var connectedBridge: BridgeDeviceInfo? = null

    data class BridgeDeviceInfo(
        val deviceName: String,
        val deviceAddress: String,
        val rssi: Int,
        val isBridge: Boolean = true
    )

    // BLE Scanner
    private var bleScanner: BluetoothLeScanner? = null

    /**
     * Start Bluetooth LE discovery for bridge devices.
     * Devices with "RAV4-CarConnect-Bridge" prefix will be detected.
     */
    fun startBleDiscovery() {
        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled) {
            logger.log(ConnectionStateLogger.State.BT_DISCOVERY_START,
                "Bluetooth is not enabled")
            return
        }

        val scanner = bluetoothAdapter.bluetoothLeScanner ?: run {
            logger.log(ConnectionStateLogger.State.BT_DISCOVERY_START,
                "BLE scanner not available")
            return
        }

        this.bleScanner = scanner
        if (!isScanning.compareAndSet(false, true)) {
            logger.log(ConnectionStateLogger.State.BT_DISCOVERY_START,
                "Discovery already in progress")
            return
        }

        logger.log(ConnectionStateLogger.State.BT_DISCOVERY_START,
            "Starting BLE discovery for bridge devices")

        val scanFilter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid(BRIDGE_SERVICE_UUID))
            .build()

        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        scanner.startScan(listOf(scanFilter), settings, scanCallback)

        // Auto-stop after 10 seconds
        executor.execute {
            Thread.sleep(10000)
            stopBleDiscovery()
        }
    }

    /** Stop BLE discovery. */
    fun stopBleDiscovery() {
        if (isScanning.compareAndSet(true, false)) {
            bleScanner?.stopScan(scanCallback)
            logger.log(ConnectionStateLogger.State.BT_DISCOVERY_START,
                "BLE discovery stopped")
        }
    }

    /** BLE scan callback — detects bridge devices. */
    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            val device = result.device
            val name = result.device.name ?: "Unnamed"
            val rssi = result.rssi

            if (name.startsWith(BRIDGE_NAME_PREFIX)) {
                val bridge = BridgeDeviceInfo(
                    deviceName = name,
                    deviceAddress = device.address,
                    rssi = rssi
                )
                discoveredBridges[name] = bridge

                logger.log(ConnectionStateLogger.State.BT_DISCOVERY_FOUND,
                    "Found bridge: $name (${device.address}), RSSI=$rssi")
                stateManager.logBridgeFound(name, device.address, rssi)
            }
        }

        override fun onScanFailed(errorCode: Int) {
            logger.log(ConnectionStateLogger.State.ERROR,
                "BLE scan failed: error=$errorCode")
        }
    }

    /**
     * Attempt to connect to a bridge device via Wi-Fi Direct.
     * The bridge must be discovered first via BLE.
     */
    fun connectToBridge(bridge: BridgeDeviceInfo) {
        logger.log(ConnectionStateLogger.State.BT_CONNECTED,
            "Connecting to bridge: ${bridge.deviceName}")

        // Step 1: Establish Wi-Fi Direct connection
        if (wifiP2pManager != null) {
            connectViaWifiDirect(bridge)
        } else {
            // Fallback: try standard Wi-Fi connection
            connectViaWifi(bridge)
        }
    }

    /** Connect via Wi-Fi Direct (preferred for wireless AA). */
    @SuppressLint("MissingPermission")
    private fun connectViaWifiDirect(bridge: BridgeDeviceInfo) {
        logger.log(ConnectionStateLogger.State.WIFI_CONNECTING,
            "Connecting via Wi-Fi Direct to: ${bridge.deviceName}")

        val channel = wifiP2pManager?.initialize(context, Looper.getMainLooper())
        if (channel == null) {
            logger.log(ConnectionStateLogger.State.ERROR, "Failed to initialize Wi-Fi P2P channel")
            stateManager.setError("Wi-Fi Direct initialization failed")
            return
        }

        val config = WifiP2pConfig().apply {
            device = WifiP2pDevice().apply {
                this.address = bridge.deviceAddress
                this.device = bridge.deviceName
            }
            wps = WpsSetup.PROMPT
        }

        wifiP2pManager?.connect(channel, config, object : WifiP2pManager.ActionListener {
            override fun onSuccess() {
                logger.log(ConnectionStateLogger.State.WIFI_CONNECTED,
                    "Wi-Fi Direct connected to: ${bridge.deviceName}")
                connectedBridge = bridge
            }

            override fun onFailure(reason: Int) {
                logger.log(ConnectionStateLogger.State.WIFI_DISCONNECTED,
                    "Wi-Fi Direct connection failed: reason=$reason")
                stateManager.setError("Wi-Fi Direct connection failed (reason=$reason)")
            }
        })
    }

    /** Fallback: connect via standard Wi-Fi AP mode. */
    private fun connectViaWifi(bridge: BridgeDeviceInfo) {
        logger.log(ConnectionStateLogger.State.WIFI_CONNECTING,
            "Connecting via standard Wi-Fi to bridge: ${bridge.deviceName}")

        val config = WifiConfiguration().apply {
            SSID = "\"$WIFI_DIRECT_GROUP_OWNER\""
            preSharedKey = WIFI_DIRECT_PASSWORD
        }

        val networkId = wifiManager.addNetwork(config)
        if (networkId == -1) {
            logger.log(ConnectionStateLogger.State.ERROR, "Failed to add Wi-Fi network")
            stateManager.setError("Wi-Fi network config failed")
            return
        }

        if (wifiManager.enableNetwork(networkId, true)) {
            logger.log(ConnectionStateLogger.State.WIFI_CONNECTED,
                "Wi-Fi connected to bridge network")
            connectedBridge = bridge
        } else {
            logger.log(ConnectionStateLogger.State.WIFI_DISCONNECTED,
                "Failed to enable Wi-Fi network")
            stateManager.setError("Wi-Fi enable failed")
        }
    }

    /**
     * Attempt automatic reconnection to the last-known bridge.
     * Called when the app resumes or after a connection drop.
     */
    fun attemptAutoReconnect() {
        val lastBridge = getLastKnownBridge()
        if (lastBridge != null) {
            logger.log(ConnectionStateLogger.State.BT_PAIRING,
                "Attempting auto-reconnect to: ${lastBridge.deviceName}")
            connectToBridge(lastBridge)
        } else {
            logger.log(ConnectionStateLogger.State.BRIDGE_NOT_DETECTED,
                "No previous bridge to reconnect to")
        }
    }

    /** Disconnect from the current bridge. */
    fun disconnect() {
        if (connectedBridge != null) {
            logger.log(ConnectionStateLogger.State.BT_DISCONNECTED,
                "Disconnecting from bridge: ${connectedBridge!!.deviceName}")

            if (wifiP2pManager != null) {
                val mainLooper = Looper.getMainLooper()
                val channel = wifiP2pManager?.initialize(context, mainLooper)
                channel?.let {
                    wifiP2pManager?.removeGroup(it, object : WifiP2pManager.ActionListener {
                        override fun onSuccess() {
                            logger.log(ConnectionStateLogger.State.WIFI_DISCONNECTED, "Wi-Fi Direct group removed")
                        }

                        override fun onFailure(reason: Int) {
                            logger.log(ConnectionStateLogger.State.WIFI_DISCONNECTED,
                                "Failed to remove Wi-Fi Direct group: $reason")
                        }
                    })
                }
            }

            connectedBridge = null
        }
    }

    private fun getLastKnownBridge(): BridgeDeviceInfo? {
        // In Phase 3, this would read from SharedPreferences
        // For now, return null until we have persisted bridge info
        return null
    }

    fun getDiscoveredBridges(): List<BridgeDeviceInfo> {
        return discoveredBridges.values.toList()
    }

    fun destroy() {
        stopBleDiscovery()
        disconnect()
    }
}

// WpsSetup enum for Wi-Fi Protected Setup
private enum class WpsSetup {
    PROMPT,
    PIN
}
