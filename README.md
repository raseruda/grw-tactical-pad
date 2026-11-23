# Ghost Tactical Pad — Ghost Recon Wildlands Second-Screen Companion

> **English** | [Português (PT-BR)](#português-pt-br)

**Ghost Tactical Pad** is a free, open-source tactical second-screen & LAN companion mod for **Tom Clancy's Ghost Recon Wildlands** (inspired by [Purah Pad for TotK](https://github.com/raseruda/totk-recomp-purah-pad)).  
Run it automatically on a **second monitor** alongside `GRW.exe` or open it from any **tablet, laptop, or smartphone** on your local network.

---

## Features

- **Multi-LOD 32K Tactical Map of Bolivia** — Extracts tiles on demand directly from your local `gr.wmap` (Satellite), `gr_h.wmap` (Skell Technology Heatmap), and `DataPC.forge` (official province masks & AnvilNext 2.0 icons) at 60 FPS (`Canvas 2D` + zoom/pan + player trail + custom tactical pins). Zero copyrighted game assets are bundled.
- **Live Stealth Telemetry & "Safe to Fire" HUD** — Tracks nearby enemies, head look direction, FOV vision cones, your equipped weapon's suppressed/unsuppressed acoustic radius, and evaluates **Safe to Fire** in real time.
- **Automatic Aim Shot & Kill-Witness Warnings** — When you aim at an enemy, Ghost Tactical Pad checks every other enemy nearby and warns immediately if:
  1. Anyone would **hear** the gunshot or bullet impact (**Sound Alert**).
  2. Anyone has line of sight (head orientation, FOV cone, and 3D / heightmap terrain occlusion) to **see** the target being killed (**Visual Witness Alert**).
- **Solo AI & Co-op Ally Tracking** — Recognizes both Solo AI squadmates and Co-op human teammates, automatically firing the same gunshot-hearing and kill-witness alerts whenever an ally aims at an enemy so you can coordinate silent sync shots.
- **Complete Weapons, Attachments & Intel Database** — Searchable catalog covering **59 weapons** (with acoustic profiles), **66 attachments**, **10 bonus medals**, **21 provinces**, **4 cartel wings**, and **12 POI categories**, showing exact province/region unlock locations with one-click **Show on Map**, progress checkboxes, and cartel hierarchy tracking.
- **100% Customizable Overlays & Rules** — Toggle and tune every overlay, vision cone, noise ring, ally filter (Solo/Co-op), FOV width/range, and alert threshold individually. Preferences persist automatically to `data/settings.json` and browser storage.
- **Zero-AV-Flag Standalone Distribution** — Uses a pure native `winmm.dll` x64 proxy (`KERNEL32.dll` import only) paired with the official PSF embedded Python 3.12 runtime — **0 `.exe` files** and **0 nested archives** in the release zip. EasyAntiCheat is no longer shipped with Steam Title Update 25 (`GRW.exe`), allowing `winmm.dll` telemetry cleanly in Solo and Co-op.

---

## Installation (Pre-Built Release)

1. Download and extract **`GhostPad_GRW_v1.0.0.zip`**.
2. Run **`Instalar Mod na Pasta do Jogo.bat`** *or* copy `winmm.dll` and the `GhostPad\` folder next to `GRW.exe` inside your game directory (e.g. `C:\Program Files (x86)\Steam\steamapps\common\Wildlands\`).
3. Launch **Ghost Recon Wildlands** normally. Ghost Tactical Pad starts its local HTTP/SSE server on port **`8766`** and opens automatically on your secondary display (or at `http://127.0.0.1:8766` / your LAN IP shown in the top bar).

> **Standalone / Offline Mode:** You can also run **`Iniciar Ghost Pad.bat`** (`python launcher.py`) anytime without opening the game to browse the Bolivia map, plan routes, and check where to find every weapon, attachment, medal, and cartel target.

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

`build_proxy.py` compiles `winmm.dll` (`181` forwarded WinMM exports + Title Update 25 read-only observer hooks + native LZO1X decompressor), packages the official PSF embedded Python runtime into `mod_release/`, validates clean PE/zip rules (`0` `.exe` files, `0` nested archives, `KERNEL32.dll`-only import table), and produces `GhostPad_GRW_v1.0.0.zip`.

### Running Tests

```bat
python -m unittest discover -s tests -v
```

---

## Customization & Controls

Open the **Settings** panel in the UI to customize every aspect independently:
- Map layer (**Satellite**, **Skell Heatmap**), province borders, cartel hierarchy overlays, player trail, and tactical drone marker.
- Acoustic circles (unsuppressed/suppressed weapon noise & bullet impact distance) and "Safe to Fire" HUD banner.
- Enemy FOV cones (detection range, horizontal cone angle, terrain occlusion toggle).
- Ally alerts (**Solo AI** and/or **Co-op Teammates** aim detection for heard shots and visual kill witnesses).
- Automatic language switching (**English** / **Português (BR)**, auto-detected from Steam ACF or Windows locale).

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

- **Mapa Tático 32K da Bolívia em 60 FPS** — Lê diretamente os arquivos locais do seu jogo (`gr.wmap` Satélite, `gr_h.wmap` Mapa de Calor Skell e `DataPC.forge` com máscaras de província e ícones oficiais), sem distribuir nenhum arquivo protegido do jogo.
- **Telemetria Stealth & Indicador "Seguro para Atirar"** — Exibe posição dos inimigos, direção do olhar, cones de visão, raio de barulho da arma equipada (com e sem silenciador) e indicador ao vivo informando se um disparo agora seria ouvido ou visto.
- **Detecção Automática ao Mirar (Som + Testemunha Visual)** — Ao mirar em qualquer inimigo, o sistema avisa automaticamente se algum outro inimigo vai **ouvir o tiro / impacto** ou **ver o abate** (considerando campo de visão e oclusão de terreno).
- **Aliados Solo (IA) e Co-op (Jogadores)** — Reconhece os membros do seu esquadrão no modo Solo e aliados humanos no Co-op, gerando os mesmos alertas de som e testemunha visual sempre que um aliado mirar em um inimigo.
- **Database Completo de Armas, Acessórios e Itens** — Catálogo pesquisável com **59 armas**, **66 acessórios**, **10 medalhas de bônus**, **21 províncias**, **4 alas do cartel** e **12 categorias de POI**, mostrando **onde conseguir cada item** com botão **Mostrar no Mapa** e checklist de progresso.
- **Totalmente Customizável** — Todos os overlays, raios acústicos, ângulos de visão, filtros de aliados Solo/Co-op, alertas visuais/sonoros e marcadores podem ser ativados, desativados e ajustados individualmente.
- **Instalação Limpa e Segura** — Proxy nativo `winmm.dll` + Python 3.12 oficial embarcado (`0` `.exe`, `0` zips aninhados). Basta extrair `GhostPad_GRW_v1.0.0.zip` e executar `Instalar Mod na Pasta do Jogo.bat` (ou copiar `winmm.dll` e `GhostPad\` para a pasta de `GRW.exe`), ou abrir `Iniciar Ghost Pad.bat` para usar o mapa e catálogo offline.
