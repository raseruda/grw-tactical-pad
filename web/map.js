/* Motor Canvas 2D 60 FPS Multi-LOD do Ghost Tactical Pad */
window.GhostMap = (() => {
  const WORLD_PX = 32768;
  const GRID_LOD0 = 128;

  class MapController {
    constructor(canvas, opts) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.opts = opts || {};
      this.camU = 0.5;
      this.camV = 0.5;
      this.zoom = 0.035; // zoom=1 -> 1px = 1px do mapa 32K
      this.prefs = {};
      this.worldBounds = { min_x: -10500, max_x: 10500, min_y: -10500, max_y: 10500 };

      this.mapData = null;
      this.progress = { collected_items: [], completed_pois: [], discovered_provinces: [], defeated_bosses: [] };
      this.userMarkers = [];
      this.liveState = null;
      this.selectedPoi = null;
      this.highlightedItemId = null;

      this.tileCache = new Map();
      this.iconCache = new Map();
      this.maskCache = new Map();

      this._dragging = false;
      this._moved = false;
      this._lastX = 0;
      this._lastY = 0;
      this._needsRedraw = true;
      this._visiblePois = [];

      this._bindEvents();
      this._resize();
      this._loop();
    }

    setData(mapData) {
      this.mapData = mapData;
      this._needsRedraw = true;
    }

    setPrefs(prefs) {
      this.prefs = Object.assign({}, prefs || {});
      this._needsRedraw = true;
    }

    setWorldBounds(wb) {
      if (wb) this.worldBounds = wb;
      this._needsRedraw = true;
    }

    setProgress(prog) {
      if (prog) this.progress = prog;
      this._needsRedraw = true;
    }

    setMarkers(markers) {
      this.userMarkers = markers || [];
      this._needsRedraw = true;
    }

    setLive(live) {
      this.liveState = live;
      if (this.prefs.followPlayer && live && live.player && typeof live.player.u === "number") {
        const tgt = (this.prefs.showDrone !== false && live.drone) ? live.drone : live.player;
        this.camU = tgt.u;
        this.camV = tgt.v;
      }
      this._needsRedraw = true;
    }

    focusUV(u, v, minZoom) {
      this.camU = Math.max(0, Math.min(1, u));
      this.camV = Math.max(0, Math.min(1, v));
      if (minZoom && this.zoom < minZoom) this.zoom = minZoom;
      this._needsRedraw = true;
      if (this.opts.onViewChange) this.opts.onViewChange(this.camU, this.camV, this.zoom);
    }

    recenterOnPlayer() {
      const l = this.liveState;
      if (l && l.player) {
        const tgt = (this.prefs.showDrone !== false && l.drone) ? l.drone : l.player;
        this.focusUV(tgt.u, tgt.v, Math.max(this.zoom, 0.45));
      } else {
        this.focusUV(0.5, 0.5, 0.032);
      }
    }

    zoomBy(factor, cx, cy) {
      const rect = this.canvas.getBoundingClientRect();
      const px = cx !== undefined ? cx : rect.width * 0.5;
      const py = cy !== undefined ? cy : rect.height * 0.5;
      const before = this.screenToUV(px, py);
      this.zoom = Math.max(0.018, Math.min(2.5, this.zoom * factor));
      const after = this.screenToUV(px, py);
      this.camU += before.u - after.u;
      this.camV += before.v - after.v;
      this.camU = Math.max(0, Math.min(1, this.camU));
      this.camV = Math.max(0, Math.min(1, this.camV));
      this._needsRedraw = true;
      if (this.opts.onViewChange) this.opts.onViewChange(this.camU, this.camV, this.zoom);
    }

    uvToScreen(u, v) {
      const w = this.canvas.width / (window.devicePixelRatio || 1);
      const h = this.canvas.height / (window.devicePixelRatio || 1);
      const scale = WORLD_PX * this.zoom;
      return {
        x: w * 0.5 + (u - this.camU) * scale,
        y: h * 0.5 + (v - this.camV) * scale,
      };
    }

    screenToUV(sx, sy) {
      const w = this.canvas.width / (window.devicePixelRatio || 1);
      const h = this.canvas.height / (window.devicePixelRatio || 1);
      const scale = WORLD_PX * this.zoom;
      return {
        u: this.camU + (sx - w * 0.5) / scale,
        v: this.camV + (sy - h * 0.5) / scale,
      };
    }

    metersToPixels(meters) {
      const span = Math.max(1000, (this.worldBounds.max_x - this.worldBounds.min_x) || 21000);
      return (meters / span) * WORLD_PX * this.zoom;
    }

    _resize() {
      const dpr = window.devicePixelRatio || 1;
      const rect = this.canvas.parentElement.getBoundingClientRect();
      this.canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      this.canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      this._needsRedraw = true;
    }

    _bindEvents() {
      window.addEventListener("resize", () => this._resize());

      this.canvas.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return;
        this._dragging = true;
        this._moved = false;
        this._lastX = e.clientX;
        this._lastY = e.clientY;
      });

      window.addEventListener("mousemove", (e) => {
        const rect = this.canvas.getBoundingClientRect();
        const sx = e.clientX - rect.left;
        const sy = e.clientY - rect.top;
        if (sx >= 0 && sy >= 0 && sx <= rect.width && sy <= rect.height && this.opts.onCursorMove) {
          const uv = this.screenToUV(sx, sy);
          this.opts.onCursorMove(uv.u, uv.v);
        }
        if (!this._dragging) return;
        const dx = e.clientX - this._lastX;
        const dy = e.clientY - this._lastY;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) this._moved = true;
        this._lastX = e.clientX;
        this._lastY = e.clientY;
        const scale = WORLD_PX * this.zoom;
        this.camU = Math.max(0, Math.min(1, this.camU - dx / scale));
        this.camV = Math.max(0, Math.min(1, this.camV - dy / scale));
        if (this._moved && this.prefs.followPlayer && this.opts.onUserPan) {
          this.opts.onUserPan();
        }
        this._needsRedraw = true;
      });

      window.addEventListener("mouseup", (e) => {
        if (!this._dragging) return;
        const wasMoved = this._moved;
        this._dragging = false;
        if (wasMoved && this.opts.onViewChange) {
          this.opts.onViewChange(this.camU, this.camV, this.zoom);
        } else if (!wasMoved && e.target === this.canvas) {
          const rect = this.canvas.getBoundingClientRect();
          this._handleClick(e.clientX - rect.left, e.clientY - rect.top);
        }
      });

      this.canvas.addEventListener("wheel", (e) => {
        e.preventDefault();
        const rect = this.canvas.getBoundingClientRect();
        const factor = e.deltaY < 0 ? 1.22 : 1 / 1.22;
        this.zoomBy(factor, e.clientX - rect.left, e.clientY - rect.top);
      }, { passive: false });

      this.canvas.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        const rect = this.canvas.getBoundingClientRect();
        const uv = this.screenToUV(e.clientX - rect.left, e.clientY - rect.top);
        if (this.opts.onContextMark) this.opts.onContextMark(uv.u, uv.v);
      });
    }

    _handleClick(sx, sy) {
      // Hit-test POIs visíveis + marcadores do usuário
      for (const m of this.userMarkers) {
        const pt = this.uvToScreen(m.u, m.v);
        if (Math.hypot(pt.x - sx, pt.y - sy) <= 16) {
          if (this.opts.onSelectMarker) this.opts.onSelectMarker(m);
          return;
        }
      }
      let best = null;
      let bestD = 18;
      for (const poi of this._visiblePois) {
        const pt = this.uvToScreen(poi.u, poi.v);
        const d = Math.hypot(pt.x - sx, pt.y - sy);
        if (d < bestD) {
          bestD = d;
          best = poi;
        }
      }
      this.selectedPoi = best;
      this._needsRedraw = true;
      if (this.opts.onSelectPoi) this.opts.onSelectPoi(best);
    }

    _getTile(style, lod, col, row) {
      const key = `${style}/${lod}/${col}/${row}`;
      let rec = this.tileCache.get(key);
      if (!rec) {
        const img = new Image();
        rec = { img, loaded: false, err: false };
        img.onload = () => { rec.loaded = true; this._needsRedraw = true; };
        img.onerror = () => { rec.err = true; };
        img.src = `/api/tile/${style}/${lod}/${col}/${row}.png`;
        this.tileCache.set(key, rec);
        if (this.tileCache.size > 600) {
          const first = this.tileCache.keys().next().value;
          this.tileCache.delete(first);
        }
      }
      return rec;
    }

    _getIcon(name) {
      let rec = this.iconCache.get(name);
      if (!rec) {
        const img = new Image();
        rec = { img, loaded: false };
        img.onload = () => { rec.loaded = true; this._needsRedraw = true; };
        img.src = `/api/icon/${name}.png`;
        this.iconCache.set(name, rec);
      }
      return rec;
    }

    _getMask(name) {
      let rec = this.maskCache.get(name);
      if (!rec) {
        const img = new Image();
        rec = { img, loaded: false };
        img.onload = () => { rec.loaded = true; this._needsRedraw = true; };
        img.src = `/api/mask/${name}.png`;
        this.maskCache.set(name, rec);
      }
      return rec;
    }

    _loop() {
      if (this._needsRedraw) {
        this._needsRedraw = false;
        this.draw();
      }
      requestAnimationFrame(() => this._loop());
    }

    _computeVisiblePois() {
      if (!this.mapData) return [];
      const enabled = this.prefs.enabledCats ? new Set(this.prefs.enabledCats) : null;
      const mode = this.prefs.mapMode || "assist";
      const hideDone = Boolean(this.prefs.hideCompleted);
      const fog = Boolean(this.prefs.fogOfWar);
      const doneItems = new Set(this.progress.collected_items || []);
      const donePois = new Set(this.progress.completed_pois || []);
      const discProvs = new Set(this.progress.discovered_provinces || []);
      const player = this.liveState && this.liveState.player;
      const rad = Number(this.prefs.assistRadius || 350);
      const span = Math.max(1000, (this.worldBounds.max_x - this.worldBounds.min_x) || 21000);

      const out = [];
      for (const poi of this.mapData.pois) {
        if (enabled && !enabled.has(poi.cat)) continue;
        const isDone = donePois.has(poi.id) || (poi.item_id && doneItems.has(poi.item_id));
        if (hideDone && isDone) continue;
        if (fog && !discProvs.has(poi.province)) continue;

        if (mode === "spoiler_free" && !discProvs.has(poi.province)) continue;
        if (mode === "assist" && !discProvs.has(poi.province) && poi.cat !== "rally_point" && poi.cat !== "boss_hq") {
          if (player) {
            const distM = Math.hypot((poi.u - player.u) * span, (poi.v - player.v) * span);
            if (distM > rad) continue;
          } else {
            continue;
          }
        }
        out.push({ ...poi, done: isDone });
      }
      return out;
    }

    draw() {
      const ctx = this.ctx;
      const dpr = window.devicePixelRatio || 1;
      const w = this.canvas.width / dpr;
      const h = this.canvas.height / dpr;
      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.fillStyle = "#04070b";
      ctx.fillRect(0, 0, w, h);

      const style = this.prefs.mapStyle === "heatmap" ? "heatmap" : "satellite";
      const lod = Math.max(0, Math.min(6, Math.round(-Math.log2(Math.max(0.01, this.zoom)))));
      const zoomLbl = document.getElementById("map-zoom-label");
      if (zoomLbl) zoomLbl.textContent = `LOD ${lod} · ${(this.zoom * 100).toFixed(1)}%`;

      // Base LOD 6 para nunca piscar durante zoom
      const baseGrid = 2;
      for (let r = 0; r < baseGrid; r++) {
        for (let c = 0; c < baseGrid; c++) {
          const rec = this._getTile(style, 6, c, r);
          if (rec.loaded) {
            const p0 = this.uvToScreen(c / baseGrid, r / baseGrid);
            const p1 = this.uvToScreen((c + 1) / baseGrid, (r + 1) / baseGrid);
            ctx.drawImage(rec.img, p0.x, p0.y, p1.x - p0.x + 0.5, p1.y - p0.y + 0.5);
          }
        }
      }

      // Camada LOD ativa
      if (lod < 6) {
        const grid = GRID_LOD0 >> lod;
        const tl = this.screenToUV(0, 0);
        const br = this.screenToUV(w, h);
        const c0 = Math.max(0, Math.floor(tl.u * grid));
        const c1 = Math.min(grid - 1, Math.floor(br.u * grid));
        const r0 = Math.max(0, Math.floor(tl.v * grid));
        const r1 = Math.min(grid - 1, Math.floor(br.v * grid));
        for (let r = r0; r <= r1; r++) {
          for (let c = c0; c <= c1; c++) {
            const rec = this._getTile(style, lod, c, r);
            if (rec.loaded) {
              const p0 = this.uvToScreen(c / grid, r / grid);
              const p1 = this.uvToScreen((c + 1) / grid, (r + 1) / grid);
              ctx.drawImage(rec.img, p0.x, p0.y, p1.x - p0.x + 0.6, p1.y - p0.y + 0.6);
            }
          }
        }
      }

      const tlMap = this.uvToScreen(0, 0);
      const brMap = this.uvToScreen(1, 1);

      // Bordas de províncias / máscara da Bolívia
      if (this.prefs.showProvinces !== false) {
        const provMask = this._getMask("provinces_overlay");
        if (provMask.loaded) {
          ctx.drawImage(provMask.img, tlMap.x, tlMap.y, brMap.x - tlMap.x, brMap.y - tlMap.y);
        }
        const borderMask = this._getMask("bolivia_border");
        if (borderMask.loaded) {
          ctx.drawImage(borderMask.img, tlMap.x, tlMap.y, brMap.x - tlMap.x, brMap.y - tlMap.y);
        }
      }

      // Nomes das 21 províncias
      if (this.prefs.showProvinces !== false && this.mapData && this.mapData.provinces) {
        ctx.textAlign = "center";
        ctx.font = "700 11px Segoe UI, sans-serif";
        for (const p of this.mapData.provinces) {
          const pt = this.uvToScreen(p.u, p.v);
          if (pt.x < -80 || pt.x > w + 80 || pt.y < -30 || pt.y > h + 30) continue;
          ctx.fillStyle = "rgba(4, 7, 11, 0.72)";
          ctx.fillText(p.name.toUpperCase(), pt.x + 1, pt.y + 1);
          ctx.fillStyle = "rgba(186, 230, 253, 0.86)";
          ctx.fillText(p.name.toUpperCase(), pt.x, pt.y);
        }
      }

      // POIs do catálogo
      this._visiblePois = this._computeVisiblePois();
      for (const poi of this._visiblePois) {
        const pt = this.uvToScreen(poi.u, poi.v);
        if (pt.x < -24 || pt.x > w + 24 || pt.y < -24 || pt.y > h + 24) continue;
        const isHl = this.highlightedItemId && poi.item_id === this.highlightedItemId;
        const isSel = this.selectedPoi && this.selectedPoi.id === poi.id;
        ctx.save();
        if (poi.done) ctx.globalAlpha = 0.42;
        if (isHl || isSel) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 17, 0, Math.PI * 2);
          ctx.strokeStyle = isHl ? "#facc15" : "#38bdf8";
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }
        const ic = this._getIcon(poi.cat);
        if (ic.loaded) {
          ctx.drawImage(ic.img, pt.x - 11, pt.y - 11, 22, 22);
        } else {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
          ctx.fillStyle = "#38bdf8";
          ctx.fill();
        }
        ctx.restore();
      }

      // Marcadores customizados do usuário
      if (this.prefs.showCustom !== false) {
        for (const m of this.userMarkers) {
          const pt = this.uvToScreen(m.u, m.v);
          ctx.save();
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 8, 0, Math.PI * 2);
          ctx.fillStyle = m.color || "#38bdf8";
          ctx.fill();
          ctx.strokeStyle = "#04070b";
          ctx.lineWidth = 2;
          ctx.stroke();
          ctx.fillStyle = "#f8fafc";
          ctx.font = "600 11px Segoe UI, sans-serif";
          ctx.fillText(m.title, pt.x + 11, pt.y + 4);
          ctx.restore();
        }
      }

      // Camada AO VIVO: Trilha, Radar, Inimigos, Aliados, Acústica, Visão e Testemunhas
      this._drawLiveTacticalLayer(ctx, w, h);

      ctx.restore();
    }

    _drawArrow(ctx, x, y, yawDeg, size, fill, stroke) {
      const rad = (yawDeg * Math.PI) / 180;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(rad);
      ctx.beginPath();
      ctx.moveTo(0, -size * 1.25);
      ctx.lineTo(size * 0.8, size * 0.9);
      ctx.lineTo(0, size * 0.4);
      ctx.lineTo(-size * 0.8, size * 0.9);
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1.6;
      ctx.stroke();
      ctx.restore();
    }

    _drawLiveTacticalLayer(ctx, w, h) {
      const live = this.liveState;
      if (!live) return;
      const tac = live.tactical || {};
      const player = live.player;

      // Trilha da sessão
      if (this.prefs.showTrail !== false && Array.isArray(live.trail) && live.trail.length > 1) {
        ctx.save();
        ctx.beginPath();
        live.trail.forEach((pt, idx) => {
          const s = this.uvToScreen(pt.u, pt.v);
          if (idx === 0) ctx.moveTo(s.x, s.y);
          else ctx.lineTo(s.x, s.y);
        });
        ctx.strokeStyle = "rgba(56, 189, 248, 0.55)";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.restore();
      }

      // Círculo do Radar (Assist)
      if (player && this.prefs.mapMode === "assist") {
        const ps = this.uvToScreen(player.u, player.v);
        const rPx = this.metersToPixels(Number(this.prefs.assistRadius || 350));
        ctx.save();
        ctx.beginPath();
        ctx.arc(ps.x, ps.y, rPx, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(56, 189, 248, 0.35)";
        ctx.setLineDash([6, 6]);
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.restore();
      }

      // Raio sonoro da arma equipada ao redor do Jogador
      if (player && this.prefs.showWeaponNoiseRing !== false && tac.safe_fire && tac.safe_fire.hear_radius_m > 0) {
        const ps = this.uvToScreen(player.u, player.v);
        const rPx = this.metersToPixels(tac.safe_fire.hear_radius_m);
        const isSafe = tac.safe_fire.safe;
        ctx.save();
        ctx.beginPath();
        ctx.arc(ps.x, ps.y, rPx, 0, Math.PI * 2);
        ctx.fillStyle = isSafe ? "rgba(34, 197, 94, 0.05)" : "rgba(245, 158, 11, 0.11)";
        ctx.fill();
        ctx.strokeStyle = isSafe ? "rgba(34, 197, 94, 0.6)" : "rgba(245, 158, 11, 0.85)";
        ctx.setLineDash([5, 5]);
        ctx.lineWidth = 1.6;
        ctx.stroke();
        ctx.restore();
      }

      // Inimigos, direção do olhar, cones FOV e círculos de audição
      const enemies = live.enemies || [];
      const visRangeM = Number(this.prefs.enemyVisionRangeM || 55);
      const fovRad = (Number(this.prefs.enemyFovDeg || 110) * Math.PI) / 180;
      const visPx = this.metersToPixels(visRangeM);

      if (this.prefs.showEnemies !== false) {
        for (const en of enemies) {
          if (en.alive === false) continue;
          const es = this.uvToScreen(en.u, en.v);
          if (es.x < -120 || es.x > w + 120 || es.y < -120 || es.y > h + 120) continue;

          const yawDeg = Number(en.yaw || 0);
          const lookAngleCanvas = ((yawDeg - 90) * Math.PI) / 180; // 0 deg = Norte = -PI/2 no canvas

          // Cone de Visão (FOV)
          if (this.prefs.showEnemyVisionCones !== false && visPx > 4) {
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(es.x, es.y);
            ctx.arc(es.x, es.y, visPx, lookAngleCanvas - fovRad * 0.5, lookAngleCanvas + fovRad * 0.5);
            ctx.closePath();
            const isEngaged = en.alert === "engaged" || en.alert === "hunted";
            const isSusp = en.alert === "suspected";
            ctx.fillStyle = isEngaged
              ? "rgba(239, 68, 68, 0.18)"
              : isSusp
              ? "rgba(245, 158, 11, 0.16)"
              : "rgba(239, 68, 68, 0.09)";
            ctx.fill();
            ctx.strokeStyle = isSusp ? "rgba(245, 158, 11, 0.45)" : "rgba(239, 68, 68, 0.35)";
            ctx.lineWidth = 1;
            ctx.stroke();
            ctx.restore();
          }

          // Círculo opcional de audição do inimigo (alerta próximo)
          if (this.prefs.showEnemyHearingRings) {
            const hPx = this.metersToPixels(Number(this.prefs.bulletImpactNoiseM || 12));
            ctx.save();
            ctx.beginPath();
            ctx.arc(es.x, es.y, hPx, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(245, 158, 11, 0.32)";
            ctx.setLineDash([3, 4]);
            ctx.stroke();
            ctx.restore();
          }

          const baseColor = en.faction === "unidad" ? "#a855f7" : en.alert === "suspected" ? "#f59e0b" : "#ef4444";
          if (this.prefs.showEnemyDirection !== false) {
            this._drawArrow(ctx, es.x, es.y, yawDeg, 7.5, baseColor, "#04070b");
          } else {
            ctx.beginPath();
            ctx.arc(es.x, es.y, 5.5, 0, Math.PI * 2);
            ctx.fillStyle = baseColor;
            ctx.fill();
          }
        }
      }

      // Aliados (Solo IA + Co-op) e linhas de mira
      const allies = tac.visible_allies || [];
      for (const al of allies) {
        const as = this.uvToScreen(al.u, al.v);
        const col = al.type === "coop" ? "#a855f7" : "#22c55e";
        if (this.prefs.showAllySightlines !== false && al.is_aiming && al.aim_dir) {
          const aimLenPx = Math.max(40, this.metersToPixels(90));
          const ang = Math.atan2(al.aim_dir[0], al.aim_dir[1]);
          ctx.save();
          ctx.beginPath();
          ctx.moveTo(as.x, as.y);
          ctx.lineTo(as.x + Math.sin(ang) * aimLenPx, as.y - Math.cos(ang) * aimLenPx);
          ctx.strokeStyle = al.type === "coop" ? "rgba(192, 132, 252, 0.7)" : "rgba(74, 222, 128, 0.65)";
          ctx.setLineDash([4, 4]);
          ctx.lineWidth = 1.6;
          ctx.stroke();
          ctx.restore();
        }
        this._drawArrow(ctx, as.x, as.y, Number(al.yaw || 0), 8, col, "#ffffff");
        ctx.save();
        ctx.font = "700 10.5px Segoe UI, sans-serif";
        ctx.fillStyle = col;
        ctx.fillText(al.name || (al.type === "coop" ? "CO-OP" : "AI"), as.x + 11, as.y + 3);
        ctx.restore();
      }

      // Linhas de Testemunha Visual & Sonora para Mira do Jogador e Mira dos Aliados
      if (this.prefs.showKillWitnessLines !== false) {
        const shots = [];
        if (tac.player_aim) shots.push(tac.player_aim);
        if (Array.isArray(tac.ally_aims)) shots.push(...tac.ally_aims);

        for (const sh of shots) {
          if (typeof sh.target_u !== "number" || typeof sh.target_v !== "number") continue;
          const ts = this.uvToScreen(sh.target_u, sh.target_v);
          const ss = this.uvToScreen(sh.shooter_u, sh.shooter_v);

          // Linha do atirador até o alvo
          ctx.save();
          ctx.beginPath();
          ctx.moveTo(ss.x, ss.y);
          ctx.lineTo(ts.x, ts.y);
          ctx.strokeStyle = sh.verdict === "safe" ? "#22c55e" : sh.verdict === "sound_risk" ? "#f59e0b" : "#ef4444";
          ctx.lineWidth = 2.2;
          ctx.setLineDash([7, 4]);
          ctx.stroke();

          // Círculo do impacto da bala ao redor do alvo
          if (sh.impact_noise_m > 0) {
            ctx.beginPath();
            ctx.arc(ts.x, ts.y, this.metersToPixels(sh.impact_noise_m), 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(245, 158, 11, 0.5)";
            ctx.lineWidth = 1.2;
            ctx.stroke();
          }

          // Alvo destacado
          ctx.setLineDash([]);
          ctx.beginPath();
          ctx.arc(ts.x, ts.y, 12, 0, Math.PI * 2);
          ctx.strokeStyle = sh.verdict === "safe" ? "#22c55e" : "#ff2e4c";
          ctx.lineWidth = 2.5;
          ctx.stroke();

          // Linhas vermelhas de cada testemunha visual -> alvo
          for (const vw of (sh.visual_witnesses || [])) {
            const ws = this.uvToScreen(vw.u, vw.v);
            ctx.beginPath();
            ctx.moveTo(ws.x, ws.y);
            ctx.lineTo(ts.x, ts.y);
            ctx.strokeStyle = "rgba(255, 46, 76, 0.92)";
            ctx.lineWidth = 2.2;
            ctx.stroke();
          }
          // Linhas âmbar de cada ouvinte -> atirador/alvo
          for (const sw of (sh.sound_witnesses || [])) {
            const ws = this.uvToScreen(sw.u, sw.v);
            const src = sw.reason === "impact" ? ts : ss;
            ctx.beginPath();
            ctx.moveTo(ws.x, ws.y);
            ctx.lineTo(src.x, src.y);
            ctx.strokeStyle = "rgba(245, 158, 11, 0.88)";
            ctx.setLineDash([3, 3]);
            ctx.lineWidth = 2;
            ctx.stroke();
          }
          ctx.restore();
        }
      }

      // Drone
      if (this.prefs.showDrone !== false && live.drone) {
        const ds = this.uvToScreen(live.drone.u, live.drone.v);
        ctx.save();
        ctx.beginPath();
        ctx.arc(ds.x, ds.y, 7, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(56, 189, 248, 0.3)";
        ctx.fill();
        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = "#bae6fd";
        ctx.font = "700 10px Segoe UI, sans-serif";
        ctx.fillText("DRONE", ds.x + 10, ds.y + 3);
        ctx.restore();
      }

      // Jogador (Ghost Local)
      if (player) {
        const ps = this.uvToScreen(player.u, player.v);
        this._drawArrow(ctx, ps.x, ps.y, Number(player.yaw || 0), 10, "#38bdf8", "#ffffff");
      }
    }
  }

  return { MapController };
})();
