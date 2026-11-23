# Ghost Tactical Pad — Ghost Recon Wildlands Second-Screen Companion

> **English** | [Português (PT-BR)](#português-pt-br)

**Ghost Tactical Pad** is a free, open-source tactical second-screen & LAN companion mod for **Tom Clancy's Ghost Recon Wildlands** (inspired by [Purah Pad for TotK](https://github.com/raseruda/totk-recomp-purah-pad)).  
Run it automatically on a **second monitor** alongside `GRW.exe` or open it from any **tablet, laptop, or smartphone** on your local network.

---

## Features

- **Multi-LOD 32K Tactical Map of Bolivia** — Extracts tiles on demand directly from your local `gr.wmap` (Satellite), `gr_h.wmap` (Skell Technology Heatmap), and `DataPC.forge` (province masks and **official BC7 HUD icons** for all 12 POI categories) at 60 FPS (`Canvas 2D` + zoom/pan + player trail + custom tactical pins). Zero copyrighted game assets are bundled.
- **Faction Classification & Live Alert States** — Separates every NPC by faction using `Entity::GetFaction` (`Entity + 0xD0`) + `GR_cNPCComponent` subcomponents with distinct map colors (**Blue** for Ghosts & Co-op allies, **Mustard Yellow** for Santa Blanca, **Purple** for La Unidad, **Green** for Rebels, and **White** for Civilians) plus dynamic alert outlines (**Orange ring** = Suspicious, **Red ring** = Hostile).
- **Live Stealth Telemetry & Customizable Detection Groups** — Tracks FOV vision cones, hearing rings, and equipped weapon noise radius (**Always visible** or **Only when aiming**). By default, sound and vision detection target **Santa Blanca** and **La Unidad**, with a faction matrix in Settings to toggle any group individually.
- **Automatic Aim Shot & Kill-Witness Warnings** — When you (or any Solo AI / Co-op ally) aim at an enemy, Ghost Tactical Pad checks nearby targets and warns immediately if anyone would **hear** the gunshot/impact (**Sound Alert**) or have line of sight to **see** the takedown (**Visual Witness Alert**).
- **Automatic Progression Sync & Armory Compatibility** — Automatically decrypts and syncs unlocked weapons, attachments, missions, bosses, provinces, **30 Bonus Medals**, **149 Skill Points**, and **211 Kingslayer Documents** directly from Wildlands `.save` files and `GRN_WorldMap`:
  - Click any weapon to inspect all **compatible attachments grouped by category** (Optics, Muzzle, Barrel, Magazine, Underbarrel, Rail, Stock).
  - Click any attachment to inspect all **compatible weapons grouped by weapon class**.
  - Click any province in **Cartel & Provinces** to see a full breakdown of **Completed (`✔`)** vs **Remaining (`○`)** missions, weapons, attachments, medals, skill points, Kingslayer documents, rebel ops, and bases.
  - **"Nearby" (`Por Perto`) Drawer with Category Filter Chips** — Shows only collectibles, missions, and intel by default (Weapons, Weapon Parts, Medals, Skill Points, Documents, Intel, Missions), with interactive filter chips to optionally include Bases, Fast Travel, Enemies, or Rebels/Allies.
- **Auto Game Language Sync (16 Languages)** — Reads Wildlands' active `LAUNCHER_GAME_LANGUAGE` configuration and follows the game's configured language automatically.
- **Real-Time Persistence & Single-Instance Protection** — All settings, tactical toggles, POI filters, camera position, and active tab persist continuously in real time. Prevents duplicate windows during Steam → Ubisoft Connect bootstrap handoff.
- **Standalone Executable (`GhostTacticalPad.exe`)** — Runs out-of-the-box with zero system Python or external dependencies required.

---

## Installation (Pre-Built Release)

1. Download and extract **`GhostPad_GRW_v1.3.0.zip`**.
2. Run **`Instalar Mod.bat`** *or* copy `winmm.dll`, `GhostTacticalPad.exe`, and `GhostPad\` next to `GRW.exe` inside your game directory (e.g. `C:\Program Files (x86)\Steam\steamapps\common\Wildlands\`).
3. Launch **Ghost Recon Wildlands** normally. Ghost Tactical Pad starts its local HTTP/SSE server on port **`8766`** and opens automatically on your secondary display (or at `http://127.0.0.1:8766` / your LAN IP shown in the Settings modal).

> **Standalone / Offline Mode:** Double-click **`GhostTacticalPad.exe`** (or **`Iniciar Ghost Pad.bat`**) anytime without opening the game and without having Python installed on your PC.

---

## Building from Source

### Requirements
- Windows x64 + **Visual Studio Build Tools** (`cl.exe` & `ml64.exe` via `vcvars64.bat`)
- **Python 3.12+** (Windows Store / PSF) with `Pillow` and `texture2ddecoder` (`pip install -r requirements.txt`)

### Commands

```bat
pip install -r requirements.txt
python mod_native/build_proxy.py
```

`build_proxy.py` compiles `winmm.dll` (`181` forwarded WinMM exports + Title Update 25 NPC/camera/weapon/`UPLAY_SAVE` observer hooks + native LZO1X decompressor) and `GhostTacticalPad.exe` (native standalone launcher loading the bundled embedded Python 3.12 runtime), validates clean PE/zip rules, and produces `GhostPad_GRW_v1.3.0.zip`.

### Running Tests

```bat
python -m unittest discover -s tests -v
```

---

## Credits & License

- **License:** Open-source under the [MIT License](LICENSE). You are free to study, modify, and redistribute forks under MIT terms.
- **100% Free & Non-Commercial Project:** This mod is strictly non-commercial.
- **Reverse-Engineering Attribution (CC BY-NC 4.0):**  
  AnvilNext 2.0 engine notes by Firejumper93, https://github.com/Firejumper93/GhostReconWildlands-AnvilNext2.0-Documentation
- **Companion Architecture:** Adapted from [totk-recomp-purah-pad](https://github.com/raseruda/totk-recomp-purah-pad).

### Legal Disclaimer
Tom Clancy's Ghost Recon Wildlands, AnvilNext 2.0, Santa Blanca, and related assets are trademarks/copyrights of Ubisoft Entertainment. Ghost Tactical Pad distributes **zero** game files, textures, maps, or copyrighted strings — everything is read locally from the user's legally owned installation.

---

<a name="português-pt-br"></a>

# Ghost Tactical Pad — Mod Second-Screen para Ghost Recon Wildlands

O **Ghost Tactical Pad** é um companheiro tático gratuito e open-source em segunda tela (ou navegador na rede local / tablet / celular) para **Tom Clancy's Ghost Recon Wildlands**, adaptado da arquitetura do [Purah Pad para TotK](https://github.com/raseruda/totk-recomp-purah-pad).

## Recursos Principais

- **Mapa Tático 32K da Bolívia em 60 FPS** — Lê diretamente os arquivos locais do seu jogo (`gr.wmap` Satélite, `gr_h.wmap` Mapa de Calor Skell e `DataPC.forge` com máscaras de província e os **ícones oficiais BC7 do jogo** para todos os filtros), sem distribuir nenhum arquivo protegido do jogo.
- **Facções, Cores e Estados Dinâmicos de Alerta** — Classifica automaticamente **Ghosts/Co-op (Azul)**, **Santa Blanca (Amarelo mostarda)**, **La Unidad (Roxo)**, **Rebeldes (Verde)** e **Civis (Branco)**, exibindo contorno **Laranja** quando desconfiados e **Vermelho** quando hostis.
- **Cones de Visão, Raio Sonoro e Grupos Customizáveis** — Detecção acústica e visual padrão ativada apenas para Santa Blanca e La Unidad (personalizável por grupo na interface), além de opção para exibir o raio sonoro da arma **Sempre visível** ou **Só ao mirar**.
- **Alertas Automáticos ao Mirar (Você + Aliados Solo IA / Co-op)** — Avisa em tempo real se alguém vai **ouvir** o disparo/impacto ou **ver** o abate ao mirar você ou seus aliados.
- **Reconhecimento Automático & Compatibilidade Arma ↔ Acessório** — Identifica automaticamente armas, acessórios, missões, chefes e tarefas concluídas/faltantes por província. Clicar em uma arma mostra todos os acessórios compatíveis por categoria; clicar em um acessório mostra todas as armas compatíveis por classe.
- **Idioma Sincronizado com o Jogo** — Lê automaticamente `LAUNCHER_GAME_LANGUAGE` do jogo para acompanhar o idioma configurado.
- **Instância Única, Salvamento Contínuo & Executável Independente** — Corrige abertura dupla na inicialização Steam/Ubisoft, salva todas as preferências em tempo real e inclui **`GhostTacticalPad.exe`** independente (não exige Python instalado no PC).
