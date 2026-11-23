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
    progress: {
      collected_items: [],
      completed_pois: [],
      discovered_provinces: [],
      defeated_bosses: [],
      completed_missions: [],
      auto_collected_items: [],
      auto_completed_pois: [],
      auto_completed_missions: [],
      auto_defeated_bosses: [],
      auto_sync_info: {},
    },
    live: null,
    markers: [],
    demoOn: false,
    lastRiskBeepAt: 0,
    audioCtx: null,
    selectedWikiId: null,
    lastProgressVersion: 0,
    refreshingProgress: false,
    reloadingLang: false,
  };

  // Evita duas guias abertas apontando para o mesmo mod
  const tabBornAt = performance.now();
  let singletonChan = null;
  try {
    if (typeof BroadcastChannel !== "undefined") {
      singletonChan = new BroadcastChannel("ghost_tactical_pad_singleton");
      singletonChan.onmessage = (ev) => {
        const msg = ev.data;
        if (msg === "ping") {
          singletonChan.postMessage("focus_existing");
          try { window.focus(); } catch {}
        } else if (msg === "focus_existing" && (performance.now() - tabBornAt) < 2500) {
          try { window.close(); } catch {}
        }
      };
      singletonChan.postMessage("ping");
    }
  } catch {}

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
      }, 150);
    }
  }

  function flushPrefsBeacon() {
    try {
      const blob = new Blob([JSON.stringify({ ui_prefs: STATE.prefs })], { type: "application/json" });
      navigator.sendBeacon("/api/settings", blob);
    } catch {}
  }

  window.addEventListener("pagehide", flushPrefsBeacon);
  window.addEventListener("beforeunload", flushPrefsBeacon);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") flushPrefsBeacon();
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

    const noiseMode = p.weaponNoiseRingMode || "always";
    document.querySelectorAll("#noise-mode-seg .mode-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.noiseMode === noiseMode);
    });

    // Checkboxes vinculados via data-pref
    document.querySelectorAll("input[type=checkbox][data-pref]").forEach((chk) => {
      const k = chk.dataset.pref;
      if (k in p) chk.checked = Boolean(p[k]);
    });

    const ghostMapChk = $("chk-faction-map-ghost");
    if (ghostMapChk) {
      ghostMapChk.checked = p.showAlliesSolo !== false || p.showAlliesCoop !== false;
    }

    const visFacSet = new Set(Array.isArray(p.visionFactions) ? p.visionFactions : ["santa_blanca", "unidad"]);
    document.querySelectorAll("input[type=checkbox][data-faction-vision]").forEach((chk) => {
      chk.checked = visFacSet.has(chk.dataset.factionVision);
    });
    const sndFacSet = new Set(Array.isArray(p.soundFactions) ? p.soundFactions : ["santa_blanca", "unidad"]);
    document.querySelectorAll("input[type=checkbox][data-faction-sound]").forEach((chk) => {
      chk.checked = sndFacSet.has(chk.dataset.factionSound);
    });

    // Wiki & Cartel persisted filters
    const wCat = p.wikiCat || "all";
    document.querySelectorAll("#wiki-cats .pill").forEach((b) => b.classList.toggle("active", b.dataset.wcat === wCat));
    if ($("wiki-class-filter")) $("wiki-class-filter").value = p.wikiClassFilter || "all";
    if ($("chk-wiki-missing")) $("chk-wiki-missing").checked = Boolean(p.wikiMissingOnly);
    const cWing = p.cartelWingFilter || "all";
    document.querySelectorAll("#cartel-wings .pill").forEach((b) => b.classList.toggle("active", b.dataset.wing === cWing));
    if ($("map-nearby")) {
      $("map-nearby").classList.toggle("hidden", !p.nearbyOpen);
    }
    if ($("btn-nearby")) {
      $("btn-nearby").classList.toggle("active", Boolean(p.nearbyOpen));
    }

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
        scheduleSavePrefs(true);
      });
    });

    document.querySelectorAll("#noise-mode-seg .mode-btn").forEach((b) => {
      b.addEventListener("click", () => {
        STATE.prefs.weaponNoiseRingMode = b.dataset.noiseMode;
        applyPrefsToControls();
        scheduleSavePrefs(true);
      });
    });

    const ghostMapChk = $("chk-faction-map-ghost");
    if (ghostMapChk) {
      ghostMapChk.addEventListener("change", () => {
        STATE.prefs.showAlliesSolo = ghostMapChk.checked;
        STATE.prefs.showAlliesCoop = ghostMapChk.checked;
        applyPrefsToControls();
        scheduleSavePrefs(true);
      });
    }

    document.querySelectorAll("input[type=checkbox][data-faction-vision]").forEach((chk) => {
      chk.addEventListener("change", () => {
        STATE.prefs.visionFactions = Array.from(
          document.querySelectorAll("input[type=checkbox][data-faction-vision]:checked")
        ).map((el) => el.dataset.factionVision);
        applyPrefsToControls();
        scheduleSavePrefs(true);
      });
    });

    document.querySelectorAll("input[type=checkbox][data-faction-sound]").forEach((chk) => {
      chk.addEventListener("change", () => {
        STATE.prefs.soundFactions = Array.from(
          document.querySelectorAll("input[type=checkbox][data-faction-sound]:checked")
        ).map((el) => el.dataset.factionSound);
        applyPrefsToControls();
        scheduleSavePrefs(true);
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
        weaponNoiseRingMode: "always",
        showSafeToFireHud: true,
        showPlayerAimWarning: true,
        showAlliesSolo: true,
        showAlliesCoop: true,
        showAllyAimWarning: true,
        showAllySightlines: true,
        showKillWitnessLines: true,
        showDrone: true,
        useTerrainLos: true,
        showFactionSantaBlanca: true,
        showFactionUnidad: true,
        showFactionRebel: true,
        showFactionCivilian: true,
        visionFactions: ["santa_blanca", "unidad"],
        soundFactions: ["santa_blanca", "unidad"],
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
      scheduleSavePrefs(true);
    });
    $("btn-cat-none").addEventListener("click", () => {
      STATE.prefs.enabledCats = [];
      renderCategoryList();
      applyPrefsToControls();
      scheduleSavePrefs(true);
    });

    $("map-search").addEventListener("input", renderMapSearch);
    $("btn-new-marker").addEventListener("click", () => openMarkerEditor(mapCtrl.camU, mapCtrl.camV));
    $("btn-nearby").addEventListener("click", () => {
      STATE.prefs.nearbyOpen = !STATE.prefs.nearbyOpen;
      STATE.prefs.nearbyManuallyClosed = !STATE.prefs.nearbyOpen;
      applyPrefsToControls();
      if (STATE.prefs.nearbyOpen) renderNearbyDrawer(true);
      scheduleSavePrefs(true);
    });
    $("btn-sim-demo").addEventListener("click", toggleDemoSimulation);

    // Wiki controls
    document.querySelectorAll("#wiki-cats .pill").forEach((b) => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#wiki-cats .pill").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        STATE.prefs.wikiCat = b.dataset.wcat;
        renderWikiGrid();
        scheduleSavePrefs(true);
      });
    });
    $("wiki-class-filter").addEventListener("change", (e) => {
      STATE.prefs.wikiClassFilter = e.target.value;
      renderWikiGrid();
      scheduleSavePrefs(true);
    });
    $("chk-wiki-missing").addEventListener("change", (e) => {
      STATE.prefs.wikiMissingOnly = e.target.checked;
      renderWikiGrid();
      scheduleSavePrefs(true);
    });
    $("wiki-search").addEventListener("input", renderWikiGrid);

    // Cartel controls
    document.querySelectorAll("#cartel-wings .pill").forEach((b) => {
      b.addEventListener("click", () => {
        document.querySelectorAll("#cartel-wings .pill").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        STATE.prefs.cartelWingFilter = b.dataset.wing;
        renderCartelGrid();
        scheduleSavePrefs(true);
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
      STATE.lang = res.lang || STATE.lang;
      STATE.langSetting = res.lang_setting || e.target.value;
      GhostI18n.setLang(STATE.lang);
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
        { id: "sb_2", faction: "santa_blanca", x: 446.0, y: -2440.0, z: 120.0, u: 0.5212, v: 0.6162, head: [446.0, -2440.0, 121.6], look_dir: [-1.0, 0.0, 0.0], yaw: 270.0, alert: "hostile", alive: true },
        { id: "sb_3", faction: "unidad", x: 420.0, y: -2492.0, z: 120.0, u: 0.5200, v: 0.6187, head: [420.0, -2492.0, 121.6], look_dir: [0.7, 0.7, 0.0], yaw: 45.0, alert: "suspected", alive: true },
        { id: "sb_4", faction: "santa_blanca", x: 375.0, y: -2445.0, z: 120.0, u: 0.5179, v: 0.6164, head: [375.0, -2445.0, 121.6], look_dir: [0.0, -1.0, 0.0], yaw: 180.0, alert: "unaware", alive: true },
      ],
      rebels: [
        { id: "reb_1", faction: "rebel", x: 392.0, y: -2518.0, z: 120.0, u: 0.5187, v: 0.6199, head: [392.0, -2518.0, 121.6], look_dir: [0.0, 1.0, 0.0], yaw: 15.0, alert: "unaware", alive: true },
        { id: "reb_2", faction: "rebel", x: 465.0, y: -2470.0, z: 120.0, u: 0.5221, v: 0.6176, head: [465.0, -2470.0, 121.6], look_dir: [-0.8, 0.6, 0.0], yaw: 310.0, alert: "hostile", alive: true },
      ],
      civilians: [
        { id: "civ_1", faction: "civilian", x: 408.0, y: -2540.0, z: 120.0, u: 0.5194, v: 0.6209, head: [408.0, -2540.0, 121.6], look_dir: [1.0, 0.0, 0.0], yaw: 90.0, alert: "unaware", alive: true },
        { id: "civ_2", faction: "civilian", x: 438.0, y: -2535.0, z: 120.0, u: 0.5209, v: 0.6207, head: [438.0, -2535.0, 121.6], look_dir: [0.0, 1.0, 0.0], yaw: 0.0, alert: "suspected", alive: true },
      ],
      trail: [{ u: 0.5192, v: 0.622 }, { u: 0.5196, v: 0.621 }, { u: 0.5200, v: 0.620 }],
    };
    await fetch("/api/debug/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(demo) });
    mapCtrl && mapCtrl.focusUV(0.52, 0.618, 1.45);
  }

  function findCatalogItem(id) {
    if (!STATE.catalog || !id) return null;
    for (const grp of [STATE.catalog.weapons || [], STATE.catalog.attachments || [], STATE.catalog.medals || []]) {
      const hit = grp.find((x) => x.id === id);
      if (hit) return hit;
    }
    return null;
  }

  function updateSyncPills() {
    const info = (STATE.progress && STATE.progress.auto_sync_info) || {};
    let modeKey = "sync.manual";
    if (info.save_write_seq || info.save_read_seq) modeKey = "sync.saveLive";
    else if (info.save_files && info.save_files.length) modeKey = "sync.fileSync";
    else if (info.source && String(info.source).includes("proximity")) modeKey = "sync.proximity";
    const text = `✔ ${GhostI18n.t("sync.active")} · ${GhostI18n.t(modeKey)}`;
    for (const id of ["wiki-sync-pill", "cartel-sync-pill"]) {
      const el = $(id);
      if (el) el.textContent = text;
    }
  }

  async function refreshProgressFromServer() {
    if (STATE.refreshingProgress) return;
    STATE.refreshingProgress = true;
    try {
      const r = await fetch("/api/progress");
      if (!r.ok) return;
      STATE.progress = await r.json();
      mapCtrl && mapCtrl.setProgress(STATE.progress);
      updateSyncPills();
      renderWikiGrid();
      renderCartelGrid();
      if (STATE.selectedWikiId) {
        const curIt = findCatalogItem(STATE.selectedWikiId);
        if (curIt) showWikiDetail(curIt);
      }
      if (STATE.prefs.selectedProvince && STATE.cartel) {
        const curProv = (STATE.cartel.provinces || []).find((p) => p.id === STATE.prefs.selectedProvince);
        if (curProv) showProvinceDetail(curProv);
      }
    } catch {} finally {
      STATE.refreshingProgress = false;
    }
  }

  function updateHudAndAlerts(live) {
    STATE.live = live;
    const pill = $("conn-pill");
    const mode = live.status === "demo" ? "demo" : (live.mode || "offline");
    pill.className = `conn-pill ${mode}`;
    pill.textContent = GhostI18n.t(`conn.${mode}`);

    // Acompanha automaticamente o idioma do jogo e progresso em tempo real
    if (STATE.langSetting === "auto" && live.lang && live.lang !== STATE.lang && !STATE.reloadingLang) {
      STATE.reloadingLang = true;
      STATE.lang = live.lang;
      GhostI18n.setLang(live.lang);
      loadStaticCaches()
        .then(() => renderAll())
        .catch(() => {})
        .finally(() => { STATE.reloadingLang = false; });
    }
    if (live.progress_version && live.progress_version !== STATE.lastProgressVersion) {
      STATE.lastProgressVersion = live.progress_version;
      refreshProgressFromServer();
    }

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
    const npcCount = Array.isArray(live.npcs)
      ? live.npcs.filter((n) => n.faction !== "ghost").length
      : (live.enemies || []).length + (live.rebels || []).length + (live.civilians || []).length;
    $("hud-squad").textContent = `👥 ${(tac.visible_allies || []).length} · 🎯 ${npcCount}`;
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
    if (!$("map-nearby").classList.contains("hidden")) renderNearbyDrawer(false);
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
            <img class="cat-icon" src="/api/icon/${c.id}.png?v=4" alt="" onerror="this.style.display='none'" />
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
        scheduleSavePrefs(true);
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

  const DEFAULT_NEARBY_CATS = [
    "weapon_case",
    "attachment_case",
    "bonus_medal",
    "skill_point",
    "kingslayer",
    "rebel_op",
    "mission",
  ];

  const NEARBY_FILTER_DEFS = [
    { id: "weapon_case", i18nKey: "nearby.cat.weapon_case" },
    { id: "attachment_case", i18nKey: "nearby.cat.attachment_case" },
    { id: "bonus_medal", i18nKey: "nearby.cat.bonus_medal" },
    { id: "skill_point", i18nKey: "nearby.cat.skill_point" },
    { id: "kingslayer", i18nKey: "nearby.cat.kingslayer" },
    { id: "rebel_op", i18nKey: "nearby.cat.rebel_op" },
    { id: "mission", i18nKey: "nearby.cat.mission" },
    { id: "bases", i18nKey: "nearby.cat.bases" },
    { id: "rally_point", i18nKey: "nearby.cat.rally_point" },
    { id: "enemies", i18nKey: "nearby.cat.enemies" },
    { id: "allies_rebels", i18nKey: "nearby.cat.allies_rebels" },
  ];

  let _nearbyLastRenderMs = 0;
  let _nearbyMouseDown = false;
  let _nearbyRowsCache = [];

  function _getActiveNearbyCats() {
    const arr = Array.isArray(STATE.prefs.nearbyCats) ? STATE.prefs.nearbyCats : DEFAULT_NEARBY_CATS;
    return new Set(arr);
  }

  function _ensureNearbyDrawerDOM(box) {
    if (box.dataset.initialized === "1" && $("nearby-list") && $("nearby-filters")) {
      const titleEl = $("nearby-title-text");
      if (titleEl) titleEl.textContent = `📡 ${GhostI18n.t("toolbar.nearby")}`;
      return;
    }
    box.dataset.initialized = "1";
    box.innerHTML = `
      <div class="modal-head" id="nearby-header">
        <h3 id="nearby-title-text">📡 ${GhostI18n.t("toolbar.nearby")}</h3>
        <button type="button" class="icon-btn" id="btn-close-nearby" title="Fechar">✕</button>
      </div>
      <div class="nearby-filters" id="nearby-filters"></div>
      <div class="nearby-list" id="nearby-list"></div>
    `;
    box.addEventListener("pointerdown", () => { _nearbyMouseDown = true; });
    window.addEventListener("pointerup", () => { _nearbyMouseDown = false; });

    const closeBtn = $("btn-close-nearby");
    const closeHandler = (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      STATE.prefs.nearbyOpen = false;
      STATE.prefs.nearbyManuallyClosed = true;
      box.classList.add("hidden");
      applyPrefsToControls();
      scheduleSavePrefs(true);
    };
    closeBtn.addEventListener("pointerdown", closeHandler);
    closeBtn.addEventListener("click", closeHandler);

    $("nearby-filters").addEventListener("click", (ev) => {
      const chip = ev.target.closest(".nearby-chip[data-ncat]");
      if (!chip) return;
      ev.preventDefault();
      ev.stopPropagation();
      const cid = chip.dataset.ncat;
      const cur = _getActiveNearbyCats();
      if (cur.has(cid)) cur.delete(cid);
      else cur.add(cid);
      STATE.prefs.nearbyCats = Array.from(cur);
      scheduleSavePrefs(true);
      renderNearbyDrawer(true);
    });

    $("nearby-list").addEventListener("click", (ev) => {
      const itemEl = ev.target.closest(".nearby-item[data-idx]");
      if (!itemEl) return;
      const r = _nearbyRowsCache[Number(itemEl.dataset.idx)];
      if (!r) return;
      STATE.prefs.followPlayer = false;
      applyPrefsToControls();
      mapCtrl.focusUV(r.u, r.v, 0.9);
      if (r.poi) showPoiDetail(r.poi);
    });
  }

  function renderNearbyDrawer(force = true) {
    const box = $("map-nearby");
    if (!box || box.classList.contains("hidden") || !STATE.mapData) return;
    _ensureNearbyDrawerDOM(box);

    const now = performance.now();
    if (!force && (_nearbyMouseDown || (now - _nearbyLastRenderMs) < 350)) {
      return;
    }
    _nearbyLastRenderMs = now;

    const activeCats = _getActiveNearbyCats();
    const filtersBox = $("nearby-filters");
    if (filtersBox) {
      filtersBox.innerHTML = NEARBY_FILTER_DEFS.map((f) => `
        <button type="button" class="nearby-chip ${activeCats.has(f.id) ? "active" : ""}" data-ncat="${f.id}">
          ${activeCats.has(f.id) ? "✔ " : ""}${GhostI18n.t(f.i18nKey)}
        </button>
      `).join("");
    }

    const p = (STATE.live && STATE.live.player) || { u: mapCtrl.camU, v: mapCtrl.camV };
    const span = (mapCtrl && mapCtrl.worldBounds && (mapCtrl.worldBounds.max_x - mapCtrl.worldBounds.min_x)) || 16384;
    const maxDist = Math.max(850, Number(STATE.prefs.assistRadius || 350) * 3.0);
    const donePois = new Set((STATE.progress && STATE.progress.completed_pois) || []);
    const doneItems = new Set((STATE.progress && STATE.progress.collected_items) || []);
    const doneMissions = new Set((STATE.progress && STATE.progress.completed_missions) || []);
    const hideCompleted = Boolean(STATE.prefs.hideCompleted);
    const rows = [];

    if (activeCats.has("enemies")) {
      for (const en of ((STATE.live && STATE.live.enemies) || [])) {
        const d = Math.hypot((en.u - p.u) * span, (en.v - p.v) * span);
        rows.push({
          kind: "enemy",
          name: `${GhostI18n.t(`faction.${en.faction}`)} (${GhostI18n.t(`alert.state${en.alert ? en.alert.charAt(0).toUpperCase() + en.alert.slice(1) : "Unaware"}`)})`,
          sub: GhostI18n.t("nearby.cat.enemies"),
          dist: d,
          u: en.u,
          v: en.v,
          isDone: false,
        });
      }
    }

    if (activeCats.has("allies_rebels")) {
      for (const al of ((STATE.live && STATE.live.allies) || [])) {
        const d = Math.hypot((al.u - p.u) * span, (al.v - p.v) * span);
        rows.push({
          kind: "ally",
          name: al.name || "Ghost",
          sub: GhostI18n.t("faction.ghost"),
          dist: d,
          u: al.u,
          v: al.v,
          isDone: false,
        });
      }
      for (const rb of ((STATE.live && STATE.live.rebels) || [])) {
        const d = Math.hypot((rb.u - p.u) * span, (rb.v - p.v) * span);
        rows.push({
          kind: "rebel",
          name: GhostI18n.t("faction.rebel"),
          sub: GhostI18n.t("nearby.cat.allies_rebels"),
          dist: d,
          u: rb.u,
          v: rb.v,
          isDone: false,
        });
      }
    }

    if (activeCats.has("mission") && STATE.cartel && Array.isArray(STATE.cartel.provinces)) {
      for (const prov of STATE.cartel.provinces) {
        for (const ms of (prov.missions || [])) {
          const isDone = doneMissions.has(ms.id);
          if (hideCompleted && isDone) continue;
          const d = Math.hypot((ms.u - p.u) * span, (ms.v - p.v) * span);
          if (d <= maxDist) {
            rows.push({
              kind: "mission",
              name: ms.name,
              sub: `${GhostI18n.t("cartel.missionsLabel")} · ${prov.name}`,
              dist: d,
              u: ms.u,
              v: ms.v,
              isDone,
            });
          }
        }
      }
    }

    const baseCats = new Set(["sb_base", "unidad_base", "sam_site", "jammer"]);
    for (const poi of STATE.mapData.pois) {
      const cat = poi.cat;
      let match = false;
      if (baseCats.has(cat)) {
        match = activeCats.has("bases");
      } else if (cat === "boss_hq") {
        match = activeCats.has("mission");
      } else {
        match = activeCats.has(cat);
      }
      if (!match) continue;
      const isDone = donePois.has(poi.id) || (poi.item_id && doneItems.has(poi.item_id));
      if (hideCompleted && isDone) continue;
      const d = Math.hypot((poi.u - p.u) * span, (poi.v - p.v) * span);
      if (d <= maxDist) {
        rows.push({
          kind: "poi",
          name: poi.name,
          sub: poi.province_name,
          dist: d,
          u: poi.u,
          v: poi.v,
          poi,
          isDone,
        });
      }
    }

    rows.sort((a, b) => a.dist - b.dist);
    _nearbyRowsCache = rows.slice(0, 25);
    const listBox = $("nearby-list");
    if (listBox) {
      listBox.innerHTML = _nearbyRowsCache.map((r, i) => `
        <div class="nearby-item ${r.isDone ? "done" : ""}" data-idx="${i}">
          <div style="display:flex;justify-content:space-between;gap:6px;align-items:center">
            <strong style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.isDone ? "✔ " : ""}${r.name}</strong>
            <span class="accent mono" style="white-space:nowrap">${Math.round(r.dist)} m</span>
          </div>
          ${r.sub ? `<div class="muted" style="font-size:11px">${r.sub}</div>` : ""}
        </div>
      `).join("") || `<div class="muted" style="padding:8px 2px">—</div>`;
    }
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
      const doneTag = isDone ? `<span class="done-badge">✔ ${GhostI18n.t("badge.collected")}</span>` : "";
      const acoustic = it.kind === "weapon" ? `<span class="muted">🔇 ${it.noise_suppressed_m}m · 🔊 ${it.noise_unsuppressed_m}m</span>` : "";
      return `
        <div class="item-card ${isDone ? "collected" : ""}" data-id="${it.id}">
          <div class="card-title-row">
            <span>${it.name}</span>
            <span style="display:flex;align-items:center;gap:4px">${doneTag}<span class="tag">${badge}</span></span>
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
    STATE.selectedWikiId = it.id;
    document.querySelectorAll("#wiki-grid .item-card").forEach((c) => {
      c.classList.toggle("selected", c.dataset.id === it.id);
    });

    const done = new Set(STATE.progress.collected_items || []);
    const autoDone = new Set(STATE.progress.auto_collected_items || []);
    const isDone = done.has(it.id);
    const isAuto = autoDone.has(it.id);
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

    let compatHtml = "";
    if (it.kind === "weapon") {
      if (it.customizable === false) {
        compatHtml = `<div class="compat-section muted" style="font-size:12px">${GhostI18n.t("wiki.customizableNo")}</div>`;
      } else {
        const groups = Array.isArray(it.compatible_attachments) ? it.compatible_attachments : [];
        if (groups.length) {
          compatHtml = `<div class="compat-section">
            <div class="section-label accent" style="margin-bottom:8px">${GhostI18n.t("wiki.compatAttachments")}</div>
            ${groups.map((grp) => `
              <div class="compat-slot-group">
                <div class="compat-slot-title">${grp.slot_label} (${grp.items.length})</div>
                <div class="compat-chips">
                  ${grp.items.map((att) => `
                    <button type="button" class="compat-chip ${done.has(att.id) ? "unlocked" : ""}" data-wiki-jump="${att.id}" title="${att.province_name} — ${att.location}">
                      ${done.has(att.id) ? "✔ " : "○ "}${att.name}
                    </button>
                  `).join("")}
                </div>
              </div>
            `).join("")}
          </div>`;
        } else {
          compatHtml = `<div class="compat-section muted" style="font-size:12px">${GhostI18n.t("wiki.noCompat")}</div>`;
        }
      }
    } else if (it.kind === "attachment") {
      const groups = Array.isArray(it.compatible_weapons) ? it.compatible_weapons : [];
      if (groups.length) {
        compatHtml = `<div class="compat-section">
          <div class="section-label accent" style="margin-bottom:8px">${GhostI18n.t("wiki.compatWeapons")}</div>
          ${groups.map((grp) => `
            <div class="compat-slot-group">
              <div class="compat-slot-title">${grp.class_label} (${grp.items.length})</div>
              <div class="compat-chips">
                ${grp.items.map((wp) => `
                  <button type="button" class="compat-chip ${done.has(wp.id) ? "unlocked" : ""}" data-wiki-jump="${wp.id}" title="${wp.province_name} — ${wp.location}">
                    ${done.has(wp.id) ? "✔ " : "○ "}${wp.name}
                  </button>
                `).join("")}
              </div>
            </div>
          `).join("")}
        </div>`;
      } else {
        compatHtml = `<div class="compat-section muted" style="font-size:12px">${GhostI18n.t("wiki.noCompat")}</div>`;
      }
    }

    panel.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px">
        <h2 style="margin:0">${it.name}</h2>
        ${isAuto ? `<span class="badge-auto">${GhostI18n.t("wiki.unlockedAuto")}</span>` : ""}
      </div>
      <div class="muted" style="margin-bottom:10px">📍 ${it.province_name} — ${it.location}</div>
      <p>${it.desc || ""}</p>
      ${acousticHtml}
      ${statsHtml}
      <div style="display:flex;gap:8px;margin-top:14px">
        <button id="btn-wiki-map" class="btn btn-cyan" style="flex:1">📍 ${GhostI18n.t("showOnMap")}</button>
        <button id="btn-wiki-collect" class="btn ${isDone ? "btn-green" : ""}">${isDone ? "✔ " + GhostI18n.t("collected") : GhostI18n.t("markCollected")}</button>
      </div>
      ${compatHtml}
    `;
    $("btn-wiki-map").onclick = () => {
      STATE.prefs.activeTab = "map";
      STATE.prefs.followPlayer = false;
      STATE.prefs.mapMode = "full";
      applyPrefsToControls();
      mapCtrl.highlightedItemId = it.id;
      mapCtrl.focusUV(it.u, it.v, 0.8);
      scheduleSavePrefs(true);
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
    panel.querySelectorAll("[data-wiki-jump]").forEach((btn) => {
      btn.onclick = () => {
        const target = findCatalogItem(btn.dataset.wikiJump);
        if (target) showWikiDetail(target);
      };
    });
  }

  function _provinceProgressStats(p) {
    const tasks = p.tasks || {};
    const doneItems = new Set(STATE.progress.collected_items || []);
    const donePois = new Set(STATE.progress.completed_pois || []);
    const doneMissions = new Set(STATE.progress.completed_missions || []);
    const autoItems = new Set(STATE.progress.auto_collected_items || []);
    const autoPois = new Set(STATE.progress.auto_completed_pois || []);
    const autoMissions = new Set(STATE.progress.auto_completed_missions || []);

    const defs = [
      ["missions", "cartel.missionsLabel", "mission"],
      ["weapons", "cartel.weaponsLabel", "item"],
      ["attachments", "cartel.attachmentsLabel", "item"],
      ["medals", "cartel.medalsLabel", "item"],
      ["skill_points", "cartel.skillPointsLabel", "poi"],
      ["kingslayer", "cartel.kingslayerLabel", "poi"],
      ["rebel_ops", "cartel.rebelOpsLabel", "poi"],
      ["rally_points", "cartel.rallyPointsLabel", "poi"],
      ["bases", "cartel.basesLabel", "poi"],
    ];

    const completed = [];
    const remaining = [];
    for (const [key, labelKey, toggleKind] of defs) {
      const arr = Array.isArray(tasks[key]) ? tasks[key] : [];
      for (const entry of arr) {
        const poiId = entry.poi_id || entry.id;
        const itemId = entry.item_id || (toggleKind === "item" ? entry.id : null);
        let isDone = false;
        let isAuto = false;
        if (toggleKind === "mission") {
          isDone = doneMissions.has(entry.id);
          isAuto = autoMissions.has(entry.id);
        } else if (toggleKind === "item") {
          isDone = doneItems.has(itemId) || (poiId && donePois.has(poiId));
          isAuto = autoItems.has(itemId) || (poiId && autoPois.has(poiId));
        } else {
          isDone = donePois.has(poiId) || (itemId && doneItems.has(itemId));
          isAuto = autoPois.has(poiId) || (itemId && autoItems.has(itemId));
        }
        const rec = { ...entry, catKey: key, catLabel: GhostI18n.t(labelKey), toggleKind, poiId, itemId, isDone, isAuto };
        if (isDone) completed.push(rec);
        else remaining.push(rec);
      }
    }
    const total = completed.length + remaining.length;
    const pct = total > 0 ? Math.round((completed.length * 100) / total) : 0;
    return { completed, remaining, total, pct };
  }

  function showProvinceDetail(p) {
    if (!p) return;
    STATE.prefs.selectedProvince = p.id;
    document.querySelectorAll("#cartel-grid .prov-card").forEach((c) => {
      c.classList.toggle("selected", c.dataset.id === p.id);
    });

    const panel = $("cartel-detail");
    if (!panel) return;
    panel.classList.remove("empty");

    const bossesDone = new Set(STATE.progress.defeated_bosses || []);
    const autoBosses = new Set(STATE.progress.auto_defeated_bosses || []);
    const isDef = bossesDone.has(p.id);
    const isBossAuto = autoBosses.has(p.id);
    const st = _provinceProgressStats(p);

    const renderGroup = (list, isDoneSection) => {
      if (!list.length) return `<div class="muted" style="font-size:12px">—</div>`;
      return list.map((t) => `
        <div class="prov-task-row ${isDoneSection ? "done" : "pending"}">
          <div style="min-width:0;flex:1">
            <div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
              ${isDoneSection ? "✔ " : "○ "}${t.name}
            </div>
            <div class="muted" style="font-size:10.5px">${t.catLabel}${t.location ? ` · ${t.location}` : ""}</div>
          </div>
          ${t.isAuto ? `<span class="badge-auto">${GhostI18n.t("cartel.autoLabel")}</span>` : ""}
          ${typeof t.u === "number" ? `<button class="icon-btn btn-task-map" data-u="${t.u}" data-v="${t.v}" data-tid="${t.item_id || t.poiId || t.id}" title="${GhostI18n.t("showOnMap")}">📍</button>` : ""}
          <button class="icon-btn btn-task-toggle" data-kind="${t.toggleKind}" data-id="${t.id}" data-item="${t.itemId || ""}" data-poi="${t.poiId || ""}" title="${isDoneSection ? GhostI18n.t("collected") : GhostI18n.t("markCollected")}">${isDoneSection ? "✔" : "○"}</button>
        </div>
      `).join("");
    };

    panel.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
        <h2 style="margin:0">${p.name}</h2>
        ${isBossAuto ? `<span class="badge-auto">${GhostI18n.t("cartel.autoLabel")}</span>` : ""}
      </div>
      <div class="muted" style="margin:4px 0 8px 0">Buchón: <strong>${p.boss}</strong> · ${p.biome}</div>
      <div class="prov-progress-row" style="margin-bottom:8px">
        <div class="prov-progress-bar"><div class="prov-progress-fill" style="width:${st.pct}%"></div></div>
        <span class="mono">${st.completed.length}/${st.total} (${st.pct}%)</span>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:10px">
        <button id="btn-detail-prov-map" class="btn btn-cyan" style="flex:1">📍 ${GhostI18n.t("showOnMap")}</button>
        <button id="btn-detail-prov-boss" class="btn ${isDef ? "btn-green" : ""}">${isDef ? "✔ " : ""}${GhostI18n.t("bossDefeated")}</button>
      </div>
      <div class="prov-tasks-group">
        <div class="prov-tasks-title" style="color:var(--green)">✔ ${GhostI18n.t("cartel.completedSection")} (${st.completed.length})</div>
        ${renderGroup(st.completed, true)}
      </div>
      <div class="prov-tasks-group">
        <div class="prov-tasks-title" style="color:#facc15">○ ${GhostI18n.t("cartel.remainingSection")} (${st.remaining.length})</div>
        ${renderGroup(st.remaining, false)}
      </div>
    `;

    $("btn-detail-prov-map").onclick = () => {
      STATE.prefs.activeTab = "map";
      STATE.prefs.followPlayer = false;
      applyPrefsToControls();
      mapCtrl.focusUV(p.u, p.v, 0.25);
      scheduleSavePrefs(true);
    };
    $("btn-detail-prov-boss").onclick = async () => {
      const r = await fetch("/api/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ toggle_boss: p.id }),
      });
      STATE.progress = await r.json();
      renderCartelGrid();
      showProvinceDetail(p);
    };
    panel.querySelectorAll(".btn-task-map").forEach((b) => {
      b.onclick = () => {
        STATE.prefs.activeTab = "map";
        STATE.prefs.followPlayer = false;
        STATE.prefs.mapMode = "full";
        applyPrefsToControls();
        mapCtrl.highlightedItemId = b.dataset.tid || null;
        mapCtrl.focusUV(Number(b.dataset.u), Number(b.dataset.v), 0.8);
        scheduleSavePrefs(true);
      };
    });
    panel.querySelectorAll(".btn-task-toggle").forEach((b) => {
      b.onclick = async () => {
        const body = {};
        if (b.dataset.kind === "mission") {
          body.toggle_mission = b.dataset.id;
        } else if (b.dataset.kind === "item") {
          body.toggle_item = b.dataset.item || b.dataset.id;
          if (b.dataset.poi) body.toggle_poi = b.dataset.poi;
        } else {
          body.toggle_poi = b.dataset.poi || b.dataset.id;
          if (b.dataset.item) body.toggle_item = b.dataset.item;
        }
        const r = await fetch("/api/progress", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        STATE.progress = await r.json();
        mapCtrl && mapCtrl.setProgress(STATE.progress);
        renderCartelGrid();
        showProvinceDetail(p);
      };
    });
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
      const isSel = STATE.prefs.selectedProvince === p.id;
      const skulls = "💀".repeat(p.skulls || 1);
      const st = _provinceProgressStats(p);
      const isAllDone = st.total > 0 && st.completed.length >= st.total;
      const isComplete = isDef || isAllDone;
      const doneTag = isComplete ? `<span class="done-badge">✔ ${GhostI18n.t("badge.completed")}</span>` : "";
      return `
        <div class="prov-card ${isComplete ? "defeated" : ""} ${isAllDone ? "completed-all" : ""} ${isSel ? "selected" : ""}" data-id="${p.id}">
          <div class="card-title-row">
            <span style="font-size:15px">${p.name}</span>
            <span style="display:flex;align-items:center;gap:5px">${doneTag}<span>${skulls}</span></span>
          </div>
          <div style="font-size:11.5px;color:${w.color || "#38bdf8"};font-weight:700">${w.name || p.wing} · Buchón: ${p.boss}</div>
          <div class="muted" style="font-size:11.5px">${p.biome} — ${p.desc}</div>
          <div class="prov-progress-row">
            <div class="prov-progress-bar"><div class="prov-progress-fill" style="width:${st.pct}%"></div></div>
            <span class="mono">${st.completed.length}/${st.total}</span>
          </div>
          <div style="display:flex;gap:8px;margin-top:6px">
            <button class="btn btn-cyan btn-prov-map" data-id="${p.id}" style="flex:1">📍 ${GhostI18n.t("showOnMap")}</button>
            <button class="btn ${isDef ? "btn-green" : ""} btn-prov-boss" data-id="${p.id}">${isDef ? "✔ " + GhostI18n.t("bossDefeated") : GhostI18n.t("bossDefeated")}</button>
          </div>
        </div>
      `;
    }).join("");

    $("cartel-grid").querySelectorAll(".prov-card").forEach((card) => {
      card.onclick = () => {
        const p = STATE.cartel.provinces.find((x) => x.id === card.dataset.id);
        if (p) {
          showProvinceDetail(p);
          scheduleSavePrefs(true);
        }
      };
    });
    $("cartel-grid").querySelectorAll(".btn-prov-map").forEach((b) => {
      b.onclick = (e) => {
        e.stopPropagation();
        const p = STATE.cartel.provinces.find((x) => x.id === b.dataset.id);
        if (p) {
          STATE.prefs.activeTab = "map";
          STATE.prefs.followPlayer = false;
          applyPrefsToControls();
          mapCtrl.focusUV(p.u, p.v, 0.25);
          scheduleSavePrefs(true);
        }
      };
    });
    $("cartel-grid").querySelectorAll(".btn-prov-boss").forEach((b) => {
      b.onclick = async (e) => {
        e.stopPropagation();
        const r = await fetch("/api/progress", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ toggle_boss: b.dataset.id }),
        });
        STATE.progress = await r.json();
        renderCartelGrid();
        const p = STATE.cartel.provinces.find((x) => x.id === b.dataset.id);
        if (p && STATE.prefs.selectedProvince === p.id) showProvinceDetail(p);
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
    const opts = [`<option value="auto">${GhostI18n.t("settings.langAuto")}</option>`];
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
    updateSyncPills();
    if (STATE.selectedWikiId) {
      const curIt = findCatalogItem(STATE.selectedWikiId);
      if (curIt) showWikiDetail(curIt);
    }
    if (STATE.prefs.selectedProvince && STATE.cartel) {
      const curProv = (STATE.cartel.provinces || []).find((p) => p.id === STATE.prefs.selectedProvince);
      if (curProv) showProvinceDetail(curProv);
    }
    applyPrefsToControls();
    if (STATE.prefs.nearbyOpen) renderNearbyDrawer(true);
  }

  function connectStream() {
    const es = new EventSource("/api/stream");
    es.onmessage = (ev) => {
      try {
        updateHudAndAlerts(JSON.parse(ev.data));
      } catch {}
    };
    es.onerror = () => {
      try { es.close(); } catch {}
      setTimeout(connectStream, 2000);
    };
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
      mapCtrl.setViewExact(STATE.prefs.camU, STATE.prefs.camV, STATE.prefs.zoom || 0.035);
    } else {
      mapCtrl.setViewExact(0.5, 0.5, 0.032);
    }

    connectStream();
  }

  init();
})();
