/**
 * TaniClaw Dashboard — app.js
 * Handles all UI interactions and API calls.
 */

const API = '';

// ── Utility ─────────────────────────────────────────────────────────────────

function plantEmoji(type) {
    const map = { chili: '🌶️', tomato: '🍅', spinach: '🥬', lettuce: '🥗', hydroponic: '💧' };
    return map[type] || '🌱';
}

function stateLabel(state) {
    const map = {
        seed: 'Benih', germination: 'Berkecambah', vegetative: 'Vegetatif',
        flowering: 'Berbunga', harvest: 'Panen', dormant: 'Dorman', dead: 'Tidak Aktif',
    };
    return map[state] || state;
}

function actionEmoji(type) {
    const map = {
        water: '💧', skip_water: '⏭️', fertilize: '🌿', harvest: '🌾',
        notify: '🔔', alert: '⚠️', log: '📝',
    };
    return map[type] || '•';
}

function iconClass(type) {
    const map = {
        water: 'icon-water', fertilize: 'icon-fertilize', harvest: 'icon-harvest',
        alert: 'icon-alert', notify: 'icon-notify', skip_water: 'icon-skip', log: 'icon-log',
    };
    return map[type] || 'icon-log';
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'Baru saja';
    if (diff < 3600) return `${Math.floor(diff / 60)} menit lalu`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} jam lalu`;
    return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
}

function toast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    c.appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

// ── Navigation ───────────────────────────────────────────────────────────────

document.querySelectorAll('.nav-item[data-page]').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        navigate(page);
    });
});

function navigate(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(`page-${page}`)?.classList.add('active');
    document.getElementById(`nav-${page}`)?.classList.add('active');

    const titles = {
        dashboard: '📊 Dashboard',
        plants: '🌿 Tanaman Saya',
        history: '📋 Riwayat',
    };
    document.getElementById('page-title').textContent = titles[page] || page;

    if (page === 'plants') loadAllPlants();
    if (page === 'history') loadHistory();
}

// ── State ────────────────────────────────────────────────────────────────────

let selectedPlantId = null;
let plants = [];
let summary = null;

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadDashboard() {
    await Promise.all([loadStats(), loadPlantCards()]);
}

async function loadStats() {
    try {
        const res = await fetch(`${API}/api/farm/summary`);
        summary = await res.json();

        document.getElementById('stat-active').textContent = summary.plants_count ?? '–';
        document.getElementById('stat-actions').textContent = summary.total_actions ?? '–';
        document.getElementById('stat-alerts').textContent = summary.alerts?.length ?? '0';

        // Weather from first plant if available
        if (summary.instructions?.length || summary.alerts?.length) {
            renderTodayInstructions(summary.instructions, summary.alerts);
        } else {
            renderTodayInstructions([], []);
        }
    } catch (e) {
        console.warn('Stats load failed:', e);
    }
}

async function loadFirstPlantWeather() {
    const active = plants.filter(p => p.is_active);
    if (!active.length) return;
    try {
        const res = await fetch(`${API}/api/weather/${active[0].id}`);
        const w = await res.json();
        document.getElementById('stat-temp').textContent = `${Math.round(w.temp_max ?? 28)}°C`;
    } catch (e) { }
}

async function loadPlantCards() {
    try {
        const res = await fetch(`${API}/api/plants?active_only=true`);
        plants = await res.json();
        renderPlantCards(plants, 'plants-grid');
        loadFirstPlantWeather();
    } catch (e) {
        document.getElementById('plants-grid').innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">Gagal memuat tanaman</div></div>';
    }
}

async function loadAllPlants() {
    const showAll = document.getElementById('show-all-plants').checked;
    try {
        const res = await fetch(`${API}/api/plants?active_only=${!showAll}`);
        const all = await res.json();
        renderPlantCards(all, 'plants-grid-full');
    } catch (e) {
        toast('Gagal memuat tanaman', 'error');
    }
}

document.getElementById('show-all-plants')?.addEventListener('change', loadAllPlants);

async function loadHistory() {
    const timeline = document.getElementById('history-timeline');
    timeline.innerHTML = '<div class="empty-state"><div class="spinner"></div></div>';
    try {
        const res = await fetch(`${API}/api/farm/history?limit=50`);
        const history = await res.json();
        if (!history.length) {
            timeline.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-title">Belum ada riwayat</div></div>';
            return;
        }
        timeline.innerHTML = history.map(h => {
            const dotClass = h.event_type.includes('alert') ? 'alert' : (h.event_type === 'state_change' ? 'state_change' : '');
            const plantName = plants.find(p => p.id === h.plant_id)?.name || h.plant_id?.substring(0, 8);
            return `
        <div class="timeline-item">
          <div class="timeline-dot ${dotClass}"></div>
          <div class="timeline-content">
            <div style="font-size:13px;font-weight:600;color:var(--slate-700)">${h.event_type.replace(/_/g, ' ')}</div>
            <div style="font-size:12px;color:var(--slate-500);margin-top:2px;">${plantName ? `🌱 ${plantName}` : ''} — ${h.event_data?.description || h.event_data?.message || JSON.stringify(h.event_data).substring(0, 80)}</div>
            <div class="timeline-time">${timeAgo(h.created_at)}</div>
          </div>
        </div>
      `;
        }).join('');
    } catch (e) {
        timeline.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">Gagal memuat riwayat</div></div>';
    }
}

// ── Rendering ─────────────────────────────────────────────────────────────────

const STAGE_ORDER = ['seed', 'germination', 'vegetative', 'flowering', 'harvest'];

function renderPlantCards(plantList, containerId) {
    const grid = document.getElementById(containerId);
    if (!plantList.length) {
        grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon">🌱</div>
        <div class="empty-state-title">Belum ada tanaman</div>
        <div class="empty-state-text">Klik "+ Tambah Tanaman" untuk mulai memantau tanaman pertama Anda.</div>
      </div>
    `;
        return;
    }

    grid.innerHTML = plantList.map(p => {
        const emoji = plantEmoji(p.plant_type);
        const stageIdx = STAGE_ORDER.indexOf(p.current_state);
        const stageDots = STAGE_ORDER.map((s, i) => {
            const cls = i < stageIdx ? 'done' : i === stageIdx ? 'current' : '';
            return `<div class="stage-dot ${cls}"></div>`;
        }).join('');

        return `
      <div class="plant-card animate-fade-up" onclick="openPlantDetail('${p.id}')">
        <div class="plant-card-emoji">${emoji}</div>
        <div class="plant-card-name">${p.name}</div>
        <div class="plant-card-type">${p.plant_type} • ${p.growing_method || 'soil'}</div>
        <div>
          <span class="plant-card-state badge-${p.current_state}">
            ${stateLabel(p.current_state)}
          </span>
        </div>
        <div class="plant-card-days">📅 Hari ke-${p.days_since_planting}</div>
        <div class="lifecycle-progress">
          <div style="font-size:10px;color:var(--slate-400);margin-bottom:4px;">Progress</div>
          <div class="lifecycle-stages">${stageDots}</div>
        </div>
      </div>
    `;
    }).join('');
}

function renderTodayInstructions(instructions, alerts) {
    const list = document.getElementById('today-instructions');

    // Show alerts first
    const alertsContainer = document.getElementById('alerts-container');
    alertsContainer.innerHTML = alerts.map(a => `
    <div class="alert-banner">
      <div class="alert-banner-icon">⚠️</div>
      <div class="alert-banner-text">${a}</div>
    </div>
  `).join('');

    if (!instructions.length && !alerts.length) {
        list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">✅</div><div class="empty-state-title">Tidak ada tindakan khusus hari ini</div><div class="empty-state-text">Tambahkan tanaman hoặc jalankan siklus agen untuk melihat instruksi.</div></div>';
        return;
    }

    list.innerHTML = instructions.map((instr, i) => {
        const type = guessActionType(instr);
        return `
      <li class="instruction-item" style="animation-delay:${i * 60}ms">
        <div class="instruction-icon ${iconClass(type)}">${actionEmoji(type)}</div>
        <div class="instruction-text">${instr}</div>
      </li>
    `;
    }).join('');
}

function guessActionType(text) {
    const t = text.toLowerCase();
    if (t.includes('siram') || t.includes('water')) return 'water';
    if (t.includes('pupuk') || t.includes('fertilize')) return 'fertilize';
    if (t.includes('panen') || t.includes('harvest')) return 'harvest';
    if (t.includes('peringatan') || t.includes('alert')) return 'alert';
    if (t.includes('lewati') || t.includes('skip')) return 'skip_water';
    return 'log';
}

// ── Plant Detail Panel ────────────────────────────────────────────────────────

async function openPlantDetail(plantId) {
    selectedPlantId = plantId;
    const panel = document.getElementById('detail-panel');
    panel.classList.add('open');

    const plant = plants.find(p => p.id === plantId);
    if (plant) {
        document.getElementById('detail-name').textContent = `${plantEmoji(plant.plant_type)} ${plant.name}`;
        document.getElementById('detail-type').textContent = `${plant.plant_type} • ${plant.location}`;
    }

    document.getElementById('detail-body').innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';
    document.getElementById('btn-trigger-plant').onclick = () => triggerPlantCycle(plantId);
    document.getElementById('btn-deactivate-plant').onclick = () => deactivatePlant(plantId);

    try {
        const [instRes, weatherRes, actRes] = await Promise.all([
            fetch(`${API}/api/plants/${plantId}/instructions`),
            fetch(`${API}/api/weather/${plantId}`),
            fetch(`${API}/api/actions/${plantId}?limit=10`),
        ]);

        const instr = await instRes.json();
        const weather = await weatherRes.json();
        const actions = await actRes.json();

        document.getElementById('detail-body').innerHTML = renderDetailBody(instr, weather, actions);
    } catch (e) {
        document.getElementById('detail-body').innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-title">Gagal memuat detail</div></div>';
    }
}

function renderDetailBody(instr, weather, actions) {
    const instructionItems = (instr.instructions || []).map(i => {
        const type = guessActionType(i);
        return `<li class="instruction-item"><div class="instruction-icon ${iconClass(type)}">${actionEmoji(type)}</div><div class="instruction-text">${i}</div></li>`;
    }).join('');

    const alertItems = (instr.alerts || []).map(a => `<div class="alert-banner"><div class="alert-banner-icon">⚠️</div><div class="alert-banner-text">${a}</div></div>`).join('');

    const actionRows = (actions || []).slice(0, 5).map(a => `
    <div style="display:flex;gap:8px;align-items:center;padding:8px 0;border-bottom:1px solid var(--slate-100);font-size:13px;">
      <span>${actionEmoji(a.action_type)}</span>
      <span style="flex:1;color:var(--slate-600)">${a.description.substring(0, 70)}${a.description.length > 70 ? '…' : ''}</span>
      <span style="color:var(--slate-400);font-size:11px">${timeAgo(a.created_at)}</span>
    </div>
  `).join('');

    return `
    ${alertItems}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">
      <div style="background:var(--green-50);border-radius:8px;padding:12px;text-align:center;">
        <div style="font-size:22px;font-weight:800;color:var(--green-700)">${instr.days_since_planting}</div>
        <div style="font-size:11px;color:var(--slate-500);font-weight:500">Hari Sejak Tanam</div>
      </div>
      <div style="background:var(--amber-100);border-radius:8px;padding:12px;text-align:center;">
        <div style="font-size:22px;font-weight:800;color:var(--amber-600)">${instr.days_in_state}</div>
        <div style="font-size:11px;color:var(--slate-500);font-weight:500">Hari di ${stateLabel(instr.plant_state)}</div>
      </div>
    </div>
    ${weather ? `
    <div style="margin-bottom:16px;">
      <div style="font-size:13px;font-weight:600;color:var(--slate-600);margin-bottom:8px;">🌤️ Cuaca Hari Ini</div>
      <div class="weather-grid">
        <div class="weather-item"><div class="weather-value">${Math.round(weather.temp_max ?? 28)}°C</div><div class="weather-label">Suhu Maks</div></div>
        <div class="weather-item"><div class="weather-value">${Math.round(weather.humidity ?? 70)}%</div><div class="weather-label">Kelembaban</div></div>
        <div class="weather-item"><div class="weather-value">${weather.rainfall_mm ?? 0}mm</div><div class="weather-label">Curah Hujan</div></div>
        <div class="weather-item"><div class="weather-value">${Math.round(weather.temp_min ?? 22)}°C</div><div class="weather-label">Suhu Min</div></div>
      </div>
      <div style="background:var(--slate-50);border-radius:8px;padding:10px;margin-top:8px;font-size:12px;color:var(--slate-600)">${weather.forecast_summary}</div>
    </div>` : ''}
    <div style="margin-bottom:16px;">
      <div style="font-size:13px;font-weight:600;color:var(--slate-600);margin-bottom:8px;">📌 Instruksi Hari Ini</div>
      <ul class="instruction-list">${instructionItems || '<li class="instruction-item"><div class="instruction-text">Tidak ada instruksi khusus hari ini.</div></li>'}</ul>
    </div>
    ${actions?.length ? `
    <div style="margin-bottom:16px;">
      <div style="font-size:13px;font-weight:600;color:var(--slate-600);margin-bottom:8px;">🕐 Aktivitas Terakhir</div>
      ${actionRows}
    </div>` : ''}
    <div style="margin-top:16px;">
      <button class="btn btn-primary" style="width:100%" onclick="openChatForPlant('${instr.plant_id}')">
        💬 Chat tentang ${instr.plant_name}
      </button>
    </div>
  `;
}

function closeDetail() {
    document.getElementById('detail-panel').classList.remove('open');
    selectedPlantId = null;
}

function openChatForPlant(plantId) {
    window.open(`/chat`, '_blank');
}

// ── Actions ───────────────────────────────────────────────────────────────────

async function triggerPlantCycle(plantId) {
    const btn = document.getElementById('btn-trigger-plant');
    btn.disabled = true;
    btn.textContent = '⏳ Memproses...';
    try {
        await fetch(`${API}/api/actions/${plantId}/trigger`, { method: 'POST' });
        toast('Siklus agen berhasil dijalankan!', 'success');
        setTimeout(() => openPlantDetail(plantId), 800);
    } catch (e) {
        toast('Gagal menjalankan siklus', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '▶️ Jalankan';
    }
}

async function deactivatePlant(plantId) {
    if (!confirm('Nonaktifkan tanaman ini?')) return;
    try {
        await fetch(`${API}/api/plants/${plantId}`, { method: 'DELETE' });
        toast('Tanaman dinonaktifkan', 'success');
        closeDetail();
        loadDashboard();
    } catch (e) {
        toast('Gagal menonaktifkan tanaman', 'error');
    }
}

document.getElementById('btn-run-cycle')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-run-cycle');
    btn.disabled = true;
    btn.textContent = '⏳ Memproses...';
    try {
        const active = plants.filter(p => p.is_active);
        if (!active.length) { toast('Tidak ada tanaman aktif', 'error'); return; }
        for (const p of active) {
            await fetch(`${API}/api/actions/${p.id}/trigger`, { method: 'POST' });
        }
        toast('Siklus selesai!', 'success');
        loadDashboard();
    } catch (e) {
        toast('Gagal menjalankan siklus', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '▶️ Jalankan Siklus';
    }
});

// ── Add Plant Modal ───────────────────────────────────────────────────────────

function openAddPlantModal() {
    document.getElementById('add-plant-modal').classList.add('open');
    // Set default date to today
    document.getElementById('input-date').value = new Date().toISOString().split('T')[0];
}

function closeAddPlantModal() {
    document.getElementById('add-plant-modal').classList.remove('open');
    document.getElementById('add-plant-form').reset();
}

function detectLocation() {
    if (!navigator.geolocation) { toast('Geolokasi tidak didukung', 'error'); return; }
    toast('Mendeteksi lokasi...');
    navigator.geolocation.getCurrentPosition(pos => {
        document.getElementById('input-lat').value = pos.coords.latitude.toFixed(4);
        document.getElementById('input-lon').value = pos.coords.longitude.toFixed(4);
        toast('Lokasi terdeteksi!', 'success');
    }, () => toast('Gagal mendapatkan lokasi', 'error'));
}

async function submitPlant() {
    const btn = document.getElementById('btn-submit-plant');
    const name = document.getElementById('input-name').value.trim();
    const type = document.getElementById('input-type').value;
    const date = document.getElementById('input-date').value;
    const location = document.getElementById('input-location').value.trim();
    const lat = parseFloat(document.getElementById('input-lat').value);
    const lon = parseFloat(document.getElementById('input-lon').value);
    const method = document.getElementById('input-method').value;
    const soil = document.getElementById('input-soil').value;
    const notes = document.getElementById('input-notes').value.trim();

    if (!name || !type || !date || !location || isNaN(lat) || isNaN(lon)) {
        toast('Lengkapi semua field yang wajib diisi', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ Menyimpan...';

    try {
        const res = await fetch(`${API}/api/plants`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name, plant_type: type, plant_date: date,
                location, latitude: lat, longitude: lon,
                growing_method: method, soil_condition: soil,
                notes: notes || null,
            }),
        });
        if (!res.ok) {
            const err = await res.json();
            toast(err.detail || 'Gagal menambahkan tanaman', 'error');
            return;
        }
        toast(`${name} berhasil ditambahkan! 🌱`, 'success');
        closeAddPlantModal();
        loadDashboard();
    } catch (e) {
        toast('Gagal terhubung ke server', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🌱 Tambah Tanaman';
    }
}

// ── Refresh button ────────────────────────────────────────────────────────────

document.getElementById('btn-refresh')?.addEventListener('click', () => {
    loadDashboard();
    toast('Data diperbarui!', 'success');
});

// ── Close panel on outside click ──────────────────────────────────────────────

document.addEventListener('click', (e) => {
    const panel = document.getElementById('detail-panel');
    if (panel.classList.contains('open') && !panel.contains(e.target) && !e.target.closest('.plant-card')) {
        closeDetail();
    }
    const modal = document.getElementById('add-plant-modal');
    if (modal.classList.contains('open') && e.target === modal) {
        closeAddPlantModal();
    }
});

// ── Init ──────────────────────────────────────────────────────────────────────

loadDashboard();
