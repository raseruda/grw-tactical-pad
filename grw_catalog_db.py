"""Banco de dados completo de Ghost Recon Wildlands: 21 províncias, Cartel, Armas, Acessórios, Medalhas, Bases, SAMs e Rebel Ops."""
from __future__ import annotations

from typing import Any

# Perfis acústicos verificados no motor do GRW (distância máxima de detecção de disparo em metros)
WEAPON_ACOUSTICS: dict[str, dict[str, float]] = {
    "pistol": {"suppressed_m": 18.0, "unsuppressed_m": 49.0},
    "smg": {"suppressed_m": 23.0, "unsuppressed_m": 61.0},
    "ar": {"suppressed_m": 34.0, "unsuppressed_m": 93.0},
    "lmg": {"suppressed_m": 40.0, "unsuppressed_m": 109.0},
    "shotgun": {"suppressed_m": 41.0, "unsuppressed_m": 109.0},
    "sniper": {"suppressed_m": 48.0, "unsuppressed_m": 130.0},
}

CARTEL_WINGS: list[dict[str, Any]] = [
    {
        "id": "security",
        "name_en": "Security Wing",
        "name_pt": "Ala de Segurança",
        "head": "El Muro",
        "color": "#ef4444",
        "desc_en": "Cartel armed enforcers, Sicario training camps, and Unidad bribery.",
        "desc_pt": "Braço armado do cartel, campos de treinamento de sicários e suborno da Unidad.",
    },
    {
        "id": "smuggling",
        "name_en": "Smuggling Wing",
        "name_pt": "Ala de Contrabando",
        "head": "Nidia Flores",
        "color": "#f59e0b",
        "desc_en": "Airfields, Narco-subs, border routes, and cartel money laundering.",
        "desc_pt": "Aeródromos, narco-submarinos, rotas de fronteira e lavagem de dinheiro.",
    },
    {
        "id": "production",
        "name_en": "Production Wing",
        "name_pt": "Ala de Produção",
        "head": "El Yayo",
        "color": "#22c55e",
        "desc_en": "Coca plantations, paste labs, chemical processing, and refineries.",
        "desc_pt": "Plantações de coca, laboratórios de pasta, processamento químico e refinarias.",
    },
    {
        "id": "influence",
        "name_en": "Influence Wing",
        "name_pt": "Ala de Influência",
        "head": "El Cardenal",
        "color": "#a855f7",
        "desc_en": "Santa Muerte cult, cartel propaganda, radio networks, and corruption.",
        "desc_pt": "Culto à Santa Muerte, propaganda do cartel, rádios e corrupção política.",
    },
]

# As 21 províncias da Bolívia com coordenadas normalizadas (u, v) alinhadas ao gr.wmap
PROVINCES: list[dict[str, Any]] = [
    {"id": "itacua", "name": "Itacua", "wing": "security", "boss": "La Yuri & El Polito", "skulls": 1, "u": 0.52, "v": 0.62, "biome_en": "Highland Valley", "biome_pt": "Vale Serrano", "desc_en": "Starting province controlled by cartel torturers La Yuri & El Polito.", "desc_pt": "Província inicial controlada pelos torturadores La Yuri e El Polito."},
    {"id": "ocoro", "name": "Ocoro", "wing": "production", "boss": "El Emisario", "skulls": 2, "u": 0.53, "v": 0.49, "biome_en": "Subtropical River Valley", "biome_pt": "Vale Fluvial Subtropical", "desc_en": "Coca processing hub between Agua Verde and Itacua.", "desc_pt": "Centro de processamento de coca entre Agua Verde e Itacua."},
    {"id": "agua_verde", "name": "P.N. de Agua Verde", "wing": "influence", "boss": "Carzita", "skulls": 2, "u": 0.50, "v": 0.30, "biome_en": "Lake & Resorts", "biome_pt": "Lago e Resorts", "desc_en": "Luxury lake resorts used to entertain corrupt politicians and VIPs.", "desc_pt": "Resorts luxuosos usados para corromper políticos e VIPs."},
    {"id": "barvechos", "name": "Barvechos", "wing": "smuggling", "boss": "El Pulpo", "skulls": 3, "u": 0.34, "v": 0.50, "biome_en": "Arid Plateau & Mines", "biome_pt": "Planalto Árido e Minas", "desc_en": "Cartel accounting and mineral smuggling corridor.", "desc_pt": "Contabilidade do cartel e corredor de contrabando mineral."},
    {"id": "mojocoyo", "name": "Mojocoyo", "wing": "smuggling", "boss": "Antonio", "skulls": 3, "u": 0.17, "v": 0.53, "biome_en": "Crater Lake & Highlands", "biome_pt": "Lago de Cratera e Planalto", "desc_en": "Stockpiles and air-drop staging grounds around a volcanic lake.", "desc_pt": "Estoques de carga e zonas de entrega ao redor de um lago vulcânico."},
    {"id": "san_mateo", "name": "San Mateo", "wing": "security", "boss": "El Pozolero", "skulls": 3, "u": 0.33, "v": 0.35, "biome_en": "Dry Canyons", "biome_pt": "Cânions Secos", "desc_en": "Disposal grounds and prison camps overseen by El Pozolero.", "desc_pt": "Campos de eliminação e prisões comandados por El Pozolero."},
    {"id": "tabacal", "name": "Tabacal", "wing": "production", "boss": "Madre Coca", "skulls": 2, "u": 0.53, "v": 0.14, "biome_en": "Lush Coca Valleys", "biome_pt": "Vales de Coca", "desc_en": "Heartland of traditional coca farming guarded by Madre Coca.", "desc_pt": "Coração do cultivo tradicional de coca protegido por Madre Coca."},
    {"id": "espiritu_santo", "name": "Espíritu Santo", "wing": "influence", "boss": "La Santera", "skulls": 3, "u": 0.80, "v": 0.15, "biome_en": "Misty Cloud Forest", "biome_pt": "Floresta Nebulosa", "desc_en": "Pilgrimage site and shrine headquarters of the Santa Muerte cult.", "desc_pt": "Sítio de peregrinação e sede do culto à Santa Muerte."},
    {"id": "monte_puncu", "name": "Monte Puncu", "wing": "influence", "boss": "DJ Perico", "skulls": 3, "u": 0.72, "v": 0.28, "biome_en": "Mountain Jungle", "biome_pt": "Selva Serrana", "desc_en": "Propaganda radio relay hills and jungle towns.", "desc_pt": "Colinas das torres de rádio de propaganda e vilas na selva."},
    {"id": "villa_verde", "name": "Villa Verde", "wing": "production", "boss": "El Wey", "skulls": 2, "u": 0.69, "v": 0.48, "biome_en": "Tropical Jungle", "biome_pt": "Selva Tropical", "desc_en": "Jungle chemical labs and river docks.", "desc_pt": "Laboratórios químicos na selva e docas fluviais."},
    {"id": "caimanes", "name": "Caimanes", "wing": "smuggling", "boss": "El Cerebro", "skulls": 4, "u": 0.86, "v": 0.48, "biome_en": "Swamp Delta", "biome_pt": "Pântano e Delta", "desc_en": "Flooded swamp shipyards building narco-submarines.", "desc_pt": "Estaleiros escondidos no pântano para construir narco-submarinos."},
    {"id": "la_cruz", "name": "La Cruz", "wing": "smuggling", "boss": "El Boquita", "skulls": 2, "u": 0.62, "v": 0.64, "biome_en": "Forest & Towns", "biome_pt": "Florestas e Vilas", "desc_en": "Transit crossroads connecting southern production to eastern rivers.", "desc_pt": "Entroncamento logístico ligando o sul produtor aos rios do leste."},
    {"id": "libertad", "name": "Libertad", "wing": "production", "boss": "Marcus Jensen", "skulls": 4, "u": 0.82, "v": 0.66, "biome_en": "Industrial City", "biome_pt": "Cidade Industrial", "desc_en": "Industrial chemical plants producing pure cocaine at scale.", "desc_pt": "Complexo químico industrial produzindo cocaína pura em escala."},
    {"id": "flor_de_oro", "name": "Flor de Oro", "wing": "security", "boss": "General Baro", "skulls": 5, "u": 0.78, "v": 0.85, "biome_en": "Fortified Jungle", "biome_pt": "Selva Fortificada", "desc_en": "Heavily fortified Unidad border stronghold commanded by General Baro.", "desc_pt": "Fortaleza fronteiriça da Unidad comandada pelo General Baro."},
    {"id": "pucara", "name": "Pucara", "wing": "influence", "boss": "El Yayo (Operações)", "skulls": 3, "u": 0.57, "v": 0.84, "biome_en": "Ancient Ruins & Canyons", "biome_pt": "Ruínas e Cânions", "desc_en": "Southern ruins and cartel-pressured Aymara villages.", "desc_pt": "Ruínas ancestrais e vilarejos aymaras sob pressão do cartel."},
    {"id": "remanzo", "name": "Remanzo", "wing": "production", "boss": "El Gato", "skulls": 3, "u": 0.44, "v": 0.76, "biome_en": "Livestock Farmlands", "biome_pt": "Fazendas e Pastagens", "desc_en": "Slaughterhouses and livestock ranches hiding drug packaging.", "desc_pt": "Matadouros e fazendas usados para embalar carregamentos."},
    {"id": "malca", "name": "Malca", "wing": "influence", "boss": "El Chido / El Cardenal", "skulls": 3, "u": 0.34, "v": 0.76, "biome_en": "Red Rock Canyons", "biome_pt": "Cânions Vermelhos", "desc_en": "Cathedral stronghold of El Cardenal and narcocorrido concerts.", "desc_pt": "Catedral fortaleza de El Cardenal e palco de narcocorridos."},
    {"id": "montuyoc", "name": "Montuyoc", "wing": "security", "boss": "Carl Bookhart", "skulls": 4, "u": 0.22, "v": 0.68, "biome_en": "Alpine Military Range", "biome_pt": "Cordilheira Militar", "desc_en": "High-altitude sicario training bases run by Carl Bookhart.", "desc_pt": "Bases de treinamento de altitude comandadas por Carl Bookhart."},
    {"id": "inca_camina", "name": "Inca Camina", "wing": "smuggling", "boss": "La Cabra", "skulls": 5, "u": 0.18, "v": 0.86, "biome_en": "Snowy Peaks & Craters", "biome_pt": "Picos Nevados e Crateras", "desc_en": "Peruvian smuggling pass across freezing Andean mountain peaks.", "desc_pt": "Rota de contrabando peruana pelos picos nevados dos Andes."},
    {"id": "media_luna", "name": "Media Luna", "wing": "security", "boss": "El Comandante / El Muro", "skulls": 5, "u": 0.31, "v": 0.13, "biome_en": "Canyon Fortress", "biome_pt": "Cânion Fortaleza", "desc_en": "Deadly canyon airspace packed with SAM batteries and M.O.B. Condor.", "desc_pt": "Desfiladeiro mortal repleto de baterias SAM e a base M.O.B. Condor."},
    {"id": "koani", "name": "Koani", "wing": "smuggling", "boss": "Boston Reed", "skulls": 5, "u": 0.14, "v": 0.13, "biome_en": "Salt Flats", "biome_pt": "Salar de Uyuni", "desc_en": "Expansive white salt flats, train depot, and smuggling airbase.", "desc_pt": "Planície branca de sal, pátio ferroviário e base aérea de contrabando."},
]

# Catálogo de Armas (todas as armas base desbloqueáveis + chefes + iniciais)
# Estatísticas normalizadas 0..100 para UI de Armeiro + perfil acústico exato por classe
def _w(
    wid: str,
    name: str,
    wclass: str,
    prov: str,
    loc_en: str,
    loc_pt: str,
    u: float,
    v: float,
    obtain: str = "weapon_case",
    dmg: int = 55,
    acc: int = 60,
    han: int = 60,
    rng: int = 55,
    rof: int = 65,
    pen: int = 50,
    noise_stat: int = 55,
    suppressed_default: bool = True,
    desc_en: str = "",
    desc_pt: str = "",
) -> dict[str, Any]:
    ac = WEAPON_ACOUSTICS[wclass]
    return {
        "id": wid,
        "kind": "weapon",
        "name": name,
        "weapon_class": wclass,
        "province": prov,
        "location_en": loc_en,
        "location_pt": loc_pt,
        "u": round(u, 4),
        "v": round(v, 4),
        "obtain_type": obtain,
        "noise_suppressed_m": ac["suppressed_m"],
        "noise_unsuppressed_m": ac["unsuppressed_m"],
        "suppressible": True,
        "suppressed_default": suppressed_default,
        "stats": {
            "damage": dmg,
            "accuracy": acc,
            "handling": han,
            "range": rng,
            "rof": rof,
            "penetration": pen,
            "noise": noise_stat,
        },
        "desc_en": desc_en or f"{name} ({wclass.upper()}) — found at {loc_en}.",
        "desc_pt": desc_pt or f"{name} ({wclass.upper()}) — encontrada em {loc_pt}.",
    }


WEAPONS_DB: list[dict[str, Any]] = [
    # --- Assault Rifles ---
    _w("wp_p416", "P416", "ar", "itacua", "Starter Loadout / Itacua Armory", "Equipamento Inicial / Arsenal de Itacua", 0.515, 0.625, "starter", 48, 62, 70, 52, 74, 48, 55, True, "Balanced starting 5.56mm assault rifle.", "Fuzil de assalto 5.56mm inicial equilibrado."),
    _w("wp_m4a1", "M4A1", "ar", "flor_de_oro", "Armadillo / Southern Unidad Outpost", "Posto Avançado da Unidad Sul (Flor de Oro)", 0.765, 0.855, "weapon_case", 54, 65, 68, 56, 82, 50, 58),
    _w("wp_acr", "ACR", "ar", "media_luna", "Culta Outpost (Media Luna)", "Posto Avançado Culta (Media Luna)", 0.305, 0.145, "weapon_case", 56, 74, 66, 62, 68, 54, 58),
    _w("wp_mk17", "MK17 (SCAR-H)", "ar", "flor_de_oro", "M.O.B. Jaguar / Southern Bunker", "Bunker Sul / Base Unidad (Flor de Oro)", 0.802, 0.872, "weapon_case", 72, 70, 52, 68, 56, 72, 50),
    _w("wp_tar21", "TAR-21", "ar", "montuyoc", "Chavina Training Center Armory", "Arsenal do Centro de Treinamento Chavina", 0.215, 0.662, "weapon_case", 55, 68, 72, 58, 78, 52, 58),
    _w("wp_auga3", "AUG A3", "ar", "barvechos", "Barvechos Mine Compound", "Complexo da Mina de Barvechos", 0.342, 0.482, "weapon_case", 56, 72, 66, 60, 66, 52, 58),
    _w("wp_556xi", "556xi", "ar", "caimanes", "Caimanes Swamp Outpost", "Posto no Pântano de Caimanes", 0.855, 0.462, "weapon_case", 58, 64, 65, 60, 68, 55, 56),
    _w("wp_ak47", "AK-47", "ar", "libertad", "Libertad City Cartel Barracks", "Quartel do Cartel em Libertad", 0.830, 0.672, "weapon_case", 66, 54, 58, 54, 60, 66, 48),
    _w("wp_ak12", "AK-12", "ar", "tabacal", "Tabacal Coca Processing Plant", "Usina de Processamento de Tabacal", 0.542, 0.128, "weapon_case", 60, 68, 62, 60, 64, 58, 54),
    _w("wp_r5rgp", "R5 RGP", "ar", "remanzo", "Remanzo Cartel Depot", "Depósito do Cartel em Remanzo", 0.448, 0.742, "weapon_case", 57, 70, 64, 58, 62, 54, 56),
    _w("wp_g2", "FAMAS G2", "ar", "inca_camina", "Inca Camina Southern Outpost", "Posto Avançado Sul de Inca Camina", 0.168, 0.875, "weapon_case", 52, 64, 74, 54, 86, 50, 56),
    _w("wp_805bren", "805 Bren A2", "ar", "villa_verde", "Villa Verde North Lab", "Laboratório Norte de Villa Verde", 0.682, 0.465, "weapon_case", 58, 70, 64, 60, 66, 55, 56),
    _w("wp_l85a2", "L85A2", "ar", "espiritu_santo", "Espíritu Santo Shrine Compound", "Complexo do Santuário de Espíritu Santo", 0.812, 0.155, "weapon_case", 54, 73, 66, 62, 64, 54, 58),
    _w("wp_sr3m", "SR3M", "ar", "agua_verde", "Arroyo Baya Northern Outpost", "Posto Norte de Arroyo Baya (Agua Verde)", 0.548, 0.295, "weapon_case", 62, 62, 70, 50, 74, 62, 64),
    _w("wp_ritmo", "Ritmo (Boss)", "ar", "ocoro", "Defeat El Emisario in Ocoro", "Derrote El Emisario em Ocoro", 0.530, 0.502, "boss_reward", 58, 66, 68, 56, 70, 56, 54),

    # --- Sniper Rifles ---
    _w("wp_m40a5", "M40A5", "sniper", "itacua", "Itacua Echo Safe House Bunker", "Bunker Próximo a Itacua Echo", 0.502, 0.605, "weapon_case", 78, 82, 50, 82, 22, 74, 42),
    _w("wp_hti", "HTI", "sniper", "montuyoc", "Chavina Training Center South", "Sul do Centro de Treinamento Chavina", 0.238, 0.692, "weapon_case", 98, 76, 30, 96, 16, 98, 28, True, "Anti-materiel .50 cal rifle capable of 1-shotting helicopters.", "Rifle antimaterial .50 capaz de destruir helicópteros com 1 tiro."),
    _w("wp_msr", "MSR", "sniper", "montuyoc", "Choza Padre Mine Outpost", "Posto da Mina Choza Padre (Montuyoc)", 0.195, 0.658, "weapon_case", 90, 86, 42, 94, 24, 88, 36),
    _w("wp_l115a3", "L115A3", "sniper", "monte_puncu", "Monte Puncu Radio Outpost", "Posto de Rádio de Monte Puncu", 0.728, 0.292, "weapon_case", 88, 84, 46, 92, 22, 85, 38),
    _w("wp_mk14", "Mk14", "sniper", "koani", "Koani Train Cemetery Outpost", "Posto do Cemitério de Trens de Koani", 0.132, 0.145, "weapon_case", 72, 78, 56, 80, 54, 70, 48),
    _w("wp_g28", "G28", "sniper", "san_mateo", "San Mateo Cartel Camp", "Acampamento do Cartel em San Mateo", 0.342, 0.342, "weapon_case", 70, 80, 58, 78, 56, 68, 50),
    _w("wp_sr25", "SR25", "sniper", "caimanes", "Caimanes Base Building 2F", "Base de Caimanes (2º Andar)", 0.872, 0.495, "weapon_case", 74, 78, 54, 82, 52, 72, 48),
    _w("wp_svd", "Dragunov SVD", "sniper", "agua_verde", "Agua Verde Eastern Dock", "Docas Leste de Agua Verde", 0.535, 0.315, "weapon_case", 76, 74, 52, 80, 50, 74, 46),
    _w("wp_srsa1", "SRSA1", "sniper", "mojocoyo", "Mojocoyo Lakeside Outpost", "Posto à Beira do Lago de Mojocoyo", 0.185, 0.515, "weapon_case", 82, 84, 60, 82, 24, 76, 45),
    _w("wp_m1891", "M1891", "sniper", "libertad", "Libertad Southern Mansion", "Mansão Sul de Libertad", 0.808, 0.692, "weapon_case", 84, 72, 52, 80, 26, 78, 40),
    _w("wp_sr1", "SR-1", "sniper", "koani", "Koani Salt Flats Research Base", "Base de Pesquisa do Salar de Koani", 0.155, 0.112, "weapon_case", 85, 84, 48, 88, 22, 82, 42),

    # --- Submachine Guns (SMGs) ---
    _w("wp_mp5", "MP5", "smg", "itacua", "Itacua Western Outpost", "Posto Oeste de Itacua", 0.488, 0.618, "weapon_case", 42, 68, 82, 40, 76, 38, 74),
    _w("wp_mp7", "MP7", "smg", "barvechos", "Barvechos Town Safe House", "Casa Segura da Cidade de Barvechos", 0.322, 0.512, "weapon_case", 44, 66, 84, 42, 84, 48, 74),
    _w("wp_vector", "Vector .45 ACP", "smg", "media_luna", "M.O.B. Condor Hangar (Media Luna)", "Hangar de M.O.B. Condor (Media Luna)", 0.325, 0.122, "weapon_case", 46, 68, 80, 38, 95, 40, 76),
    _w("wp_p90", "P90", "smg", "la_cruz", "La Cruz Town Outpost", "Posto da Cidade de La Cruz", 0.625, 0.635, "weapon_case", 43, 66, 82, 44, 86, 50, 72),
    _w("wp_scorpion", "Scorpion EVO 3", "smg", "mojocoyo", "Mojocoyo Cartel Depot", "Depósito do Cartel em Mojocoyo", 0.158, 0.542, "weapon_case", 44, 70, 82, 42, 88, 42, 74),
    _w("wp_pp19", "PP19", "smg", "agua_verde", "Agua Verde Island Casino", "Cassino da Ilha em Agua Verde", 0.495, 0.292, "weapon_case", 45, 66, 78, 42, 72, 40, 72),
    _w("wp_sr635", "SR-635", "smg", "ocoro", "Ocoro Northern Checkpoint", "Bloqueio Norte de Ocoro", 0.525, 0.472, "weapon_case", 46, 68, 80, 44, 76, 42, 72),
    _w("wp_psg", "PSG", "smg", "san_mateo", "La Carcel Del Pueblo (San Mateo)", "La Cárcel del Pueblo (San Mateo)", 0.318, 0.365, "weapon_case", 43, 72, 82, 42, 74, 40, 74),
    _w("wp_9x19vsn", "9x19VSN", "smg", "inca_camina", "Inca Camina Northern Camp", "Acampamento Norte de Inca Camina", 0.178, 0.835, "weapon_case", 44, 68, 80, 42, 76, 40, 74),
    _w("wp_9mmc1", "9mm C1", "smg", "remanzo", "Remanzo Slaughterhouse", "Matadouro de Remanzo", 0.428, 0.768, "weapon_case", 45, 64, 78, 42, 68, 40, 72),
    _w("wp_mpx", "MPX", "smg", "monte_puncu", "Monte Puncu Sawmill", "Serraria de Monte Puncu", 0.712, 0.268, "weapon_case", 44, 72, 84, 44, 78, 42, 74),
    _w("wp_smg11", "SMG-11", "smg", "pucara", "Pucara Ruins Compound", "Complexo das Ruínas de Pucara", 0.562, 0.835, "weapon_case", 40, 56, 90, 34, 96, 36, 76),

    # --- Light Machine Guns (LMGs) ---
    _w("wp_mk48", "Mk 48", "lmg", "espiritu_santo", "Espíritu Santo Western Base", "Base Oeste de Espíritu Santo", 0.785, 0.145, "weapon_case", 64, 58, 36, 64, 68, 66, 38),
    _w("wp_stoner", "Stoner LMG A1", "lmg", "pucara", "Pucara Cartel Bunker", "Bunker do Cartel em Pucara", 0.578, 0.852, "weapon_case", 60, 64, 46, 60, 72, 62, 46),
    _w("wp_mk249", "Mk249", "lmg", "malca", "Malca Unidad Outpost", "Posto Avançado da Unidad em Malca", 0.352, 0.748, "weapon_case", 58, 60, 42, 58, 76, 60, 42),
    _w("wp_6p41", "6P41", "lmg", "media_luna", "Media Luna Airfield South", "Sul do Aeródromo de Media Luna", 0.295, 0.152, "weapon_case", 68, 56, 34, 66, 64, 70, 36),
    _w("wp_type95", "Type 95", "lmg", "remanzo", "Remanzo Southern Ranch", "Fazenda Sul de Remanzo", 0.455, 0.778, "weapon_case", 60, 66, 48, 60, 68, 60, 44),
    _w("wp_mg121", "MG121", "lmg", "itacua", "Itacua Southern Construction Site", "Obra / Heliponto Sul de Itacua", 0.532, 0.642, "weapon_case", 62, 58, 40, 60, 70, 64, 40),
    _w("wp_llamativo", "Llamativo (Boss)", "lmg", "agua_verde", "Defeat Carzita in Agua Verde", "Derrote Carzita em Agua Verde", 0.502, 0.305, "boss_reward", 64, 62, 42, 62, 72, 64, 40),

    # --- Shotguns ---
    _w("wp_supershorty", "Super Shorty", "shotgun", "itacua", "F.O.B. Armadillo Roof (Itacua)", "Telhado da F.O.B. Armadillo (Itacua)", 0.558, 0.618, "weapon_case", 78, 40, 74, 24, 30, 52, 42),
    _w("wp_sasg12", "SASG-12", "shotgun", "agua_verde", "Agua Verde NE Outpost", "Posto Nordeste de Agua Verde", 0.538, 0.275, "weapon_case", 76, 46, 60, 28, 58, 54, 40),
    _w("wp_spas12", "SPAS-12", "shotgun", "la_cruz", "La Cruz Northern Warehouse", "Armazém Norte de La Cruz", 0.615, 0.618, "weapon_case", 82, 48, 56, 30, 48, 56, 38),
    _w("wp_m1014", "M1014", "shotgun", "koani", "Koani Train Yard", "Pátio Ferroviário de Koani", 0.148, 0.125, "weapon_case", 80, 48, 58, 30, 52, 56, 40),
    _w("wp_elobsequio", "El Obsequio (Boss)", "shotgun", "barvechos", "Defeat El Pulpo in Barvechos", "Derrote El Pulpo em Barvechos", 0.342, 0.502, "boss_reward", 84, 52, 62, 32, 46, 58, 44),

    # --- Handguns / Pistols ---
    _w("wp_p45t", "P45T", "pistol", "itacua", "Starter Sidearm", "Arma Secundária Inicial", 0.518, 0.628, "starter", 38, 60, 86, 26, 58, 32, 84),
    _w("wp_p12", "P12", "pistol", "tabacal", "Tabacal River Dock", "Doca Fluvial de Tabacal", 0.518, 0.148, "weapon_case", 40, 62, 86, 28, 58, 34, 84),
    _w("wp_m9", "M9", "pistol", "villa_verde", "Villa Verde River Outpost", "Posto Fluvial de Villa Verde", 0.695, 0.495, "weapon_case", 36, 64, 88, 28, 64, 30, 86),
    _w("wp_57usg", "5.7 USG", "pistol", "ocoro", "Ocoro Town Outpost", "Posto da Vila de Ocoro", 0.538, 0.502, "weapon_case", 42, 68, 88, 32, 64, 46, 84),
    _w("wp_m1911", "M1911", "pistol", "ocoro", "Ocoro Southern Farm", "Fazenda Sul de Ocoro", 0.518, 0.515, "weapon_case", 44, 60, 84, 26, 54, 36, 82),
    _w("wp_d50", "D-50 (Desert Eagle)", "pistol", "libertad", "Libertad Northern Outpost", "Posto Norte de Libertad", 0.818, 0.635, "weapon_case", 64, 54, 68, 34, 38, 58, 60),
    _w("wp_p227", "P227", "pistol", "malca", "Malca Cartel House", "Casa do Cartel em Malca", 0.328, 0.772, "weapon_case", 41, 64, 86, 28, 60, 34, 84),
    _w("wp_ladykiller", "Lady Killer (Boss)", "pistol", "itacua", "Defeat La Yuri & El Polito in Itacua", "Derrote La Yuri e El Polito em Itacua", 0.524, 0.616, "boss_reward", 48, 66, 86, 28, 60, 38, 86),
    _w("wp_skorpion", "Skorpion", "pistol", "remanzo", "Remanzo Unidad Outpost", "Posto da Unidad em Remanzo", 0.435, 0.752, "weapon_case", 36, 52, 86, 26, 84, 32, 80),
]


def _att(
    aid: str,
    name: str,
    slot: str,
    compat: list[str],
    prov: str,
    loc_en: str,
    loc_pt: str,
    u: float,
    v: float,
    effect_en: str,
    effect_pt: str,
) -> dict[str, Any]:
    return {
        "id": aid,
        "kind": "attachment",
        "name": name,
        "slot": slot,
        "compatible_classes": compat,
        "province": prov,
        "location_en": loc_en,
        "location_pt": loc_pt,
        "u": round(u, 4),
        "v": round(v, 4),
        "effect_en": effect_en,
        "effect_pt": effect_pt,
        "desc_en": f"{name} ({slot}) — {effect_en}",
        "desc_pt": f"{name} ({slot}) — {effect_pt}",
    }


ATTACHMENTS_DB: list[dict[str, Any]] = [
    # Itacua
    _att("att_ar_long_barrel", "Long Barrel (AR)", "barrel", ["ar"], "itacua", "Itacua Northern Outpost", "Posto Norte de Itacua", 0.512, 0.595, "+Damage, +Accuracy, +Range, -Handling", "+Dano, +Precisão, +Alcance, -Manuseio"),
    _att("att_panoramic", "Panoramic Sight", "scope", ["ar", "smg", "lmg", "shotgun"], "itacua", "Itacua Central Village", "Vila Central de Itacua", 0.525, 0.620, "Clear 1x holographic reflex optic", "Mira holográfica limpa 1x"),
    _att("att_pkas", "PK-AS Sight", "scope", ["ar", "smg"], "itacua", "Itacua Eastern Farm", "Fazenda Leste de Itacua", 0.542, 0.628, "+Accuracy (1.5x Russian collimator)", "+Precisão (colimador russo 1.5x)"),
    # Ocoro
    _att("att_pistol_extmag", "Extended Mag 30 (Handgun)", "magazine", ["pistol"], "ocoro", "Ocoro East Checkpoint", "Bloqueio Leste de Ocoro", 0.548, 0.492, "+Magazine capacity, -Handling", "+Capacidade do carregador, -Manuseio"),
    _att("att_compm4", "CompM4 Scope", "scope", ["ar", "smg", "lmg"], "ocoro", "Ocoro Central Outpost", "Posto Central de Ocoro", 0.532, 0.488, "+Accuracy (Red dot reflex)", "+Precisão (Ponto vermelho)"),
    _att("att_sr_comp_stock", "Compensated Buttstock (Sniper)", "stock", ["sniper"], "ocoro", "Ocoro West Camp", "Acampamento Oeste de Ocoro", 0.512, 0.495, "+Accuracy, +Handling", "+Precisão, +Manuseio"),
    _att("att_smg_atpial", "ATPIAL Laser Sight (SMG)", "rail", ["smg"], "ocoro", "Ocoro River Base", "Base do Rio de Ocoro", 0.526, 0.506, "+Hip-fire Accuracy & Handling", "+Precisão sem mira e Manuseio"),
    # Tabacal
    _att("att_ar_ext30", "Extended Mag 30 (AR 5.56)", "magazine", ["ar"], "tabacal", "Tabacal North Farm", "Fazenda Norte de Tabacal", 0.515, 0.125, "+Magazine capacity (30 rds)", "+Capacidade (30 munições)"),
    _att("att_sg_long_barrel", "Long Barrel (Shotgun)", "barrel", ["shotgun"], "tabacal", "Tabacal Eastern Village", "Vila Leste de Tabacal", 0.548, 0.142, "+Damage, +Range, +Accuracy", "+Dano, +Alcance, +Precisão"),
    _att("att_smg_folded", "Folded Buttstock (SMG)", "stock", ["smg"], "tabacal", "Tabacal South Outpost", "Posto Sul de Tabacal", 0.532, 0.158, "+Handling, -Accuracy", "+Manuseio, -Precisão"),
    _att("att_smg_3dot", "Laser 3Dot (SMG)", "rail", ["smg"], "tabacal", "Tabacal West Ridge", "Crista Oeste de Tabacal", 0.505, 0.140, "+Hip-fire spread control", "+Controle de dispersão no quadril"),
    # Agua Verde
    _att("att_sg_suppressor", "Shotgun Suppressor", "muzzle", ["shotgun"], "agua_verde", "Agua Verde North Villa", "Vila Norte de Agua Verde", 0.512, 0.278, "Reduces shotgun gunshot hearing to ~41m", "Reduz audibilidade da escopeta para ~41m"),
    _att("att_ar_micro_t1", "Micro T-1 Scope", "scope", ["ar", "smg"], "agua_verde", "Agua Verde West Shore", "Margem Oeste de Agua Verde", 0.478, 0.305, "+Handling, compact 1x reflex", "+Manuseio, mira reflex compacta"),
    # Barvechos
    _att("att_hg_atpial", "ATPIAL Laser Sight (Handgun)", "rail", ["pistol"], "barvechos", "Barvechos North Quarry", "Pedreira Norte de Barvechos", 0.335, 0.475, "+Handling, +Accuracy", "+Manuseio, +Precisão"),
    _att("att_lmg_long", "Long Barrel (LMG)", "barrel", ["lmg"], "barvechos", "Barvechos East Mine", "Mina Leste de Barvechos", 0.358, 0.498, "+Damage, +Range", "+Dano, +Alcance"),
    _att("att_smg_comp", "Compensator (SMG)", "muzzle", ["smg"], "barvechos", "Barvechos South Depot", "Depósito Sul de Barvechos", 0.328, 0.522, "+Recoil control, unsuppressed (~61m noise)", "+Controle de recuo, sem silenciador (~61m)"),
    _att("att_smg_short", "Short Barrel (SMG)", "barrel", ["smg"], "barvechos", "Barvechos Central Camp", "Acampamento Central de Barvechos", 0.345, 0.505, "+Handling, +Mobility", "+Manuseio, +Mobilidade"),
    _att("att_afg", "Angled Foregrip (AFG)", "underbarrel", ["ar", "smg", "sniper"], "barvechos", "Barvechos West Pass", "Passagem Oeste de Barvechos", 0.312, 0.495, "+Handling, +ADS speed", "+Manuseio e velocidade de mira"),
    _att("att_shift_grip", "Shift Short Angled Grip", "underbarrel", ["ar", "smg"], "barvechos", "Barvechos Outpost Delta", "Posto Delta de Barvechos", 0.352, 0.518, "+Handling, +Mobility", "+Manuseio, +Mobilidade"),
    # Mojocoyo
    _att("att_ar_stanag30", "5.56 STANAG 30 Mag", "magazine", ["ar"], "mojocoyo", "Mojocoyo North Outpost", "Posto Norte de Mojocoyo", 0.168, 0.508, "Standard 30-round STANAG magazine", "Carregador STANAG 30 munições"),
    _att("att_lmg_3dot", "Laser 3Dot (LMG)", "rail", ["lmg"], "mojocoyo", "Mojocoyo East Village", "Vila Leste de Mojocoyo", 0.188, 0.532, "+Hip-fire control", "+Controle de tiro no quadril"),
    _att("att_sr_atpial", "ATPIAL Laser Sight (Sniper)", "rail", ["sniper"], "mojocoyo", "Mojocoyo West Camp", "Acampamento Oeste de Mojocoyo", 0.148, 0.525, "+Handling, +Accuracy", "+Manuseio, +Precisão"),
    _att("att_smg_ext30", "Extended Mag 30 (SMG)", "magazine", ["smg"], "mojocoyo", "Mojocoyo South Depot", "Depósito Sul de Mojocoyo", 0.172, 0.555, "+Magazine capacity", "+Capacidade do carregador"),
    # San Mateo
    _att("att_sr_long_barrel", "Long Barrel (Sniper)", "barrel", ["sniper"], "san_mateo", "San Mateo North Checkpoint", "Bloqueio Norte de San Mateo", 0.330, 0.325, "+Damage, +Range, +Bullet Velocity", "+Dano, +Alcance, +Velocidade de projétil"),
    _att("att_ar_3dot", "Laser 3Dot (AR)", "rail", ["ar"], "san_mateo", "San Mateo East Base", "Base Leste de San Mateo", 0.352, 0.352, "+Accuracy, +Handling", "+Precisão, +Manuseio"),
    _att("att_pks07", "PKS-07 Sniper Scope", "scope", ["sniper"], "san_mateo", "San Mateo Canyon Ridge", "Crista do Cânion de San Mateo", 0.312, 0.348, "Long-range tactical sniper optic", "Mira telescópica de longo alcance"),
    _att("att_ar_folded", "Folded Buttstock (AR)", "stock", ["ar"], "san_mateo", "San Mateo South Camp", "Acampamento Sul de San Mateo", 0.338, 0.372, "+Handling, +Mobility", "+Manuseio, +Mobilidade"),
    # Monte Puncu
    _att("att_ar_comp_v2", "Compensator V2 (AR)", "muzzle", ["ar"], "monte_puncu", "Monte Puncu North Bunker", "Bunker Norte de Monte Puncu", 0.715, 0.258, "+Recoil & Penetration, loud (~93m)", "+Recuo e Penetração, alto (~93m)"),
    _att("att_digital_scope", "Digital Scope", "scope", ["ar", "smg", "lmg"], "monte_puncu", "Monte Puncu Central Town", "Cidade de Monte Puncu", 0.725, 0.282, "2.0x/4.0x variable zoom optic", "Mira com zoom variável 2x/4x"),
    _att("att_exps_g33", "EXPS & G33 Flip Magnifier", "scope", ["ar", "smg", "lmg"], "monte_puncu", "Monte Puncu East Outpost", "Posto Leste de Monte Puncu", 0.742, 0.288, "1x Holo + 3.5x flip magnifier", "Mira holográfica 1x + ampliador 3.5x"),
    _att("att_fg_v4", "Foregrip V4", "underbarrel", ["ar", "lmg"], "monte_puncu", "Monte Puncu South Ridge", "Crista Sul de Monte Puncu", 0.718, 0.305, "+Accuracy, +Recoil control", "+Precisão, +Controle de recuo"),
    _att("att_lmg_comp", "Compensator (LMG)", "muzzle", ["lmg"], "monte_puncu", "Monte Puncu West Lab", "Laboratório Oeste de Monte Puncu", 0.698, 0.278, "+Stability, loud (~109m)", "+Estabilidade, alto (~109m)"),
    # Espiritu Santo
    _att("att_ta31h", "TA31H ACOG Scope", "scope", ["ar", "lmg", "sniper"], "espiritu_santo", "Espíritu Santo North Outpost", "Posto Norte de Espíritu Santo", 0.798, 0.132, "4x tactical ACOG optic", "Mira tática ACOG 4x"),
    _att("att_sr_rangefinder", "Range Finder (Sniper)", "rail", ["sniper"], "espiritu_santo", "Espíritu Santo East Shrine", "Santuário Leste de Espíritu Santo", 0.818, 0.165, "+Range, +Bullet drop compensation", "+Alcance e compensação balística"),
    _att("att_lmg_folded", "Folded Buttstock (LMG)", "stock", ["lmg"], "espiritu_santo", "Espíritu Santo South Camp", "Acampamento Sul de Espíritu Santo", 0.792, 0.168, "+Handling, +ADS speed", "+Manuseio e velocidade de mira"),
    # Caimanes
    _att("att_ar_short_barrel", "Short Barrel (AR)", "barrel", ["ar"], "caimanes", "Caimanes North Swamp", "Pântano Norte de Caimanes", 0.848, 0.448, "+Handling, +Mobility", "+Manuseio, +Mobilidade"),
    _att("att_ar_mag50", "Large 50-Round Mag (AR)", "magazine", ["ar"], "caimanes", "Caimanes Submarine Dock", "Doca de Submarinos de Caimanes", 0.875, 0.475, "+50 round capacity", "+Capacidade de 50 munições"),
    _att("att_exps3", "EXPS3 Holographic Sight", "scope", ["ar", "smg", "lmg", "shotgun"], "caimanes", "Caimanes Central Outpost", "Posto Central de Caimanes", 0.858, 0.482, "+Accuracy, clear CQB reticle", "+Precisão, retículo CQB limpo"),
    _att("att_sr_comp_stock2", "Compensated Buttstock (Sniper)", "stock", ["sniper"], "caimanes", "Caimanes South Island", "Ilha Sul de Caimanes", 0.865, 0.512, "+Stability, +Accuracy", "+Estabilidade, +Precisão"),
    # Flor de Oro
    _att("att_ar_rangefinder", "Range Finder (AR)", "rail", ["ar"], "flor_de_oro", "Flor de Oro North Watchtower", "Torre Norte de Flor de Oro", 0.772, 0.832, "+Range, +Accuracy", "+Alcance, +Precisão"),
    _att("att_lmg_suppressor", "LMG Suppressor", "muzzle", ["lmg"], "flor_de_oro", "M.O.B. Jaguar East Hangar", "Hangar Leste M.O.B. Jaguar", 0.798, 0.848, "Reduces LMG gunshot hearing to ~40m", "Reduz audibilidade de LMG para ~40m"),
    _att("att_sr_ext30", "Extended Mag 30 (Sniper/DMR)", "magazine", ["sniper"], "flor_de_oro", "Flor de Oro Border Camp", "Acampamento da Fronteira", 0.785, 0.868, "+DMR/Sniper capacity", "+Capacidade para DMR/Sniper"),
    _att("att_sr_3dot", "Laser 3Dot (Sniper)", "rail", ["sniper"], "flor_de_oro", "Flor de Oro West Jungle", "Selva Oeste de Flor de Oro", 0.758, 0.845, "+Handling, +Accuracy", "+Manuseio, +Precisão"),
    # Libertad
    _att("att_ar_762_30", "Extended Mag 30 (AK 7.62)", "magazine", ["ar"], "libertad", "Libertad North Factory", "Fábrica Norte de Libertad", 0.818, 0.648, "+30rd 7.62x39 capacity", "+30 munições 7.62x39"),
    _att("att_ar_comp_stock", "Compensated Buttstock (AR)", "stock", ["ar"], "libertad", "Libertad East Compound", "Complexo Leste de Libertad", 0.835, 0.662, "+Accuracy, +Recoil control", "+Precisão, +Controle de recuo"),
    _att("att_sg_ext_tube", "Large Magazine / Tube (Shotgun)", "magazine", ["shotgun"], "libertad", "Libertad South Outpost", "Posto Sul de Libertad", 0.812, 0.682, "+Shell capacity", "+Capacidade de cartuchos"),
    # Malca
    _att("att_lmg_atpial", "ATPIAL Laser Sight (LMG)", "rail", ["lmg"], "malca", "Malca North Quarry", "Pedreira Norte de Malca", 0.335, 0.742, "+Handling, +Accuracy", "+Manuseio, +Precisão"),
    _att("att_sg_comp", "Compensator (Shotgun)", "muzzle", ["shotgun"], "malca", "Malca Cathedral Outpost", "Posto da Catedral de Malca", 0.348, 0.765, "+Tighter spread, loud (~109m)", "+Menor dispersão, alto (~109m)"),
    _att("att_sr_comp", "Compensator (Sniper)", "muzzle", ["sniper"], "malca", "Malca South Canyon", "Cânion Sul de Malca", 0.322, 0.778, "+Stability, loud (~130m)", "+Estabilidade, alto (~130m)"),
    # Pucara
    _att("att_ar_atpial", "ATPIAL Laser Sight (AR)", "rail", ["ar"], "pucara", "Pucara North Outpost", "Posto Norte de Pucara", 0.562, 0.822, "+Handling, +Hip-fire", "+Manuseio, +Tiro no quadril"),
    _att("att_tars101", "TARS101 Sniper Scope", "scope", ["sniper"], "pucara", "Pucara Western Ruins", "Ruínas Oeste de Pucara", 0.548, 0.842, "4.5x/5.5x variable long-range sniper optic", "Mira telescópica variável 4.5x/5.5x"),
    _att("att_fg_v2", "Foregrip V2", "underbarrel", ["ar", "lmg", "smg"], "pucara", "Pucara East Village", "Vila Leste de Pucara", 0.582, 0.838, "+Accuracy, +Stability", "+Precisão, +Estabilidade"),
    # Remanzo
    _att("att_m203", "M203 Grenade Launcher", "underbarrel", ["ar"], "remanzo", "Remanzo Central Farm", "Fazenda Central de Remanzo", 0.442, 0.758, "40mm underbarrel grenade launcher", "Lança-granadas 40mm acoplado"),
    _att("att_sr_comp_v2", "Compensator V2 (Sniper)", "muzzle", ["sniper"], "remanzo", "Remanzo East Outpost", "Posto Leste de Remanzo", 0.462, 0.768, "+Damage & Penetration, loud (~130m)", "+Dano e Penetração, alto (~130m)"),
    _att("att_sr_ext10", "Extended Mag 10 (.338 Sniper)", "magazine", ["sniper"], "remanzo", "Remanzo West Ranch", "Rancho Oeste de Remanzo", 0.425, 0.748, "+10rd sniper capacity", "+10 munições para rifle sniper"),
    # Koani
    _att("att_t5xi", "T5Xi Tactical Scope (6x)", "scope", ["sniper"], "koani", "Koani Train Depot North", "Norte do Pátio de Trens de Koani", 0.138, 0.105, "Highest-zoom 6x sniper optic in base game", "Mira sniper 6x de maior alcance do jogo base"),
    _att("att_posp", "POSP Scope", "scope", ["sniper", "ar"], "koani", "Koani Salt Flats Outpost", "Posto do Salar de Koani", 0.155, 0.135, "4x Eastern Bloc optic", "Mira tática russa 4x"),
    _att("att_micro_g33", "Micro T-1 & G33 Magnifier", "scope", ["ar", "smg", "lmg"], "koani", "Koani Airbase East", "Base Aérea Leste de Koani", 0.165, 0.118, "Compact reflex + 3x flip magnifier", "Reflex compacta + ampliador 3x"),
    _att("att_hg_ext15", "Extended Mag 15 (Handgun)", "magazine", ["pistol"], "koani", "Koani Southwest Checkpoint", "Bloqueio Sudoeste de Koani", 0.125, 0.155, "+Pistol capacity", "+Capacidade de pistola"),
    # Media Luna
    _att("att_sr_suppressor", "Sniper Suppressor", "muzzle", ["sniper"], "media_luna", "Media Luna Western Outpost", "Posto Oeste de Media Luna", 0.288, 0.135, "Reduces sniper gunshot hearing to ~48m", "Reduz audibilidade de sniper para ~48m"),
    _att("att_ar_suppressor", "AR Suppressor", "muzzle", ["ar"], "media_luna", "Media Luna Central Base", "Base Central de Media Luna", 0.312, 0.132, "Reduces AR gunshot hearing to ~34m", "Reduz audibilidade de fuzil para ~34m"),
    _att("att_smg_rangefinder", "Range Finder (SMG)", "rail", ["smg"], "media_luna", "Media Luna Eastern Canyon", "Cânion Leste de Media Luna", 0.338, 0.145, "+Range, +Accuracy", "+Alcance, +Precisão"),
    # Inca Camina
    _att("att_g28_scope", "G28 Scope (5x + Red Dot)", "scope", ["sniper", "ar"], "inca_camina", "Inca Camina Airfield", "Aeródromo de Inca Camina", 0.175, 0.858, "Dual-role 5x sniper + top red dot", "Mira dupla 5x sniper + red dot superior"),
    _att("att_lmg_ext200", "200-Round Ammo Box (LMG)", "magazine", ["lmg"], "inca_camina", "Inca Camina Peak Outpost", "Posto do Pico de Inca Camina", 0.195, 0.872, "+200rd LMG box", "+Caixa de 200 munições LMG"),
    # Montuyoc
    _att("att_hg_3dot", "Laser 3Dot (Handgun)", "rail", ["pistol"], "montuyoc", "Montuyoc South Pass", "Passagem Sul de Montuyoc", 0.222, 0.688, "+Hip-fire pistol accuracy", "+Precisão de pistola sem mira"),
    _att("att_lmg_comp_v2", "Compensator V2 (LMG)", "muzzle", ["lmg"], "montuyoc", "Montuyoc East Checkpoint", "Bloqueio Leste de Montuyoc", 0.242, 0.672, "+Damage & Stability, loud (~109m)", "+Dano e Estabilidade, alto (~109m)"),
    # La Cruz & Villa Verde
    _att("att_std_gl", "STD Grenade Launcher", "underbarrel", ["ar"], "la_cruz", "La Cruz South Warehouse", "Armazém Sul de La Cruz", 0.618, 0.652, "High-explosive underbarrel launcher", "Lança-granadas acoplado"),
    _att("att_ar_flash_hider", "Flash Hider (AR)", "muzzle", ["ar"], "la_cruz", "La Cruz West Farm", "Fazenda Oeste de La Cruz", 0.602, 0.638, "Hides muzzle flash, loud (~93m)", "Oculta clarão do disparo, alto (~93m)"),
    _att("att_vv_grip", "Vertical Foregrip", "underbarrel", ["ar", "smg", "lmg"], "villa_verde", "Villa Verde South Camp", "Acampamento Sul de Villa Verde", 0.692, 0.488, "+Accuracy, +Handling", "+Precisão, +Manuseio"),
]

# Medalhas de Bônus (passivas permanentes!)
BONUS_MEDALS: list[dict[str, Any]] = [
    {"id": "med_stamina", "kind": "medal", "name_en": "Physical Training Medal (Stamina)", "name_pt": "Medalha de Treinamento Físico (Estamina)", "province": "itacua", "location_en": "Itacua North Ruins", "location_pt": "Ruínas Norte de Itacua", "u": 0.508, "v": 0.602, "bonus_en": "+25% Stamina capacity", "bonus_pt": "+25% de capacidade de Estamina"},
    {"id": "med_drone_range", "kind": "medal", "name_en": "Tech Specialist Medal (Drone Range)", "name_pt": "Medalha Especialista Tech (Alcance do Drone)", "province": "agua_verde", "location_en": "Agua Verde South Dock", "location_pt": "Doca Sul de Agua Verde", "u": 0.492, "v": 0.322, "bonus_en": "+25% Drone Signal Range", "bonus_pt": "+25% de Alcance do Drone"},
    {"id": "med_detection", "kind": "medal", "name_en": "Stealth Medal (Enemy Detection)", "name_pt": "Medalha de Furtividade (Detecção)", "province": "ocoro", "location_en": "Ocoro River Shrine", "location_pt": "Santuário do Rio Ocoro", "u": 0.542, "v": 0.482, "bonus_en": "Slows enemy visual detection speed", "bonus_pt": "Reduz velocidade de detecção visual inimiga"},
    {"id": "med_ammo", "kind": "medal", "name_en": "Munitions Medal (Ammo Capacity)", "name_pt": "Medalha de Munição (Capacidade)", "province": "montuyoc", "location_en": "Montuyoc Training Bunker", "location_pt": "Bunker de Treinamento de Montuyoc", "u": 0.205, "v": 0.678, "bonus_en": "+25% Max Reserve Ammo", "bonus_pt": "+25% de Munição Reserva Máxima"},
    {"id": "med_explosion", "kind": "medal", "name_en": "Ordnance Medal (Blast Radius)", "name_pt": "Medalha de Artilharia (Raio Explosivo)", "province": "koani", "location_en": "Koani Airfield Tower", "location_pt": "Torre do Aeródromo de Koani", "u": 0.142, "v": 0.118, "bonus_en": "+25% Explosive Blast Radius", "bonus_pt": "+25% de Raio de Explosão"},
    {"id": "med_quiet_run", "kind": "medal", "name_en": "Quiet Running Medal", "name_pt": "Medalha de Corrida Silenciosa", "province": "espiritu_santo", "location_en": "Espíritu Santo Ridge Camp", "location_pt": "Acampamento da Crista de Espíritu Santo", "u": 0.788, "v": 0.162, "bonus_en": "-25% Footstep Noise", "bonus_pt": "-25% de Ruído ao Correr"},
    {"id": "med_revive", "kind": "medal", "name_en": "Medic Medal (Revive Speed)", "name_pt": "Medalha Médica (Velocidade de Reanimação)", "province": "caimanes", "location_en": "Caimanes Field Hospital", "location_pt": "Hospital de Campanha de Caimanes", "u": 0.852, "v": 0.495, "bonus_en": "+25% Teammate Revive Speed", "bonus_pt": "+25% de Velocidade de Reanimação"},
    {"id": "med_vehicle_armor", "kind": "medal", "name_en": "Armored Convoy Medal", "name_pt": "Medalha de Blindagem Veicular", "province": "flor_de_oro", "location_en": "Flor de Oro Unidad Depot", "location_pt": "Depósito da Unidad de Flor de Oro", "u": 0.772, "v": 0.858, "bonus_en": "+25% Vehicle Armor", "bonus_pt": "+25% de Blindagem de Veículos"},
    {"id": "med_stable_aim", "kind": "medal", "name_en": "Sharpshooter Medal (Stable Aim)", "name_pt": "Medalha de Atirador de Elite", "province": "media_luna", "location_en": "Media Luna Canyon Outpost", "location_pt": "Posto do Cânion de Media Luna", "u": 0.318, "v": 0.118, "bonus_en": "-25% Weapon Sway", "bonus_pt": "-25% de Oscilação da Mira"},
    {"id": "med_thermal", "kind": "medal", "name_en": "Recon Medal (Binocular Zoom)", "name_pt": "Medalha de Reconhecimento (Binóculos)", "province": "tabacal", "location_en": "Tabacal Lookout", "location_pt": "Mirante de Tabacal", "u": 0.528, "v": 0.132, "bonus_en": "+25% Binocular & Drone Battery", "bonus_pt": "+25% de Bateria de Drone/Binóculos"},
]

# Categorias do Mapa Tático (14 categorias GRW)
MAP_CATEGORIES: list[dict[str, Any]] = [
    {"id": "weapon_case", "name_en": "Weapon Cases", "name_pt": "Caixas de Armas", "color": "#f59e0b", "icon": "weapon_case"},
    {"id": "attachment_case", "name_en": "Weapon Attachments", "name_pt": "Acessórios de Arma", "color": "#38bdf8", "icon": "attachment_case"},
    {"id": "bonus_medal", "name_en": "Bonus Medals", "name_pt": "Medalhas de Bônus", "color": "#eab308", "icon": "bonus_medal"},
    {"id": "sb_base", "name_en": "Santa Blanca Bases", "name_pt": "Bases Santa Blanca", "color": "#ef4444", "icon": "sb_base"},
    {"id": "unidad_base", "name_en": "Unidad Fortresses", "name_pt": "Fortalezas Unidad", "color": "#a855f7", "icon": "unidad_base"},
    {"id": "sam_site", "name_en": "SAM Launchers", "name_pt": "Baterias SAM", "color": "#fb7185", "icon": "sam_site"},
    {"id": "jammer", "name_en": "Drone Jammers", "name_pt": "Bloqueadores de Drone", "color": "#f43f5e", "icon": "jammer"},
    {"id": "rebel_op", "name_en": "Rebel Ops", "name_pt": "Operações Rebeldes", "color": "#22c55e", "icon": "rebel_op"},
    {"id": "rally_point", "name_en": "Rally Points (Fast Travel)", "name_pt": "Pontos de Encontro", "color": "#60a5fa", "icon": "rally_point"},
    {"id": "skill_point", "name_en": "Skill Points", "name_pt": "Pontos de Habilidade", "color": "#34d399", "icon": "skill_point"},
    {"id": "kingslayer", "name_en": "Kingslayer Files", "name_pt": "Arquivos Kingslayer", "color": "#cbd5e1", "icon": "kingslayer"},
    {"id": "boss_hq", "name_en": "Buchón / Cartel Bosses", "name_pt": "Chefes / Buchones", "color": "#dc2626", "icon": "boss_hq"},
]


def build_static_databases(lang: str = "pt-BR") -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Gera map_data, catalog e cartel já localizados para o idioma pedido."""
    is_pt = lang.lower().startswith("pt")
    prov_by_id = {p["id"]: p for p in PROVINCES}
    pois: list[dict[str, Any]] = []

    # 1. Caixas de Armas
    catalog_weapons: list[dict[str, Any]] = []
    for w in WEAPONS_DB:
        prov = prov_by_id.get(w["province"], {})
        loc = w["location_pt"] if is_pt else w["location_en"]
        desc = w["desc_pt"] if is_pt else w["desc_en"]
        w_entry = {
            **w,
            "location": loc,
            "province_name": prov.get("name", w["province"]),
            "desc": desc,
        }
        catalog_weapons.append(w_entry)
        if w["obtain_type"] == "weapon_case":
            pois.append({
                "id": f"poi_{w['id']}",
                "cat": "weapon_case",
                "name": w["name"],
                "province": w["province"],
                "province_name": prov.get("name", w["province"]),
                "u": w["u"],
                "v": w["v"],
                "item_id": w["id"],
                "desc": f"{loc} — {desc}",
            })

    # 2. Acessórios de Armas
    catalog_attachments: list[dict[str, Any]] = []
    for a in ATTACHMENTS_DB:
        prov = prov_by_id.get(a["province"], {})
        loc = a["location_pt"] if is_pt else a["location_en"]
        eff = a["effect_pt"] if is_pt else a["effect_en"]
        desc = a["desc_pt"] if is_pt else a["desc_en"]
        a_entry = {
            **a,
            "location": loc,
            "province_name": prov.get("name", a["province"]),
            "effect": eff,
            "desc": desc,
        }
        catalog_attachments.append(a_entry)
        pois.append({
            "id": f"poi_{a['id']}",
            "cat": "attachment_case",
            "name": a["name"],
            "province": a["province"],
            "province_name": prov.get("name", a["province"]),
            "u": a["u"],
            "v": a["v"],
            "item_id": a["id"],
            "desc": f"{loc} — {eff}",
        })

    # 3. Medalhas de Bônus
    catalog_medals: list[dict[str, Any]] = []
    for m in BONUS_MEDALS:
        prov = prov_by_id.get(m["province"], {})
        name = m["name_pt"] if is_pt else m["name_en"]
        loc = m["location_pt"] if is_pt else m["location_en"]
        bon = m["bonus_pt"] if is_pt else m["bonus_en"]
        m_entry = {
            **m,
            "name": name,
            "location": loc,
            "province_name": prov.get("name", m["province"]),
            "bonus": bon,
            "desc": f"{loc} — {bon}",
        }
        catalog_medals.append(m_entry)
        pois.append({
            "id": f"poi_{m['id']}",
            "cat": "bonus_medal",
            "name": name,
            "province": m["province"],
            "province_name": prov.get("name", m["province"]),
            "u": m["u"],
            "v": m["v"],
            "item_id": m["id"],
            "desc": f"{loc} — {bon}",
        })

    # 4. Bases, Pontos de Encontro, SAMs, Jammers, Rebel Ops & Bosses por província
    for idx, p in enumerate(PROVINCES):
        pid = p["id"]
        u, v = p["u"], p["v"]
        # Rally point / Safehouse principal da província
        pois.append({
            "id": f"rally_{pid}_alpha",
            "cat": "rally_point",
            "name": f"{p['name']} Alpha",
            "province": pid,
            "province_name": p["name"],
            "u": round(max(0.03, min(0.97, u - 0.018)), 4),
            "v": round(max(0.03, min(0.97, v - 0.012)), 4),
            "desc": ("Ponto de Encontro / Viagem Rápida" if is_pt else "Safehouse / Fast Travel Rally Point"),
        })
        # Sede do Buchón
        pois.append({
            "id": f"boss_{pid}",
            "cat": "boss_hq",
            "name": f"{p['boss']} ({p['name']})",
            "province": pid,
            "province_name": p["name"],
            "u": u,
            "v": v,
            "desc": (p["desc_pt"] if is_pt else p["desc_en"]),
        })
        # Rebel Op
        pois.append({
            "id": f"rebel_{pid}",
            "cat": "rebel_op",
            "name": f"{'Op. Rebelde' if is_pt else 'Rebel Op'} — {p['name']}",
            "province": pid,
            "province_name": p["name"],
            "u": round(max(0.03, min(0.97, u + 0.022)), 4),
            "v": round(max(0.03, min(0.97, v + 0.016)), 4),
            "desc": ("Suporte Rebelde (Morteiro / Avistamento / Veículo / Distração)" if is_pt else "Rebel Support Unlock (Mortar / Spotting / Vehicle / Diversion)"),
        })
        # Skill Point & Kingslayer File
        pois.append({
            "id": f"skill_{pid}",
            "cat": "skill_point",
            "name": f"{'Ponto de Habilidade' if is_pt else 'Skill Point'} ({p['name']})",
            "province": pid,
            "province_name": p["name"],
            "u": round(max(0.03, min(0.97, u - 0.012)), 4),
            "v": round(max(0.03, min(0.97, v + 0.020)), 4),
            "desc": ("+1/+3/+5 Pontos de Habilidade" if is_pt else "Skill Points Cache"),
        })
        pois.append({
            "id": f"ks_{pid}",
            "cat": "kingslayer",
            "name": f"{'Arquivo Kingslayer' if is_pt else 'Kingslayer File'} — {p['name']}",
            "province": pid,
            "province_name": p["name"],
            "u": round(max(0.03, min(0.97, u + 0.015)), 4),
            "v": round(max(0.03, min(0.97, v - 0.018)), 4),
            "desc": ("Dossiê de inteligência sobre o cartel e a região" if is_pt else "Cartel & regional intelligence dossier"),
        })
        # Unidad fortress & SAM/Jammer nas províncias mais fortificadas
        if p["skulls"] >= 3 or pid in ("itacua", "agua_verde", "barvechos"):
            pois.append({
                "id": f"uni_{pid}",
                "cat": "unidad_base",
                "name": f"{'Base Unidad' if is_pt else 'Unidad Base'} — {p['name']}",
                "province": pid,
                "province_name": p["name"],
                "u": round(max(0.03, min(0.97, u + 0.028)), 4),
                "v": round(max(0.03, min(0.97, v - 0.014)), 4),
                "desc": ("Fortaleza da Unidad com alarme, gerador e reforços blindados" if is_pt else "Unidad fortress with alarm panels, generator and heavy reinforcements"),
            })
        else:
            pois.append({
                "id": f"sb_{pid}",
                "cat": "sb_base",
                "name": f"{'Base Santa Blanca' if is_pt else 'Santa Blanca Base'} — {p['name']}",
                "province": pid,
                "province_name": p["name"],
                "u": round(max(0.03, min(0.97, u + 0.026)), 4),
                "v": round(max(0.03, min(0.97, v - 0.012)), 4),
                "desc": ("Posto fortificado do Cartel Santa Blanca" if is_pt else "Fortified Santa Blanca Cartel compound"),
            })
        if p["skulls"] >= 3:
            pois.append({
                "id": f"sam_{pid}",
                "cat": "sam_site",
                "name": f"SAM — {p['name']}",
                "province": pid,
                "province_name": p["name"],
                "u": round(max(0.03, min(0.97, u - 0.024)), 4),
                "v": round(max(0.03, min(0.97, v - 0.022)), 4),
                "desc": ("Lançador terra-ar antiaéreo" if is_pt else "Surface-to-air anti-aircraft missile battery"),
            })
        if p["skulls"] >= 2 and idx % 2 == 0:
            pois.append({
                "id": f"jam_{pid}",
                "cat": "jammer",
                "name": f"{'Bloqueador de Drone' if is_pt else 'Drone Jammer'} — {p['name']}",
                "province": pid,
                "province_name": p["name"],
                "u": round(max(0.03, min(0.97, u + 0.008)), 4),
                "v": round(max(0.03, min(0.97, v + 0.024)), 4),
                "desc": ("Interfere no sinal do drone em ~180m" if is_pt else "Disables drone signal within ~180m until disabled"),
            })

    cats_out = [
        {
            "id": c["id"],
            "name": c["name_pt"] if is_pt else c["name_en"],
            "color": c["color"],
            "icon": c["icon"],
        }
        for c in MAP_CATEGORIES
    ]
    provs_out = [
        {
            "id": p["id"],
            "name": p["name"],
            "wing": p["wing"],
            "boss": p["boss"],
            "skulls": p["skulls"],
            "u": p["u"],
            "v": p["v"],
            "biome": p["biome_pt"] if is_pt else p["biome_en"],
            "desc": p["desc_pt"] if is_pt else p["desc_en"],
        }
        for p in PROVINCES
    ]
    wings_out = [
        {
            "id": w["id"],
            "name": w["name_pt"] if is_pt else w["name_en"],
            "head": w["head"],
            "color": w["color"],
            "desc": w["desc_pt"] if is_pt else w["desc_en"],
        }
        for w in CARTEL_WINGS
    ]

    map_data = {
        "categories": cats_out,
        "provinces": provs_out,
        "pois": pois,
        "acoustics": WEAPON_ACOUSTICS,
    }
    catalog_data = {
        "weapons": catalog_weapons,
        "attachments": catalog_attachments,
        "medals": catalog_medals,
        "acoustics": WEAPON_ACOUSTICS,
    }
    cartel_data = {
        "leader": "El Sueño",
        "wings": wings_out,
        "provinces": provs_out,
    }
    return map_data, catalog_data, cartel_data
