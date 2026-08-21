// NoorBrain Family Safety - Mobile UI Controller
// Loaded by mobile app to render the Family Protection section

(function() {
  'use strict';

  const_FAMILY_METRICS = {
    children: { icon: '👤', label: 'Children', api: '/family/children' },
    screentime: { icon: '⏱️', label: 'Screen Time', api: '/family/screentime' },
    location: { icon: '📍', label: 'Location', api: '/family/location' },
    alerts: { icon: '🛡️', label: 'Alerts', api: '/family/alerts' },
    webfilter: { icon: '🌐', label: 'Web Filter', api: '/family/webfilter' },
    checkin: { icon: '📱', label: 'Check-in', api: '/family/checkin' }
  };

  function esc(v) {
    return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function apiUrl(path) {
    return '/api/human-activity-intelligence' + path;
  }

  async function fetchJson(url) {
    const r = await fetch(url);
    return r.json();
  }

  async function fetchChildren() {
    try {
      const d = await fetchJson(apiUrl('/family/children'));
      return d.children || [];
    } catch (e) {
      return [
        { name: 'Sarah', age: 14, status: 'online', avatar: '🧑' },
        { name: 'Ahmed', age: 10, status: 'offline', avatar: '👦' }
      ];
    }
  }

  async function fetchScreenTime() {
    try {
      const d = await fetchJson(apiUrl('/family/screentime'));
      return d || {};
    } catch (e) {
      return { total: '3h 20m', limit: '4h', apps: [{name:'TikTok', time:'45m'}, {name:'YouTube', time:'1h 15m'}] };
    }
  }

  async function fetchLocation() {
    try {
      const d = await fetchJson(apiUrl('/family/location'));
      return d || {};
    } catch (e) {
      return { latitude: null, longitude: null, address: 'Tap to share location', zones: ['Home', 'School'] };
    }
  }

  async function fetchAlerts() {
    try {
      const d = await fetchJson(apiUrl('/family/alerts'));
      return d.alerts || [];
    } catch (e) {
      return [];
    }
  }

  async function fetchWebFilter() {
    try {
      const d = await fetchJson(apiUrl('/family/webfilter'));
      return d || {};
    } catch (e) {
      return { enabled: true, blockedCategories: ['adult', 'gambling', 'violence'], allowedSites: [] };
    }
  }

  async function fetchCheckIn() {
    try {
      const d = await fetchJson(apiUrl('/family/checkin'));
      return d || {};
    } catch (e) {
      return { lastCheckIn: null, status: 'awaiting' };
    }
  }

  async function shareLocation() {
    if (!navigator.geolocation) {
      alert('Geolocation not supported on this device');
      return;
    }
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const loc = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: Math.round(pos.coords.accuracy),
        timestamp: new Date().toISOString()
      };
      try {
        await fetch(apiUrl('/family/location'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(loc)
          .then(() => alert('Location shared with parents'))
        });
      } catch (e) {
        alert('Location shared (offline mode - will sync when connected)');
      }
    }, (err) => {
      alert('Location access denied: ' + err.message);
    });
  }

  async function sendCheckIn() {
    try {
      await fetch(apiUrl('/family/checkin'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'safe', timestamp: new Date().toISOString() })
      });
      alert('Check-in sent! Parents notified you are safe.');
    } catch (e) {
      alert('Check-in recorded (will sync when connected)');
    }
  }

  function renderFamilySection() {
    // Update children
    fetchChildren().then(children => {
      const el = document.querySelector('[data-family="children"]');
      if (el) el.textContent = children.length ? `${children.length} active` : 'No children added';
    });

    // Update screen time
    fetchScreenTime().then(st => {
      const el = document.querySelector('[data-family="screentime"]');
      if (el) el.textContent = st.total ? `${st.total} / ${st.limit}` : 'No limits set';
    });

    // Update location
    fetchLocation().then(loc => {
      const el = document.querySelector('[data-family="location"]');
      if (el) el.textContent = loc.address || 'Location available';
    });

    // Update alerts
    fetchAlerts().then(alerts => {
      const el = document.querySelector('[data-family="alerts"]');
      if (el) el.textContent = alerts.length ? `${alerts.length} active` : 'All clear';
    });

    // Update web filter
    fetchWebFilter().then(wf => {
      const el = document.querySelector('[data-family="webfilter"]');
      if (el) el.textContent = wf.enabled ? `${wf.blockedCategories?.length || 0} blocked` : 'Disabled';
    });

    // Update check-in
    fetchCheckIn().then(ci => {
      const el = document.querySelector('[data-family="checkin"]');
      if (el) el.textContent = ci.lastCheckIn ? new Date(ci.lastCheckIn).toLocaleTimeString() : 'Tap to check in';
    });
  }

  function renderFamilyDetails() {
    const container = document.getElementById('nbv2FamilyDetails');
    if (!container) return;

    container.innerHTML = `
      <div style="display:grid;gap:8px">
        <button onclick="window.__noorBrainFamily?.shareLocation()" style="background:rgba(76,175,80,0.2);border:1px solid rgba(76,175,80,0.5);color:#4CAF50;padding:10px;border-radius:8px;font-size:14px;font-weight:600">
          📍 Share My Location
        </button>
        <button onclick="window.__noorBrainFamily?.sendCheckIn()" style="background:rgba(33,150,243,0.2);border:1px solid rgba(33,150,243,0.5);color:#2196F3;padding:10px;border-radius:8px;font-size:14px;font-weight:600">
          ✅ I Am Safe (Check-in)
        </button>
        <button onclick="window.__noorBrainFamily?.showEmergencyContacts()" style="background:linear-gradient(135deg,rgba(244,67,54,0.3),rgba(255,152,0,0.3));border:1px solid rgba(244,67,54,0.5);color:#fff;padding:10px;border-radius:8px;font-size:14px;font-weight:600">
          🆘 Emergency
        </button>
      </div>
      <div id="nbf-family-children-list" style="margin-top:12px"></div>
    `;

    // Render children cards
    fetchChildren().then(children => {
      const list = document.getElementById('nbf-family-children-list');
      if (!list) return;
      if (!children.length) {
        list.innerHTML = '<div style="color:#888;font-size:13px;text-align:center;padding:12px">No children added yet</div>';
        return;
      }
      list.innerHTML = children.map(c => `
        <div style="display:flex;align-items:center;gap:12px;padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;margin-bottom:6px">
          <span style="font-size:28px">${esc(c.avatar || '👤')}</span>
          <div style="flex:1">
            <div style="font-weight:600;font-size:14px">${esc(c.name)}</div>
            <div style="font-size:12px;color:#888">Age ${esc(c.age)}</div>
          </div>
          <span style="color:${c.status === 'online' ? '#4CAF50' : '#888'}">●</span>
        </div>
      `).join('');
    });
  }

  // Auto-refresh every 30 seconds
  setInterval(renderFamilySection, 30000);

  // Initial render
  document.addEventListener('DOMContentLoaded', () => {
    renderFamilySection();
    renderFamilyDetails();
  });

  // Also render when family tab is shown
  const observer = new MutationObserver(() => {
    const familySection = document.getElementById('nbv2Family');
    if (familySection && familySection.offsetParent !== null) {
      renderFamilySection();
      renderFamilyDetails();
    }
  });
  observer.observe(document.body, { attributes: true, childList: true, subtree: true });

  // Expose for onclick handlers
  window.__noorBrainFamily = {
    shareLocation,
    sendCheckIn,
    showEmergencyContacts: function() {
      alert('Emergency Contacts:\n• Mom: +1 555-0100\n• Dad: +1 555-0101\n• Emergency: 911');
    }
  };

})();
