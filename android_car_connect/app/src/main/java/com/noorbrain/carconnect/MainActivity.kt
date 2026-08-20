package com.noorbrain.carconnect

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.noorbrain.carconnect.core.ConnectionStateManager
import com.noorbrain.carconnect.core.ConnectionStateLogger
import com.noorbrain.carconnect.databinding.ActivityMainBinding
import com.noorbrain.carconnect.usb.UsbCommunicationService
import com.noorbrain.carconnect.usb.UsbReceiver
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * MainActivity
 *
 * Phase 2: Displays USB connection status and connection state logs.
 *
 * The UI is designed for quick glances while driving:
 * - Large status indicators
 * - Connection state summary
 * - Log viewer (scrollable, timestamped)
 * - Manual USB scan button
 * - Clear log button
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var app: CarConnectApp
    private lateinit var stateManager: ConnectionStateManager
    private lateinit var logger: ConnectionStateLogger
    private lateinit var usbService: UsbCommunicationService
    private lateinit var usbReceiver: UsbReceiver

    private lateinit var logAdapter: LogAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        app = applicationContext as CarConnectApp
        stateManager = app.connectionManager
        logger = app.stateLogger

        usbService = UsbCommunicationService(this, stateManager, logger)
        usbReceiver = UsbReceiver()

        // View binding
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Simple full-screen approach (car-friendly)
        // No edge-to-edge needed for Phase 2 prototype

        setupUi()
        registerReceivers()
        scanCurrentState()
    }

    private fun setupUi() {
        // USB scan button
        binding.btnScanUsb.setOnClickListener {
            scanCurrentState()
            Toast.makeText(this, "Scanning USB devices...", Toast.LENGTH_SHORT).show()
        }

        // Clear log button
        binding.btnClearLog.setOnClickListener {
            logger.clearLogs()
            logAdapter.submitList(emptyList())
            refreshLogView()
            Toast.makeText(this, "Logs cleared", Toast.LENGTH_SHORT).show()
        }

        // Refresh log button
        binding.btnRefreshLog.setOnClickListener {
            refreshLogView()
        }

        logAdapter = LogAdapter()
        binding.recyclerLogs.layoutManager = LinearLayoutManager(this)
        binding.recyclerLogs.adapter = logAdapter

        updateUi()
    }

    private fun registerReceivers() {
        val filter = UsbReceiver.intentFilter
        registerReceiver(usbReceiver, filter)
    }

    private fun unregisterReceivers() {
        try {
            unregisterReceiver(usbReceiver)
        } catch (e: IllegalArgumentException) {
            // Already unregistered — safe to ignore
        }
    }

    /** Scan current USB state and update UI. */
    private fun scanCurrentState() {
        val devices = stateManager.scanUsbDevices()
        usbService.scanAndOpen()

        updateUi()

        if (devices.isEmpty()) {
            binding.tvUsbStatus.text = "No USB device detected"
            binding.tvUsbStatus.setTextColor(0xFF888888.toInt())
        } else {
            val sb = StringBuilder()
            for (device in devices) {
                sb.append(device.toString()).append("\n")
            }
            binding.tvUsbStatus.text = "USB device(s) detected:\n$sb"
            binding.tvUsbStatus.setTextColor(0xFF00FF00.toInt())
        }
    }

    /** Refresh the log view from the log file. */
    private fun refreshLogView() {
        CoroutineScope(Dispatchers.IO).launch {
            val logContent = logger.readLogs()
            val lines = logContent.lines()
                .filter { it.isNotBlank() }
                .reversed() // Most recent first
                .take(200) // Cap at 200 lines for performance

            launch(Dispatchers.Main) {
                logAdapter.submitList(lines.toList())
            }
        }
    }

    /** Update all UI elements based on current state. */
    private fun updateUi() {
        val state = stateManager.getCurrentState()

        // Connection mode display
        binding.tvConnectionMode.text = "Mode: ${state.connectionMode}"

        // USB status
        if (state.usbConnected && state.usbDevice != null) {
            binding.tvUsbConnected.text = "USB: Connected"
            binding.tvUsbDeviceDetails.text = state.usbDevice.toString()
        } else {
            binding.tvUsbConnected.text = "USB: Disconnected"
            binding.tvUsbDeviceDetails.text = ""
        }

        // Error display
        if (state.lastError != null) {
            binding.tvError.text = "Error: ${state.lastError}"
            binding.tvError.visibility = View.VISIBLE
        } else {
            binding.tvError.visibility = View.GONE
        }

        refreshLogView()
    }

    override fun onResume() {
        super.onResume()
        updateUi()
        refreshLogView()
    }

    override fun onDestroy() {
        super.onDestroy()
        usbService.destroy()
        unregisterReceivers()
    }
}
