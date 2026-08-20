package com.noorbrain.carconnect;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiConfiguration;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;

import com.noorbrain.carconnect.core.ConnectionStateLogger;
import com.noorbrain.carconnect.core.ConnectionStateManager;
import com.noorbrain.carconnect.databinding.ActivityMainBinding;
import com.noorbrain.carconnect.usb.UsbCommunicationService;
import com.noorbrain.carconnect.usb.UsbReceiver;

import java.math.BigInteger;
import java.net.InetAddress;
import java.net.UnknownHostException;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.List;

/**
 * MainActivity — CarPlay Edition
 *
 * Phase 3+: Supports both USB detection AND WiFi connection to the
 * Raspberry Pi Zero 2W bridge device.
 *
 * This version supports:
 * - USB connection detection and logging (Phase 2)
 * - WiFi connection to bridge device (Phase 3+)
 * - CarPlay mode activation
 * - Connection state monitoring
 */
public class MainActivity extends AppCompatActivity {
    private static final String TAG = "MainActivity";

    private ActivityMainBinding binding;
    private CarConnectApp app;
    private ConnectionStateManager stateManager;
    private ConnectionStateLogger logger;
    private UsbCommunicationService usbService;
    private UsbReceiver usbReceiver;
    private LogAdapter logAdapter;

    // WiFi
    private WifiManager wifiManager;
    private Handler handler = new Handler(Looper.getMainLooper());
    private static final String BRIDGE_SSID = "RAV4-CarConnect-Bridge";
    private static final String BRIDGE_PASSWORD = "carconnect123";

    // Connection mode
    private enum Mode { USB_DIRECT, WIFI_BRIDGE }
    private Mode currentMode = Mode.USB_DIRECT;

    // WiFi receiver for connection state
    private final BroadcastReceiver wifiReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String action = intent.getAction();
            if (WifiManager.NETWORK_STATE_CHANGED_ACTION.equals(action)) {
                android.net.NetworkInfo netInfo = intent.getParcelableExtra(WifiManager.EXTRA_NETWORK_INFO);
                if (netInfo != null && netInfo.isConnected()) {
                    WifiInfo wifiInfo = intent.getParcelableExtra(WifiManager.EXTRA_WIFI_INFO);
                    if (wifiInfo != null) {
                        String ssid = wifiInfo.getSSID();
                        if (ssid != null && ssid.contains(BRIDGE_SSID)) {
                            log("WiFi connected to bridge: " + ssid);
                            binding.tvWifiStatus.setText("WiFi: Connected to Bridge");
                            binding.tvWifiStatus.setTextColor(0xFF00FF00);
                        }
                    }
                }
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        app = (CarConnectApp) getApplication();
        stateManager = app.getConnectionManager();
        logger = app.getStateLogger();

        usbService = new UsbCommunicationService(this, stateManager, logger);
        usbReceiver = new UsbReceiver();

        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);

        setupUI();
        registerReceivers();
        scanCurrentState();
    }

    private void setupUI() {
        // Mode toggle
        binding.btnSwitchMode.setOnClickListener(v -> switchMode());

        // USB scan
        binding.btnScanUsb.setOnClickListener(v -> {
            scanCurrentState();
            Toast.makeText(this, "Scanning...", Toast.LENGTH_SHORT).show();
        });

        // WiFi connect
        binding.btnConnectWifi.setOnClickListener(v -> connectToBridge());

        // Clear log
        binding.btnClearLog.setOnClickListener(v -> {
            logger.clearLogs();
            logAdapter.submitList(new ArrayList<>());
            refreshLogView();
            Toast.makeText(this, "Logs cleared", Toast.LENGTH_SHORT).show();
        });

        // Refresh log
        binding.btnRefreshLog.setOnClickListener(v -> refreshLogView());

        logAdapter = new LogAdapter();
        binding.recyclerLogs.setLayoutManager(new LinearLayoutManager(this));
        binding.recyclerLogs.setAdapter(logAdapter);

        updateUI();
    }

    private void switchMode() {
        if (currentMode == Mode.USB_DIRECT) {
            currentMode = Mode.WIFI_BRIDGE;
            log("Switching to WiFi Bridge mode — connecting to bridge device");
            binding.tvModeIndicator.setText("Mode: WiFi Bridge");
            binding.tvUsbControls.setVisibility(View.GONE);
            binding.tvWifiControls.setVisibility(View.VISIBLE);
        } else {
            currentMode = Mode.USB_DIRECT;
            log("Switching to USB Direct mode");
            binding.tvModeIndicator.setText("Mode: USB Direct");
            binding.tvUsbControls.setVisibility(View.VISIBLE);
            binding.tvWifiControls.setVisibility(View.GONE);
        }
        updateUI();
    }

    private void connectToBridge() {
        if (wifiManager == null) {
            log("WiFi not available");
            return;
        }

        log("Connecting to bridge: " + BRIDGE_SSID);

        // Turn on WiFi
        if (!wifiManager.isWifiEnabled()) {
            wifiManager.setWifiEnabled(true);
        }

        // Create WiFi config
        WifiConfiguration config = new WifiConfiguration();
        config.SSID = "\"" + BRIDGE_SSID + "\"";
        config.preSharedKey = "\"" + BRIDGE_PASSWORD + "\"";
        config.allowedKeyManagement.set(WifiConfiguration.KeyMgmt.WPA_PSK);

        int networkId = wifiManager.addNetwork(config);
        if (networkId == -1) {
            log("Failed to add WiFi network");
            Toast.makeText(this, "Failed to connect to bridge", Toast.LENGTH_LONG).show();
            return;
        }

        if (wifiManager.enableNetwork(networkId, true)) {
            log("WiFi connection initiated to bridge");
            Toast.makeText(this, "Connecting to bridge...", Toast.LENGTH_SHORT).show();
        } else {
            log("Failed to enable WiFi network");
            Toast.makeText(this, "WiFi connection failed", Toast.LENGTH_LONG).show();
        }
    }

    private void registerReceivers() {
        IntentFilter filter = UsbReceiver.getIntentFilter();
        registerReceiver(usbReceiver, filter);

        IntentFilter wifiFilter = new IntentFilter();
        wifiFilter.addAction(WifiManager.NETWORK_STATE_CHANGED_ACTION);
        registerReceiver(wifiReceiver, wifiFilter);
    }

    private void unregisterReceivers() {
        try {
            unregisterReceiver(usbReceiver);
        } catch (IllegalArgumentException e) {
            // Already unregistered
        }
        try {
            unregisterReceiver(wifiReceiver);
        } catch (IllegalArgumentException e) {
            // Already unregistered
        }
    }

    private void scanCurrentState() {
        List<ConnectionStateManager.UsbDeviceInfo> devices = stateManager.scanUsbDevices();
        usbService.scanAndOpen();

        updateUI();

        if (devices.isEmpty()) {
            binding.tvUsbStatus.setText("No USB device detected");
            binding.tvUsbStatus.setTextColor(0xFF888888);
        } else {
            StringBuilder sb = new StringBuilder();
            for (ConnectionStateManager.UsbDeviceInfo device : devices) {
                sb.append(device.toString()).append("\n");
                log("USB Device: " + device.toString());
            }
            binding.tvUsbStatus.setText("USB device(s) detected:\n" + sb.toString());
            binding.tvUsbStatus.setTextColor(0xFF00FF00);
        }
    }

    private void refreshLogView() {
        new Thread(() -> {
            String logContent = logger.readLogs();
            List<String> lines = new ArrayList<>();
            for (String line : logContent.split("\n")) {
                if (!line.trim().isEmpty()) {
                    lines.add(line);
                }
            }
            // Reverse for most recent first
            java.util.Collections.reverse(lines);
            // Cap at 200 lines
            if (lines.size() > 200) {
                lines = new ArrayList<>(lines.subList(0, 200));
            }

            runOnUiThread(() -> logAdapter.submitList(lines));
        }).start();
    }

    private void updateUI() {
        ConnectionStateManager.ConnectionState state = stateManager.getCurrentState();

        binding.tvConnectionMode.setText("Mode: " + state.connectionMode);
        binding.tvModeIndicator.setText("Mode: " + (currentMode == Mode.USB_DIRECT ? "USB Direct" : "WiFi Bridge"));

        if (state.usbConnected && state.usbDevice != null) {
            binding.tvUsbConnected.setText("USB: Connected");
            binding.tvUsbDeviceDetails.setText(state.usbDevice.toString());
        } else {
            binding.tvUsbConnected.setText("USB: Disconnected");
            binding.tvUsbDeviceDetails.setText("");
        }

        if (currentMode == Mode.USB_DIRECT) {
            binding.tvUsbControls.setVisibility(View.VISIBLE);
            binding.tvWifiControls.setVisibility(View.GONE);
        } else {
            binding.tvUsbControls.setVisibility(View.GONE);
            binding.tvWifiControls.setVisibility(View.VISIBLE);
        }

        if (state.lastError != null) {
            binding.tvError.setText("Error: " + state.lastError);
            binding.tvError.setVisibility(View.VISIBLE);
        } else {
            binding.tvError.setVisibility(View.GONE);
        }

        refreshLogView();
    }

    private void log(String message) {
        logger.log(ConnectionStateLogger.State.CONNECTION_ESTABLISHED, message);
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateUI();
        refreshLogView();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        usbService.destroy();
        unregisterReceivers();
    }
}
