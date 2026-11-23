/* Controlador principal da UI — Ghost Tactical Pad */
(() => {
  const $ = (id) => document.getElementById(id);

  const STATE = {
    prefs: {},
    lang: "pt-BR",
    langSetting: "auto",
    mapData: null,
    catalog: null,
    cartel: null,
    progress: { collected_items: [], completed_pois: [], discovered_provinces: [], defeated_bosses: [] },
    live: null,
    markers: [],
    demoOn: false,
    lastRiskBeepAt: 0,
    audioCtx: null,
  };

  let mapCtrl = null;
  let saveTimer = null;

  function scheduleSavePrefs(immediate) {
    try {
      localStorage.setItem("ghostpad_prefs_v1", JSON.stringify(STATE.prefs));
    } catch {}
    if (saveTimer) clearTimeout(saveTimer);
    if (immediate) {
      fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ui_prefs: STATE.prefs }),
      }).catch(() => {});
    } else {
      saveTimer = setTimeout(() => {
        fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ui_prefs: STATE.prefs }),
        }).catch(() => {});
      }, 280);
    }
  }

  window.addEventListener("pagehide", () => {
    try {
      const blob = new Blob([JSON.stringify({ ui_prefs: STATE.prefs })], { type: "application/json" });
      navigator.sendBeacon("/api/settings", blob);
    } catch {}
  });

  function playRiskBeep(isCritical) {
    if (!STATE.prefs.alertSound) return;
    const now = performance.now();
    if (now - STATE.lastRiskBeepAt < 1800) return;
    STATE.lastRiskBeepAt = now;
    try {
      if (!STATE.audioCtx) STATE.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const ctx = STATE.audioCtx;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = isCritical ? 880 : 620;
      gain.gain.setValueAtTime(0.05, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.16);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.17);
    } catch {}
  }

  function applyPrefsToControls() {
    const p = STATE.prefs;
    // Tabs
    const activeTab = p.activeTab || "map";
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === activeTab));
    document.querySelectorAll(".tab-view").forEach((v) => v.classList.toggle("active", v.id === `view-${activeTab}`));

    // Sidebar collapse
    $("map-sidebar").classList.toggle("collapsed", Boolean(p.sidebarCollapsed));

    // Mode & Style segmented
    document.querySelectorAll("#map-mode-seg .mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === (p.mapMode || "assist")));
    $("assist-controls").classList.toggle("hidden", (p.mapMode || "assist") !== "assist");
    $("rng-assist-radius").value = p.assistRadius || 350;
    $("assist-radius-val").textContent = `${p.assistRadius || 350} m`;

    document.querySelectorAll("#map-style-seg .mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.style === (p.mapStyle || "satellite")));

    // Checkboxes vinculados via data-pref
    document.querySelectorAll("input[type=checkbox][data-pref]").forEach((chk) => {
      const k = chk.dataset.pref;
      if (k in p) chk.checked = Boolean(p[k]);
    });

    // Selects & sliders
    $("sel-weapon-override").value = p.weaponOverrideClass || "auto";
    $("sel-sup-override").value = p.weaponOverrideSuppressed || "auto";
    $("rng-vis-range").value = p.enemyVisionRangeM || 55;
    $("val-vis-range").textContent = `${p.enemyVisionRangeM || 55} m`;
    $("rng-fov-deg").value = p.enemyFovDeg || 110;
    $("val-fov-deg").textContent = `${p.enemyFovDeg || 110}°`;
    $("rng-impact-m").value = p.bulletImpactNoiseM !== undefined ? p.bulletImpactNoiseM : 12;
    $("val-impact-m").textContent = `${$("rng-impact-m").value} m`;

    if (mapCtrl) {
      mapCtrl.setPrefs(p);
    }
  }

  function bindAllControls() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        STATE.prefs.activeTab = btn.dataset.tab;
        applyPrefsToControls();
        scheduleSavePrefs();
      });
    });

    $("btn-toggle-sidebar").addEventListener("click", () => {
      STATE.prefs.sidebarCollapsed = !STATE.prefs.sidebarCollapsed;
      applyPrefsToControls();
      scheduleSavePrefs();
      setTimeout(() => mapCtrl && mapCtrl._resize(), 30);
    });

    document.querySelectorAll("#map-mode-seg .mode-btn").forEach((b) => {
      b.addEventListener("click", () => {
        STATE.prefs.mapMode = b.dataset.mode;
        applyPrefsToControls();
        scheduleSavePrefs(true);
      });
    });

    document.querySelectorAll("#map-style-seg .mode-btn").forEach((b) => {
      b.addEventListener("click", () => {
        STATE.prefs.mapStyle = b.dataset.style;
        applyPrefsToControls();
        scheduleSavePrefs();
      });
    });

    $("rng-assist-radius").addEventListener("input", (e) => {
      STATE.prefs.assistRadius = Number(e.target.value);
      $("assist-radius-val").textContent = `${STATE.prefs.assistRadius} m`;
      mapCtrl && mapCtrl.setPrefs(STATE.prefs);
      scheduleSavePrefs();
    });

    document.querySelectorAll("input[type=checkbox][data-pref]").forEach((chk) => {
      chk.addEventListener("change", () => {
        STATE.prefs[chk.dataset.pref] = chk.checked;
        applyPrefsToControls();
        scheduleSavePrefs(true);
      });
    });

    $("sel-weapon-override").addEventListener("change", (e) => {
      STATE.prefs.weaponOverrideClass = e.target.value;
      scheduleSavePrefs(true);
    });
    $("sel-sup-override").addEventListener("change", (e) => {
      STATE.prefs.weaponOverrideSuppressed = e.target.value;
      scheduleSavePrefs(true);
    });
    $("rng-vis-range").addEventListener("input", (e) => {
      STATE.prefs.enemyVisionRangeM = Number(e.target.value);
      $("val-vis-range").textContent = `${STATE.prefs.enemyVisionRangeM} m`;
      mapCtrl && mapCtrl.setPrefs(STATE.prefs);
      scheduleSavePrefs();
    });
    $("rng-fov-deg").addEventListener("input", (e) => {
      STATE.prefs.enemyFovDeg = Number(e.target.value);
      $("val-fov-deg").textContent = `${STATE.prefs.enemyFovDeg}°`;
      mapCtrl && mapCtrl.setPrefs(STATE.prefs);
      scheduleSavePrefs();
    });
    $("rng-impact-m").addEventListener("input", (e) => {
      STATE.prefs.bulletImpactNoiseM = Number(e.target.value);
      $("val-impact-m").textContent = `${STATE.prefs.bulletImpactNoiseM} m`;
      scheduleSavePrefs();
    });

    $("btn-tactical-presets").addEventListener("click", () => {
      Object.assign(STATE.prefs, {
        showEnemies: true,
        showEnemyDirection: true,
        showEnemyVisionCones: true,
        showEnemyHearingRings: false,
        showWeaponNoiseRing: true,
        showSafeToFireHud: true,
        showPlayerAimWarning: true,
        showAlliesSolo: true,
        showAlliesCoop: true,
        showAllyAimWarning: true,
        showAllySightlines: true,
        showKillWitnessLines: true,
        showDrone: true,
        useTerrainLos: true,
        enemyVisionRangeM: 55,
        enemyFovDeg: 110,
        bulletImpactNoiseM: 12,
        weaponOverrideClass: "auto",
        weaponOverrideSuppressed: "auto",
      });
      applyPrefsToControls();
      scheduleSavePrefs(true);
    });

    $("btn-recenter").addEventListener("click", () => {
      STATE.prefs.followPlayer = true;
      applyPrefsToControls();
      mapCtrl && mapCtrl.recenterOnPlayer();
      scheduleSavePrefs();
    });
    $("btn-zoom-in").addEventListener("click", () => mapCtrl && mapCtrl.zoomBy(1.35));
    $("btn-zoom-out").addEventListener("click", () => mapCtrl && mapCtrl.zoomBy(1 / 1.35));

    window.addEventListener("keydown", (e) => {
      if (e.code === "Space" && document.activeElement.tagName !== "INPUT") {
        e.preventDefault();
        mapCtrl && mapCtrl.recenterOnPlayer();
      }
    });

    $("btn-cat-all").addEventListener("click", () => {
      STATE.prefs.enabledCats = null;
      renderCategoryList();
      applyPrefsToControls();
      scheduleSavePrefs();
    });
    $("btn-cat-none").addEventListener("click", () => {
      STATE.prefs.enabledCats = [];
      renderCategoryList();
      applyPrefsToControls();
      scheduleSavePrefs();
    });

    $("map-search").addEventListener("input", renderMapSearch);
    $("btn-new-marker").addEventListener("click", () => openMarkerEditor(mapCtrl.camU, mapCtrl.camV));
    $("btn-nearby").addEventListener("click", () => {
      $("map-nearby").classList.toggle("hidden");
      renderNearbyDrawer();
    });
    $("btn-sim-demo").addEventListener("click", toggleDemoSimulation);

    // Wiki controls
    document.querySelectorAll("#wiki-cats .pill").forEach((b) => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#wiki-cats .pill").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        STATE.prefs.wikiCat = b.dataset.wcat;
        renderWikiGrid();
        scheduleSavePrefs();
      });
    });
    $("wiki-class-filter").addEventListener("change", (e) => {
      STATE.prefs.wikiClassFilter = e.target.value;
      renderWikiGrid();
      scheduleSavePrefs();
    });
    $("chk-wiki-missing").addEventListener("change", (e) => {
      STATE.prefs.wikiMissingOnly = e.target.checked;
      renderWikiGrid();
      scheduleSavePrefs();
    });
    $("wiki-search").addEventListener("input", renderWikiGrid);

    // Cartel controls
    document.querySelectorAll("#cartel-wings .pill").forEach((b) => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#cartel-wings .pill").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        STATE.prefs.cartelWingFilter = b.dataset.wing;
        renderCartelGrid();
        scheduleSavePrefs();
      });
    });

    // Settings Modal
    $("btn-settings").addEventListener("click", openSettingsModal);
    $("btn-close-settings").addEventListener("click", () => $("settings-modal").classList.add("hidden"));
    $("sel-lang").addEventListener("change", async (e) => {
      const resp = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lang: e.target.value }),
      });
      const res = await resp.json();
      GhostI18n.setLang(res.lang);
      await loadStaticCaches();
      renderAll();
    });
    $("btn-rebuild-cache").addEventListener("click", async () => {
      await fetch("/api/rebuild", { method: "POST" });
      $("settings-modal").classList.add("hidden");
      waitForBuildReady();
    });
  }

  async function toggleDemoSimulation() {
    STATE.demoOn = !STATE.demoOn;
    $("btn-sim-demo").classList.toggle("active", STATE.demoOn);
    if (!STATE.demoOn) {
      await fetch("/api/debug/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: false }) });
      return;
    }
    // Cena tática realista em Itacua demonstrando: arma equipada + mira do jogador + aliado Solo AI + aliado Co-op + cones FOV + testemunhas!
    const demo = {
      enabled: true,
      mode: "live",
      status: "demo",
      player: {
        id: "player", type: "player", name: "Nomad",
        x: 420.0, y: -2520.0, z: 120.0, u: 0.520, v: 0.620,
        head: [420.0, -2520.0, 121.6],
        aim_origin: [420.0, -2520.0, 121.6],
        aim_dir: [0.0, 1.0, 0.0],
        yaw: 0.0, vfov: 0.49, is_aiming: true,
        weapon_class: "ar", suppressed: true, stance: "crouch",
      },
      drone: { x: 445.0, y: -2490.0, z: 150.0, u: 0.5212, v: 0.6186, yaw: 35.0, dist_m: 47.0 },
      allies: [
        {
          id: "ai_holt", type: "ai", name: "Holt",
          x: 385.0, y: -2485.0, z: 120.0, u: 0.5183, v: 0.6183,
          head: [385.0, -2485.0, 121.6],
          aim_dir: [0.6247, 0.7809, 0.0], yaw: 38.6, is_aiming: true, weapon_class: "ar", suppressed: true,
        },
        {
          id: "coop_1", type: "coop", name: "Co-op Ghost 1",
          x: 455.0, y: -2500.0, z: 120.0, u: 0.5217, v: 0.6190,
          head: [455.0, -2500.0, 121.6],
          aim_dir: [-0.287, 0.958, 0.0], yaw: 343.3, is_aiming: true, weapon_class: "sniper", suppressed: false,
        },
      ],
      enemies: [
        { id: "sb_1", faction: "santa_blanca", x: 420.0, y: -2440.0, z: 120.0, u: 0.5200, v: 0.6162, head: [420.0, -2440.0, 121.6], look_dir: [0.0, -1.0, 0.0], yaw: 180.0, alert: "unaware", alive: true },
        { id: "sb_2", faction: "santa_blanca", x: 446.0, y: -2440.0, z: 120.0, u: 0.5212, v: 0.6162, head: [446.0, -2440.0, 121.6], look_dir: [-1.0, 0.0, 0.0], yaw: 270.0, alert: "unaware", alive: true },
        { id: "sb_3", faction: "unidad", x: 420.0, y: -2492.0, z: 120.0, u: 0.5200, v: 0.6187, head: [420.0, -2492.0, 121.6], look_dir: [0.7, 0.7, 0.0], yaw: 45.0, alert: "suspected", alive: true },
        { id: "sb_4", faction: "santa_blanca", x: 375.0, y: -2445.0, z: 120.0, u: 0.5179, v: 0.6164, head: [375.0, -2445.0, 121.6], look_dir: [0.0, -1.0, 0.0], yaw: 180.0, alert: "unaware", alive: true },
      ],
      trail: [{ u: 0.5192, v: 0.622 }, { u: 0.5196, v: 0.621 }, { u: 0.5200, v: 0.620 }],
    };
    await fetch("/api/debug/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(demo) });
    mapCtrl && mapCtrl.focusUV(0.52, 0.618, 1.45);
  }

  function updateHudAndAlerts(live) {
    STATE.live = live;
    const pill = $("conn-pill");
    const mode = live.status === "demo" ? "demo" : (live.mode || "offline");
    pill.className = `conn-pill ${mode}`;
    pill.textContent = GhostI18n.t(`conn.${mode}`);

    const tac = live.tactical || {};
    const sf = tac.safe_fire || {};
    const safeEl = $("hud-safe-fire");
    if (STATE.prefs.showSafeToFireHud === false) {
      safeEl.classList.add("hidden");
    } else {
      safeEl.classList.remove("hidden");
      if (!live.player) {
        safeEl.className = "safe-pill safe";
        $("hud-safe-icon").textContent = "✔";
        $("hud-safe-text").textContent = GhostI18n.t("hud.safeUnknown");
      } else if (sf.safe) {
        safeEl.className = "safe-pill safe";
        $("hud-safe-icon").textContent = "✔";
        $("hud-safe-text").textContent = `${GhostI18n.t("hud.safeOk")} (${sf.hear_radius_m || 0}m)`;
      } else {
        safeEl.className = "safe-pill warn";
        $("hud-safe-icon").textContent = "🔊";
        $("hud-safe-text").textContent = `${GhostI18n.t("hud.safeWarn", { n: sf.listener_count })} (${sf.hear_radius_m}m)`;
      }
    }

    const wCls = (sf.weapon_class || (live.player && live.player.weapon_class) || "ar").toUpperCase();
    const supLabel = sf.suppressed === false ? "UNSUPP" : "SUPP";
    $("hud-weapon").textContent = `🔫 ${wCls} · ${supLabel} · ${sf.hear_radius_m || 34}m`;
    $("hud-squad").textContent = `👥 ${(tac.visible_allies || []).length} · 🎯 ${(live.enemies || []).length}`;
    if (live.player) {
      $("hud-coords").textContent = `X:${live.player.x.toFixed(0)} Y:${live.player.y.toFixed(0)} Z:${live.player.z.toFixed(0)}`;
    } else {
      $("hud-coords").textContent = "X: — Y: —";
    }

    // Floating Tactical Alert Cards (Player Aim + Ally Aim)
    const box = $("tactical-alerts");
    const cards = [];
    const buildCardHtml = (res, badgeCls, badgeText) => {
      const reasons = [];
      if (res.sound_witness_count > 0) {
        reasons.push(`<span class="reason-chip snd">${GhostI18n.t("alert.sound", { n: res.sound_witness_count, r: res.hear_radius_m })}</span>`);
      }
      if (res.visual_witness_count > 0) {
        reasons.push(`<span class="reason-chip vis">${GhostI18n.t("alert.visual", { n: res.visual_witness_count })}</span>`);
      }
      if (reasons.length === 0) {
        reasons.push(`<span class="reason-chip ok">${GhostI18n.t("alert.clean")}</span>`);
      }
      return `
        <div class="tac-card ${res.verdict}">
          <div class="tac-head">
            <span><span class="tac-badge ${badgeCls}">${badgeText}</span> ${res.shooter_name || ""} → ${res.target_faction.toUpperCase()} (${res.shot_dist_m}m)</span>
            <span class="mono">${res.weapon_class.toUpperCase()} ${res.suppressed ? "🔇" : "🔊"}</span>
          </div>
          <div class="tac-reasons">${reasons.join("")}</div>
        </div>
      `;
    };

    let hasRisk = false;
    let isCrit = false;
    if (tac.player_aim && STATE.prefs.showPlayerAimWarning !== false) {
      cards.push(buildCardHtml(tac.player_aim, "player", GhostI18n.t("alert.playerAim")));
      if (tac.player_aim.verdict !== "safe") hasRisk = true;
      if (tac.player_aim.verdict === "critical" || tac.player_aim.verdict === "visual_risk") isCrit = true;
    }
    if (Array.isArray(tac.ally_aims) && STATE.prefs.showAllyAimWarning !== false) {
      for (const aa of tac.ally_aims) {
        const isCoop = aa.shooter_type === "coop";
        cards.push(buildCardHtml(aa, isCoop ? "coop" : "ai", GhostI18n.t(isCoop ? "alert.allyCoopAim" : "alert.allyAiAim")));
        if (aa.verdict !== "safe") hasRisk = true;
        if (aa.verdict === "critical" || aa.verdict === "visual_risk") isCrit = true;
      }
    }
    box.innerHTML = cards.join("");
    if (hasRisk) playRiskBeep(isCrit);

    if (mapCtrl) mapCtrl.setLive(live);
    if (!$("map-nearby").classList.contains("hidden")) renderNearbyDrawer();
  }

  function renderCategoryList() {
    if (!STATE.mapData) return;
    const enabled = STATE.prefs.enabledCats ? new Set(STATE.prefs.enabledCats) : null;
    const counts = {};
    for (const poi of STATE.mapData.pois) counts[poi.cat] = (counts[poi.cat] || 0) + 1;
    const html = STATE.mapData.categories.map((c) => {
      const checked = !enabled || enabled.has(c.id);
      return `
        <label class="cat-item">
          <span class="cat-left">
            <input type="checkbox" class="chk-cat" data-cat="${c.id}" ${checked ? "checked" : ""} />
            <span class="cat-dot" style="background:${c.color}"></span>
            <span>${c.name}</span>
          </span>
          <span class="cat-count">${counts[c.id] || 0}</span>
        </label>
      `;
    }).join("");
    $("map-categories").innerHTML = html;
    $("map-categories").querySelectorAll(".chk-cat").forEach((chk) => {
      chk.addEventListener("change", () => {
        const allIds = STATE.mapData.categories.map((x) => x.id);
        let cur = STATE.prefs.enabledCats ? new Set(STATE.prefs.enabledCats) : new Set(allIds);
        if (chk.checked) cur.add(chk.dataset.cat);
        else cur.delete(chk.dataset.cat);
        STATE.prefs.enabledCats = cur.size === allIds.length ? null : Array.from(cur);
        mapCtrl && mapCtrl.setPrefs(STATE.prefs);
        scheduleSavePrefs();
      });
    });
  }

  function renderMapSearch() {
    const q = $("map-search").value.trim().toLowerCase();
    const box = $("map-search-results");
    if (!q || !STATE.mapData) {
      box.classList.add("hidden");
      return;
    }
    const hits = STATE.mapData.pois.filter((p) =>
      p.name.toLowerCase().includes(q) || (p.province_name || "").toLowerCase().includes(q) || (p.desc || "").toLowerCase().includes(q)
    ).slice(0, 25);
    box.classList.remove("hidden");
    box.innerHTML = hits.map((h) => `
      <div class="search-hit" data-id="${h.id}">
        <span>${h.name}</span>
        <span class="muted">${h.province_name}</span>
      </div>
    `).join("") || `<div class="search-hit muted">—</div>`;
    box.querySelectorAll(".search-hit[data-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const poi = STATE.mapData.pois.find((x) => x.id === el.dataset.id);
        if (poi) {
          STATE.prefs.followPlayer = false;
          applyPrefsToControls();
          mapCtrl.focusUV(poi.u, poi.v, 0.75);
          showPoiDetail(poi);
        }
      });
    });
  }

  function showPoiDetail(poi) {
    const box = $("map-detail");
    if (!poi) {
      box.classList.add("hidden");
      return;
    }
    const doneSet = new Set(STATE.progress.completed_pois || []);
    const itemSet = new Set(STATE.progress.collected_items || []);
    const isDone = doneSet.has(poi.id) || (poi.item_id && itemSet.has(poi.item_id));
    box.classList.remove("hidden");
    box.innerHTML = `
      <div class="modal-head">
        <h3>${poi.name}</h3>
        <button class="icon-btn" id="btn-close-detail">✕</button>
      </div>
      <div class="muted" style="margin-bottom:8px">${poi.province_name || ""}</div>
      <p>${poi.desc || ""}</p>
      <div style="display:flex;gap:8px;margin-top:10px">
        <button class="btn ${isDone ? "btn-green" : "btn-cyan"}" id="btn-toggle-poi-done">
          ${isDone ? "✔ " + GhostI18n.t("collected") : GhostI18n.t("markCollected")}
        </button>
      </div>
    `;
    $("btn-close-detail").onclick = () => box.classList.add("hidden");
    $("btn-toggle-poi-done").onclick = async () => {
      const body = poi.item_id ? { toggle_item: poi.item_id, toggle_poi: poi.id } : { toggle_poi: poi.id };
      const r = await fetch("/api/progress", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      STATE.progress = await r.json();
      mapCtrl.setProgress(STATE.progress);
      showPoiDetail(poi);
      renderWikiGrid();
    };
  }

  function openMarkerEditor(u, v, existing) {
    const box = $("map-detail");
    box.classList.remove("hidden");
    box.innerHTML = `
      <div class="modal-head">
        <h3>${existing ? existing.title : "+ Pino Tático"}</h3>
        <button class="icon-btn" id="btn-close-detail">✕</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">
        <input id="mk-title" class="search-input" value="${existing ? existing.title : "Ponto de Sniper"}" />
        <input id="mk-note" class="search-input" placeholder="Nota tática..." value="${existing ? (existing.note || "") : ""}" />
        <input id="mk-color" type="color" value="${existing ? existing.color : "#38bdf8"}" style="height:32px;background:none;border:none" />
        <div style="display:flex;gap:8px">
          <button id="mk-save" class="btn btn-cyan" style="flex:1">Salvar</button>
          ${existing ? `<button id="mk-del" class="btn" style="color:#fca5a5">Excluir</button>` : ""}
        </div>
      </div>
    `;
    $("btn-close-detail").onclick = () => box.classList.add("hidden");
    $("mk-save").onclick = async () => {
      const payload = { title: $("mk-title").value, note: $("mk-note").value, color: $("mk-color").value, u, v };
      const url = existing ? `/api/markers/${existing.id}` : "/api/markers";
      const method = existing ? "PUT" : "POST";
      await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      await loadMarkers();
      box.classList.add("hidden");
    };
    if (existing && $("mk-del")) {
      $("mk-del").onclick = async () => {
        await fetch(`/api/markers/${existing.id}`, { method: "DELETE" });
        await loadMarkers();
        box.classList.add("hidden");
      };
    }
  }

  function renderNearbyDrawer() {
    const box = $("map-nearby");
    if (box.classList.contains("hidden") || !STATE.mapData) return;
    const p = (STATE.live && STATE.live.player) || { u: mapCtrl.camU, v: mapCtrl.camV };
    const span = 21000;
    const rows = [];
    for (const en of ((STATE.live && STATE.live.enemies) || [])) {
      const d = Math.hypot((en.u - p.u) * span, (en.v - p.v) * span);
      rows.push({ kind: "enemy", name: `${en.faction.toUpperCase()} (${en.alert})`, dist: d, u: en.u, v: en.v });
    }
    for (const poi of STATE.mapData.pois) {
      const d = Math.hypot((poi.u - p.u) * span, (poi.v - p.v) * span);
      if (d <= Number(STATE.prefs.assistRadius || 350) * 2.5) {
        rows.push({ kind: "poi", name: poi.name, sub: poi.province_name, dist: d, u: poi.u, v: poi.v, poi });
      }
    }
    rows.sort((a, b) => a.dist - b.dist);
    box.innerHTML = `
      <div class="modal-head">
        <h3>📡 ${GhostI18n.t("toolbar.nearby")}</h3>
        <button class="icon-btn" id="btn-close-nearby">✕</button>
      </div>
      ${rows.slice(0, 20).map((r, i) => `
        <div class="nearby-item" data-idx="${i}">
          <div style="display:flex;justify-content:space-between">
            <strong>${r.name}</strong>
            <span class="accent">${Math.round(r.dist)} m</span>
          </div>
          ${r.sub ? `<div class="muted" style="font-size:11px">${r.sub}</div>` : ""}
        </div>
      `).join("") || `<div class="muted">—</div>`}
    `;
    $("btn-close-nearby").onclick = () => box.classList.add("hidden");
    box.querySelectorAll(".nearby-item").forEach((el) => {
      el.onclick = () => {
        const r = rows[Number(el.dataset.idx)];
        STATE.prefs.followPlayer = false;
        applyPrefsToControls();
        mapCtrl.focusUV(r.u, r.v, 0.9);
        if (r.poi) showPoiDetail(r.poi);
      };
    });
  }

  function renderWikiGrid() {
    if (!STATE.catalog) return;
    const cat = STATE.prefs.wikiCat || "all";
    const cls = STATE.prefs.wikiClassFilter || "all";
    const missingOnly = Boolean(STATE.prefs.wikiMissingOnly);
    const q = $("wiki-search").value.trim().toLowerCase();
    const done = new Set(STATE.progress.collected_items || []);

    let list = [
      ...STATE.catalog.weapons,
      ...STATE.catalog.attachments,
      ...STATE.catalog.medals,
    ];
    list = list.filter((it) => {
      if (cat !== "all" && it.kind !== cat) return false;
      if (cls !== "all") {
        if (it.kind === "weapon" && it.weapon_class !== cls) return false;
        if (it.kind === "attachment" && !(it.compatible_classes || []).includes(cls)) return false;
        if (it.kind === "medal") return false;
      }
      if (missingOnly && done.has(it.id)) return false;
      if (q) {
        const hay = `${it.name} ${it.province_name} ${it.location} ${it.desc || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    $("wiki-grid").innerHTML = list.map((it) => {
      const isDone = done.has(it.id);
      const badge = it.kind === "weapon" ? it.weapon_class.toUpperCase() : it.kind === "attachment" ? it.slot.toUpperCase() : "MEDAL";
      const acoustic = it.kind === "weapon" ? `<span class="muted">🔇 ${it.noise_suppressed_m}m · 🔊 ${it.noise_unsuppressed_m}m</span>` : "";
      return `
        <div class="item-card ${isDone ? "collected" : ""}" data-id="${it.id}">
          <div class="card-title-row">
            <span>${it.name}</span>
            <span class="tag">${badge}</span>
          </div>
          <div class="muted" style="font-size:11.5px">📍 ${it.province_name} — ${it.location}</div>
          ${acoustic}
        </div>
      `;
    }).join("");

    $("wiki-grid").querySelectorAll(".item-card").forEach((el) => {
      el.onclick = () => {
        const it = list.find((x) => x.id === el.dataset.id);
        if (it) showWikiDetail(it);
      };
    });
  }

  function showWikiDetail(it) {
    const done = new Set(STATE.progress.collected_items || []);
    const isDone = done.has(it.id);
    const panel = $("wiki-detail");
    panel.classList.remove("empty");

    let statsHtml = "";
    if (it.stats) {
      statsHtml = Object.entries(it.stats).map(([k, v]) => `
        <div class="stat-row">
          <span style="width:90px;text-transform:capitalize">${k}</span>
          <div class="stat-bar-bg"><div class="stat-bar-fill" style="width:${v}%"></div></div>
          <span class="mono" style="width:28px;text-align:right">${v}</span>
        </div>
      `).join("");
    }
    const acousticHtml = it.kind === "weapon"
      ? `<div class="card-block" style="margin:10px 0">
           <div class="section-label accent">Perfil Acústico (Motor GRW)</div>
           <div style="margin-top:4px">🔇 Com Silenciador: <strong>${it.noise_suppressed_m} m</strong></div>
           <div>🔊 Sem Silenciador: <strong>${it.noise_unsuppressed_m} m</strong></div>
         </div>`
      : "";

    panel.innerHTML = `
      <h2 style="margin:0 0 6px 0">${it.name}</h2>
      <div class="muted" style="margin-bottom:10px">📍 ${it.province_name} — ${it.location}</div>
      <p>${it.desc || ""}</p>
      ${acousticHtml}
      ${statsHtml}
      <div style="display:flex;gap:8px;margin-top:14px">
        <button id="btn-wiki-map" class="btn btn-cyan" style="flex:1">📍 ${GhostI18n.t("showOnMap")}</button>
        <button id="btn-wiki-collect" class="btn ${isDone ? "btn-green" : ""}">${isDone ? "✔ " + GhostI18n.t("collected") : GhostI18n.t("markCollected")}</button>
      </div>
    `;
    $("btn-wiki-map").onclick = () => {
      STATE.prefs.activeTab = "map";
      STATE.prefs.followPlayer = false;
      STATE.prefs.mapMode = "full";
      applyPrefsToControls();
      mapCtrl.highlightedItemId = it.id;
      mapCtrl.focusUV(it.u, it.v, 0.8);
      scheduleSavePrefs();
    };
    $("btn-wiki-collect").onclick = async () => {
      const r = await fetch("/api/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ toggle_item: it.id, toggle_poi: `poi_${it.id}` }),
      });
      STATE.progress = await r.json();
      mapCtrl.setProgress(STATE.progress);
      showWikiDetail(it);
      renderWikiGrid();
    };
  }

  function renderCartelGrid() {
    if (!STATE.cartel) return;
    const wingFilter = STATE.prefs.cartelWingFilter || "all";
    const bossesDone = new Set(STATE.progress.defeated_bosses || []);
    const wingsById = Object.fromEntries(STATE.cartel.wings.map((w) => [w.id, w]));
    const provs = STATE.cartel.provinces.filter((p) => wingFilter === "all" || p.wing === wingFilter);

    $("cartel-summary").textContent = `${bossesDone.size} / ${STATE.cartel.provinces.length} ${GhostI18n.t("bossDefeated")}`;
    $("cartel-grid").innerHTML = provs.map((p) => {
      const w = wingsById[p.wing] || {};
      const isDef = bossesDone.has(p.id);
      const skulls = "💀".repeat(p.skulls || 1);
      return `
        <div class="prov-card ${isDef ? "defeated" : ""}">
          <div class="card-title-row">
            <span style="font-size:15px">${p.name}</span>
            <span>${skulls}</span>
          </div>
          <div style="font-size:11.5px;color:${w.color || "#38bdf8"};font-weight:700">${w.name || p.wing} · Buchón: ${p.boss}</div>
          <div class="muted" style="font-size:11.5px">${p.biome} — ${p.desc}</div>
          <div style="display:flex;gap:8px;margin-top:6px">
            <button class="btn btn-cyan btn-prov-map" data-id="${p.id}" style="flex:1">📍 ${GhostI18n.t("showOnMap")}</button>
            <button class="btn ${isDef ? "btn-green" : ""} btn-prov-boss" data-id="${p.id}">${isDef ? "✔ " + GhostI18n.t("bossDefeated") : GhostI18n.t("bossDefeated")}</button>
          </div>
        </div>
      `;
    }).join("");

    $("cartel-grid").querySelectorAll(".btn-prov-map").forEach((b) => {
      b.onclick = () => {
        const p = STATE.cartel.provinces.find((x) => x.id === b.dataset.id);
        if (p) {
          STATE.prefs.activeTab = "map";
          STATE.prefs.followPlayer = false;
          applyPrefsToControls();
          mapCtrl.focusUV(p.u, p.v, 0.25);
        }
      };
    });
    $("cartel-grid").querySelectorAll(".btn-prov-boss").forEach((b) => {
      b.onclick = async () => {
        const r = await fetch("/api/progress", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ toggle_boss: b.dataset.id }),
        });
        STATE.progress = await r.json();
        renderCartelGrid();
      };
    });
  }

  async function openSettingsModal() {
    $("settings-modal").classList.remove("hidden");
    const st = await (await fetch("/api/status")).json();
    $("lbl-game-dir").textContent = st.game_dir || "—";
    $("lbl-hooks-status").textContent = `mode=${st.connection_mode} · hooks=0x${(st.hooks_mask || 0).toString(16)}`;
    if (st.lan_url) {
      $("row-lan-url").style.display = "flex";
      $("lbl-lan-url").textContent = st.lan_url;
    }
    const opts = [`<option value="auto">Auto</option>`];
    for (const l of (st.supported_languages || [])) {
      opts.push(`<option value="${l.code}">${l.label}</option>`);
    }
    $("sel-lang").innerHTML = opts.join("");
    $("sel-lang").value = st.lang_setting || "auto";
  }

  async function loadMarkers() {
    const res = await (await fetch("/api/markers")).json();
    STATE.markers = res.markers || [];
    mapCtrl && mapCtrl.setMarkers(STATE.markers);
  }

  async function loadStaticCaches() {
    const [md, cat, cr] = await Promise.all([
      fetch("/api/static/map_data").then((r) => (r.ok ? r.json() : null)),
      fetch("/api/static/catalog").then((r) => (r.ok ? r.json() : null)),
      fetch("/api/static/cartel").then((r) => (r.ok ? r.json() : null)),
    ]);
    STATE.mapData = md;
    STATE.catalog = cat;
    STATE.cartel = cr;
  }

  async function waitForBuildReady() {
    const ov = $("setup-overlay");
    for (let i = 0; i < 120; i++) {
      const st = await (await fetch("/api/status")).json();
      if (st.build && st.build.state === "ready") {
        ov.classList.add("hidden");
        return;
      }
      ov.classList.remove("hidden");
      $("setup-bar").style.width = `${(st.build && st.build.progress) || 15}%`;
      $("setup-message").textContent = (st.build && st.build.message) || "...";
      await new Promise((r) => setTimeout(r, 400));
    }
  }

  function renderAll() {
    mapCtrl.setData(STATE.mapData);
    mapCtrl.setProgress(STATE.progress);
    renderCategoryList();
    renderWikiGrid();
    renderCartelGrid();
    applyPrefsToControls();
  }

  async function init() {
    const setRes = await (await fetch("/api/settings")).json();
    STATE.lang = setRes.lang || "pt-BR";
    STATE.langSetting = setRes.lang_setting || "auto";
    GhostI18n.setLang(STATE.lang);

    let localSaved = {};
    try { localSaved = JSON.parse(localStorage.getItem("ghostpad_prefs_v1") || "{}"); } catch {}
    STATE.prefs = Object.assign({}, localSaved, setRes.ui_prefs || {});

    mapCtrl = new GhostMap.MapController($("map-canvas"), {
      onCursorMove: (u, v) => { $("map-cursor-coords").textContent = `UV: ${u.toFixed(3)} · ${v.toFixed(3)}`; },
      onUserPan: () => {
        STATE.prefs.followPlayer = false;
        applyPrefsToControls();
        scheduleSavePrefs();
      },
      onViewChange: (u, v, z) => {
        STATE.prefs.camU = u;
        STATE.prefs.camV = v;
        STATE.prefs.zoom = z;
        scheduleSavePrefs();
      },
      onSelectPoi: (poi) => showPoiDetail(poi),
      onSelectMarker: (m) => openMarkerEditor(m.u, m.v, m),
      onContextMark: (u, v) => openMarkerEditor(u, v, null),
    });
    if (setRes.world_bounds) mapCtrl.setWorldBounds(setRes.world_bounds);

    bindAllControls();
    await waitForBuildReady();
    await loadStaticCaches();
    STATE.progress = await (await fetch("/api/progress")).json();
    await loadMarkers();
    renderAll();

    if (typeof STATE.prefs.camU === "number" && typeof STATE.prefs.camV === "number") {
      mapCtrl.focusUV(STATE.prefs.camU, STATE.prefs.camV, STATE.prefs.zoom || 0.035);
    } else {
      mapCtrl.focusUV(0.5, 0.5, 0.032);
    }

    const es = new EventSource("/api/stream");
    es.onmessage = (ev) => {
      try {
        updateHudAndAlerts(JSON.parse(ev.data));
      } catch {}
    };
  }

  init();
})();
