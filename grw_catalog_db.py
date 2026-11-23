"""Banco de dados completo de Ghost Recon Wildlands: 21 províncias, Cartel, Missões, Armas, Acessórios compatíveis, Medalhas, Bases, SAMs e Rebel Ops."""
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

WEAPON_CLASSES: list[dict[str, str]] = [
    {"id": "ar", "label_en": "Assault Rifles", "label_pt": "Fuzis de Assalto"},
    {"id": "sniper", "label_en": "Sniper Rifles", "label_pt": "Rifles de Precisão"},
    {"id": "smg", "label_en": "Submachine Guns", "label_pt": "Submetralhadoras"},
    {"id": "lmg", "label_en": "Light Machine Guns", "label_pt": "Metralhadoras Leves"},
    {"id": "shotgun", "label_en": "Shotguns", "label_pt": "Escopetas"},
    {"id": "pistol", "label_en": "Handguns", "label_pt": "Pistolas"},
]

ATTACHMENT_SLOTS: list[dict[str, str]] = [
    {"id": "scope", "label_en": "Optics / Sights", "label_pt": "Miras / Ópticas"},
    {"id": "muzzle", "label_en": "Muzzle / Suppressors", "label_pt": "Boca / Silenciadores"},
    {"id": "barrel", "label_en": "Barrels", "label_pt": "Canos"},
    {"id": "magazine", "label_en": "Magazines", "label_pt": "Carregadores"},
    {"id": "underbarrel", "label_en": "Underbarrel / Grips", "label_pt": "Acoplamentos / Empunhaduras"},
    {"id": "rail", "label_en": "Rail / Lasers", "label_pt": "Trilho / Lasers"},
    {"id": "stock", "label_en": "Stocks", "label_pt": "Coronhas"},
]

DEFAULT_SLOTS_BY_CLASS: dict[str, list[str]] = {
    "ar": ["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail", "stock"],
    "sniper": ["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail", "stock"],
    "smg": ["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail", "stock"],
    "lmg": ["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail", "stock"],
    "shotgun": ["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail"],
    "pistol": ["muzzle", "magazine", "rail"],
}

BOSS_REWARD_PROVINCE_MAP: dict[str, str] = {
    "wp_ladykiller": "itacua",
    "wp_ritmo": "ocoro",
    "wp_llamativo": "agua_verde",
    "wp_elobsequio": "barvechos",
}

ANVIL_PROVINCE_SYNC: dict[str, dict[str, str | None]] = {
    "itacua": {"root": "Itacua-SEC_11", "prefix": "SEC_11", "boss_mission": "SEC_11_M040_HuntDownTorturers"},
    "ocoro": {"root": "Ocoro-PRO_12", "prefix": "PRO_12", "boss_mission": "PRO_12_M070_Neutralize_ElEmisario"},
    "agua_verde": {"root": "AguaVerde-INF_06", "prefix": "INF_06", "boss_mission": "INF_06_M060_Boss"},
    "barvechos": {"root": "Barvechos-SMU_21", "prefix": "SMU_21", "boss_mission": "SMU_21_M050_Boss"},
    "mojocoyo": {"root": "Mojocoyo-SMU_22", "prefix": "SMU_22", "boss_mission": "SMU_22_M020_Boss"},
    "san_mateo": {"root": "SanMateo-SEC_05", "prefix": "SEC_05", "boss_mission": "SEC_05_M050_BlackstonesRatio"},
    "tabacal": {"root": "Tabacal-PRO_02", "prefix": "PRO_02", "boss_mission": "PRO_02_M040_MadreCoca"},
    "espiritu_santo": {"root": "EspirituSanto-INF_04", "prefix": "INF_04", "boss_mission": "INF_04_M040_Extract_La_Santera"},
    "monte_puncu": {"root": None, "prefix": "MS09", "boss_mission": None},
    "villa_verde": {"root": "VillaVerde-PRO_09", "prefix": "PRO_09", "boss_mission": "PRO_09_M040_ExtractElWey"},
    "caimanes": {"root": "Caimanes-SMU_13", "prefix": "SMU_13", "boss_mission": "SMU_13_M040_UnderTheRadar"},
    "la_cruz": {"root": "LaCruz", "prefix": "MS08", "boss_mission": "MS08_ElBoquita"},
    "libertad": {"root": "Libertad-PRO_20", "prefix": "PRO_20", "boss_mission": "PRO_20_M020_Extract_Boss"},
    "flor_de_oro": {"root": "FlorDeOro-SEC_19", "prefix": "SEC_19", "boss_mission": "SEC_19_M060_GeneralBaroExtract"},
    "pucara": {"root": "Pucara-INF_15", "prefix": "INF_15", "boss_mission": "INF_15_M040_InterrogateDJPerico"},
    "remanzo": {"root": "Remanzo-SMU_23", "prefix": "SMU_23", "boss_mission": "SMU_23_M050_Kill_ElGato"},
    "malca": {"root": "Malca-INF_18", "prefix": "INF_18", "boss_mission": "INF_18_M030_LastSong"},
    "montuyoc": {"root": "Montuyoc-SEC_10", "prefix": "SEC_10", "boss_mission": "SEC_10_M030_CarlBookhart"},
    "inca_camina": {"root": "IncaCamina-ULC1-SMU_14", "prefix": "SMU_14", "boss_mission": "SMU_14_M010_KillPeruvianNegotiator"},
    "media_luna": {"root": "MediaLuna-ULC2-SEC_01", "prefix": "SEC_01", "boss_mission": "SEC_01_M040_BringingDownTheHouse"},
    "koani": {"root": "Koani-SMU_25", "prefix": "SMU_25", "boss_mission": "SMU_25_M040_BostonReed"},
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


def _m(
    mid: str,
    name_en: str,
    name_pt: str,
    du: float,
    dv: float,
    is_boss: bool = False,
) -> dict[str, Any]:
    return {
        "id": mid,
        "name_en": name_en,
        "name_pt": name_pt,
        "du": du,
        "dv": dv,
        "is_boss": is_boss,
    }


def _prov(
    pid: str,
    name: str,
    wing: str,
    boss: str,
    skulls: int,
    u: float,
    v: float,
    biome_en: str,
    biome_pt: str,
    desc_en: str,
    desc_pt: str,
    forge_completed_name: str,
    missions: list[dict[str, Any]],
) -> dict[str, Any]:
    built_missions: list[dict[str, Any]] = []
    for m in missions:
        built_missions.append({
            "id": f"mis_{pid}_{m['id']}",
            "name_en": m["name_en"],
            "name_pt": m["name_pt"],
            "is_boss": bool(m["is_boss"]),
            "u": round(max(0.02, min(0.98, u + m["du"])), 4),
            "v": round(max(0.02, min(0.98, v + m["dv"])), 4),
        })
    return {
        "id": pid,
        "name": name,
        "wing": wing,
        "boss": boss,
        "skulls": skulls,
        "u": u,
        "v": v,
        "biome_en": biome_en,
        "biome_pt": biome_pt,
        "desc_en": desc_en,
        "desc_pt": desc_pt,
        "forge_completed_name": forge_completed_name,
        "missions": built_missions,
    }


# As 21 províncias da Bolívia com coordenadas normalizadas (u, v) alinhadas ao gr.wmap e missões principais
PROVINCES: list[dict[str, Any]] = [
    _prov(
        "itacua", "Itacua", "security", "La Yuri & El Polito", 1, 0.52, 0.62,
        "Highland Valley", "Vale Serrano",
        "Starting province controlled by cartel torturers La Yuri & El Polito.",
        "Província inicial controlada pelos torturadores La Yuri e El Polito.",
        "WLEGRP_FS_R_CompletedProvince_Itacua",
        [
            _m("1", "Amaru's Rescue", "O Resgate de Amaru", -0.014, -0.010),
            _m("2", "The Lieutenant", "O Tenente", 0.008, -0.012),
            _m("3", "Amaru's Extraction", "A Extração de Amaru", 0.015, 0.006),
            _m("4", "Artisans' Quarter", "O Bairro dos Artesãos", -0.018, 0.014),
            _m("5", "La Yuri and El Polito", "La Yuri e El Polito", 0.004, -0.004, True),
        ],
    ),
    _prov(
        "ocoro", "Ocoro", "production", "El Emisario", 2, 0.53, 0.49,
        "Subtropical River Valley", "Vale Fluvial Subtropical",
        "Coca processing hub between Agua Verde and Itacua.",
        "Centro de processamento de coca entre Agua Verde e Itacua.",
        "WLEGRP_FS_R_CompletedProvince_Ocoro",
        [
            _m("1", "El Emisario's Messenger", "O Mensageiro de El Emisario", -0.010, 0.010),
            _m("2", "Subway Tunnels", "Túneis de Processamento", 0.012, -0.008),
            _m("3", "White Cocaine Lab", "Laboratório de Pasta Base", -0.015, -0.014),
            _m("4", "El Emisario's House", "A Casa de El Emisario", 0.002, 0.012, True),
        ],
    ),
    _prov(
        "agua_verde", "P.N. de Agua Verde", "influence", "Carzita", 2, 0.50, 0.30,
        "Lake & Resorts", "Lago e Resorts",
        "Luxury lake resorts used to entertain corrupt politicians and VIPs.",
        "Resorts luxuosos usados para corromper políticos e VIPs.",
        "WLEGRP_FS_R_CompletedProvince_PNAguaVerde",
        [
            _m("1", "Carzita's VIP List", "Lista VIP de Carzita", -0.014, 0.012),
            _m("2", "Island Casino Audit", "Cassino da Ilha", -0.005, -0.008),
            _m("3", "The Politician", "O Político", 0.016, 0.006),
            _m("4", "Carzita's Assistant", "O Assistente de Carzita", 0.010, -0.014),
            _m("5", "Carzita Resort Finale", "Complexo de Carzita", 0.002, 0.005, True),
        ],
    ),
    _prov(
        "barvechos", "Barvechos", "smuggling", "El Pulpo", 3, 0.34, 0.50,
        "Arid Plateau & Mines", "Planalto Árido e Minas",
        "Cartel accounting and mineral smuggling corridor.",
        "Contabilidade do cartel e corredor de contrabando mineral.",
        "WLEGRP_FS_R_CompletedProvince_Barvechos",
        [
            _m("1", "The Mule", "A Mula", -0.016, 0.008),
            _m("2", "Mineral Mine Smuggling", "Minas de Contrabando", 0.012, -0.016),
            _m("3", "Nidia's Cash", "Dinheiro de Nidia", 0.015, 0.012),
            _m("4", "Escort El Pulpo", "A Fuga de El Pulpo", 0.002, 0.002, True),
        ],
    ),
    _prov(
        "mojocoyo", "Mojocoyo", "smuggling", "Antonio", 3, 0.17, 0.53,
        "Crater Lake & Highlands", "Lago de Cratera e Planalto",
        "Stockpiles and air-drop staging grounds around a volcanic lake.",
        "Estoques de carga e zonas de entrega ao redor de um lago vulcânico.",
        "WLEGRP_FS_R_CompletedProvince_Mojocoyo",
        [
            _m("1", "Gabriel's Ledger", "Os Registros de Gabriel", -0.012, -0.010),
            _m("2", "The Cocaine Stash", "O Esconderijo de Cocaína", 0.014, -0.008),
            _m("3", "Crater Airstrip", "Pista do Lago", 0.008, 0.015),
            _m("4", "Antonio's Capture", "Captura de Antonio", -0.003, 0.004, True),
        ],
    ),
    _prov(
        "san_mateo", "San Mateo", "security", "El Pozolero", 3, 0.33, 0.35,
        "Dry Canyons", "Cânions Secos",
        "Disposal grounds and prison camps overseen by El Pozolero.",
        "Campos de eliminação e prisões comandados por El Pozolero.",
        "WLEGRP_FS_R_CompletedProvince_SanMateo",
        [
            _m("1", "The Journalist", "O Jornalista", -0.015, 0.014),
            _m("2", "Acid Vat Grounds", "Campos de Dissolução", 0.012, -0.012),
            _m("3", "Prison Raid", "Invasão à Prisão", -0.012, -0.014),
            _m("4", "El Pozolero", "El Pozolero", 0.005, 0.004, True),
        ],
    ),
    _prov(
        "tabacal", "Tabacal", "production", "Madre Coca", 2, 0.53, 0.14,
        "Lush Coca Valleys", "Vales de Coca",
        "Heartland of traditional coca farming guarded by Madre Coca.",
        "Coração do cultivo tradicional de coca protegido por Madre Coca.",
        "WLEGRP_FS_R_CompletedProvince_Tabacal",
        [
            _m("1", "Coca Plantation Sweep", "Plantações de Coca", -0.014, 0.010),
            _m("2", "Union Leaders", "Líderes Sindicais", 0.015, -0.010),
            _m("3", "Chemical Supply Depot", "Depósito Químico", -0.008, -0.015),
            _m("4", "Madre Coca's Lair", "Refúgio de Madre Coca", 0.004, 0.006, True),
        ],
    ),
    _prov(
        "espiritu_santo", "Espíritu Santo", "influence", "La Santera", 3, 0.80, 0.15,
        "Misty Cloud Forest", "Floresta Nebulosa",
        "Pilgrimage site and shrine headquarters of the Santa Muerte cult.",
        "Sítio de peregrinação e sede do culto à Santa Muerte.",
        "WLEGRP_FS_R_CompletedProvince_EspirituSanto",
        [
            _m("1", "The Gold Idol", "O Ídolo de Ouro", -0.016, -0.008),
            _m("2", "Cult Reliquaries", "Relicários do Culto", 0.014, 0.010),
            _m("3", "Holy Chapel Interrogation", "Capela Santa Muerte", 0.008, -0.016),
            _m("4", "La Santera's Shrine", "O Santuário de La Santera", 0.010, 0.004, True),
        ],
    ),
    _prov(
        "monte_puncu", "Monte Puncu", "influence", "DJ Perico", 3, 0.72, 0.28,
        "Mountain Jungle", "Selva Serrana",
        "Propaganda radio relay hills and jungle towns.",
        "Colinas das torres de rádio de propaganda e vilas na selva.",
        "WLEGRP_FS_R_CompletedProvince_MontePuncu",
        [
            _m("1", "The Rebel Informant", "O Informante Rebelde", -0.014, 0.012),
            _m("2", "Substation Broadcast", "Torres de Transmissão", 0.012, -0.012),
            _m("3", "DJ Perico's Studio", "Estúdio do DJ Perico", 0.002, 0.004, True),
        ],
    ),
    _prov(
        "villa_verde", "Villa Verde", "production", "El Wey", 2, 0.69, 0.48,
        "Tropical Jungle", "Selva Tropical",
        "Jungle chemical labs and river docks.",
        "Laboratórios químicos na selva e docas fluviais.",
        "WLEGRP_FS_R_CompletedProvince_VillaVerde",
        [
            _m("1", "Northern Laboratory", "Laboratório Norte", -0.010, -0.014),
            _m("2", "Chemist Extraction", "Extração do Químico", 0.014, 0.010),
            _m("3", "River Smuggling Docks", "Docas Fluviais", -0.014, 0.012),
            _m("4", "El Wey", "El Wey", 0.004, -0.004, True),
        ],
    ),
    _prov(
        "caimanes", "Caimanes", "smuggling", "El Cerebro", 4, 0.86, 0.48,
        "Swamp Delta", "Pântano e Delta",
        "Flooded swamp shipyards building narco-submarines.",
        "Estaleiros escondidos no pântano para construir narco-submarinos.",
        "WLEGRP_FS_R_CompletedProvince_Caimanes",
        [
            _m("1", "Submarine Fleet I", "Submarinos I", -0.014, -0.012),
            _m("2", "Submarine Fleet II", "Submarinos II", 0.012, 0.014),
            _m("3", "Submarine Fleet III", "Submarinos III", -0.012, 0.015),
            _m("4", "El Cerebro's Shipyard", "O Estaleiro de El Cerebro", 0.005, 0.002, True),
        ],
    ),
    _prov(
        "la_cruz", "La Cruz", "smuggling", "El Boquita", 2, 0.62, 0.64,
        "Forest & Towns", "Florestas e Vilas",
        "Transit crossroads connecting southern production to eastern rivers.",
        "Entroncamento logístico ligando o sul produtor aos rios do leste.",
        "WLEGRP_FS_R_CompletedProvince_LaCruz",
        [
            _m("1", "The Convoy Interception", "Interceptação de Comboio", -0.012, -0.010),
            _m("2", "Warehouse Raid", "Invasão ao Armazém", 0.014, -0.008),
            _m("3", "El Boquita", "El Boquita", 0.003, 0.005, True),
        ],
    ),
    _prov(
        "libertad", "Libertad", "production", "Marcus Jensen", 4, 0.82, 0.66,
        "Industrial City", "Cidade Industrial",
        "Industrial chemical plants producing pure cocaine at scale.",
        "Complexo químico industrial produzindo cocaína pura em escala.",
        "WLEGRP_FS_R_CompletedProvince_Libertad",
        [
            _m("1", "The Chemical Factory", "Fábrica Química", -0.014, -0.012),
            _m("2", "Hazardous Waste Trail", "Rastro Tóxico", 0.014, -0.008),
            _m("3", "Purification Silos", "Silos de Purificação", -0.010, 0.016),
            _m("4", "Marcus Jensen", "Marcus Jensen", 0.006, 0.004, True),
        ],
    ),
    _prov(
        "flor_de_oro", "Flor de Oro", "security", "General Baro", 5, 0.78, 0.85,
        "Fortified Jungle", "Selva Fortificada",
        "Heavily fortified Unidad border stronghold commanded by General Baro.",
        "Fortaleza fronteiriça da Unidad comandada pelo General Baro.",
        "WLEGRP_FS_R_CompletedProvince_FlorDeOro",
        [
            _m("1", "The Mole in Unidad", "O Espião na Unidad", -0.016, -0.010),
            _m("2", "The Black Site", "Base Secreta da Unidad", 0.012, -0.014),
            _m("3", "M.O.B. Jaguar Assault", "Invasão à M.O.B. Jaguar", 0.018, 0.012),
            _m("4", "General Baro", "General Baro", -0.004, 0.008, True),
        ],
    ),
    _prov(
        "pucara", "Pucara", "influence", "El Yayo (Operações)", 3, 0.57, 0.84,
        "Ancient Ruins & Canyons", "Ruínas e Cânions",
        "Southern ruins and cartel-pressured Aymara villages.",
        "Ruínas ancestrais e vilarejos aymaras sob pressão do cartel.",
        "WLEGRP_FS_R_CompletedProvince_Pucara",
        [
            _m("1", "El Sueno's Monument", "Monumento de El Sueño", -0.014, -0.012),
            _m("2", "Aymara Village Elders", "Anciões Aymaras", 0.014, 0.010),
            _m("3", "The Chido Connection", "El Yayo · Operação Sul", 0.003, 0.004, True),
        ],
    ),
    _prov(
        "remanzo", "Remanzo", "production", "El Gato", 3, 0.44, 0.76,
        "Livestock Farmlands", "Fazendas e Pastagens",
        "Slaughterhouses and livestock ranches hiding drug packaging.",
        "Matadouros e fazendas usados para embalar carregamentos.",
        "WLEGRP_FS_R_CompletedProvince_Remanzo",
        [
            _m("1", "The Slaughterhouse", "O Matadouro", -0.012, 0.010),
            _m("2", "Livestock Smuggling", "Fazenda de Embalagem", 0.014, -0.012),
            _m("3", "El Gato's Compound", "Complexo de El Gato", 0.003, 0.002, True),
        ],
    ),
    _prov(
        "malca", "Malca", "influence", "El Chido / El Cardenal", 3, 0.34, 0.76,
        "Red Rock Canyons", "Cânions Vermelhos",
        "Cathedral stronghold of El Cardenal and narcocorrido concerts.",
        "Catedral fortaleza de El Cardenal e palco de narcocorridos.",
        "WLEGRP_FS_R_CompletedProvince_Malca",
        [
            _m("1", "Narcocorrido Stage", "Palco de Narcocorrido", -0.014, -0.012),
            _m("2", "El Chido Capture", "Captura de El Chido", 0.012, -0.008),
            _m("3", "Cathedral of Santa Muerte", "Catedral de El Cardenal", 0.002, 0.004, True),
        ],
    ),
    _prov(
        "montuyoc", "Montuyoc", "security", "Carl Bookhart", 4, 0.22, 0.68,
        "Alpine Military Range", "Cordilheira Militar",
        "High-altitude sicario training bases run by Carl Bookhart.",
        "Bases de treinamento de altitude comandadas por Carl Bookhart.",
        "WLEGRP_FS_R_CompletedProvince_Montuyoc",
        [
            _m("1", "Chavina Training Center", "Centro de Treinamento Chavina", -0.006, -0.015),
            _m("2", "The Deserter", "O Desertor", 0.015, 0.008),
            _m("3", "Mortar Squadrons", "Baterias de Morteiro", -0.015, 0.010),
            _m("4", "Carl Bookhart", "Carl Bookhart", 0.002, 0.003, True),
        ],
    ),
    _prov(
        "inca_camina", "Inca Camina", "smuggling", "La Cabra", 5, 0.18, 0.86,
        "Snowy Peaks & Craters", "Picos Nevados e Crateras",
        "Peruvian smuggling pass across freezing Andean mountain peaks.",
        "Rota de contrabando peruana pelos picos nevados dos Andes.",
        "WLEGRP_FS_R_CompletedProvince_IncaCamina",
        [
            _m("1", "Mountain Supply Convoy", "Comboio nos Andes", -0.014, -0.012),
            _m("2", "Southern Cocaine Silos", "Silos da Montanha", 0.015, 0.012),
            _m("3", "The Peruvian Connection", "La Cabra (Conexão Peruana)", 0.004, 0.002, True),
        ],
    ),
    _prov(
        "media_luna", "Media Luna", "security", "El Comandante / El Muro", 5, 0.31, 0.13,
        "Canyon Fortress", "Cânion Fortaleza",
        "Deadly canyon airspace packed with SAM batteries and M.O.B. Condor.",
        "Desfiladeiro mortal repleto de baterias SAM e a base M.O.B. Condor.",
        "WLEGRP_FS_R_CompletedProvince_MediaLuna",
        [
            _m("1", "Conspiracy of El Comandante", "Dossiê El Comandante", -0.014, 0.012),
            _m("2", "M.O.B. Condor Intel", "Intel em M.O.B. Condor", 0.014, -0.010),
            _m("3", "El Muro Confrontation", "El Comandante / El Muro", 0.002, 0.004, True),
        ],
    ),
    _prov(
        "koani", "Koani", "smuggling", "Boston Reed", 5, 0.14, 0.13,
        "Salt Flats", "Salar de Uyuni",
        "Expansive white salt flats, train depot, and smuggling airbase.",
        "Planície branca de sal, pátio ferroviário e base aérea de contrabando.",
        "WLEGRP_FS_R_CompletedProvince_Koani",
        [
            _m("1", "The Convoy at Salt Flats", "Comboio no Salar", -0.012, 0.012),
            _m("2", "Train Graveyard", "Cemitério de Trens", -0.008, 0.016),
            _m("3", "Nidia Flores Capture", "Nidia Flores (Aeródromo)", 0.014, -0.014),
            _m("4", "Boston Reed", "Boston Reed", 0.003, 0.002, True),
        ],
    ),
]


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
    platform: str | None = None,
    customizable: bool | None = None,
    supported_slots: list[str] | None = None,
    suppressible: bool = True,
    forge_patterns: list[str] | None = None,
) -> dict[str, Any]:
    ac = WEAPON_ACOUSTICS[wclass]
    is_custom = (obtain != "boss_reward") if customizable is None else bool(customizable)
    slots = list(supported_slots) if supported_slots is not None else (
        list(DEFAULT_SLOTS_BY_CLASS[wclass]) if is_custom else []
    )
    if not suppressible and "muzzle" in slots:
        slots.remove("muzzle")
    return {
        "id": wid,
        "kind": "weapon",
        "name": name,
        "weapon_class": wclass,
        "platform": platform or wclass,
        "customizable": is_custom,
        "supported_slots": slots,
        "forge_patterns": list(forge_patterns or []),
        "province": prov,
        "location_en": loc_en,
        "location_pt": loc_pt,
        "u": round(u, 4),
        "v": round(v, 4),
        "obtain_type": obtain,
        "noise_suppressed_m": ac["suppressed_m"],
        "noise_unsuppressed_m": ac["unsuppressed_m"],
        "suppressible": suppressible,
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
    _w("wp_p416", "P416", "ar", "itacua", "Starter Loadout / Itacua Armory", "Equipamento Inicial / Arsenal de Itacua", 0.515, 0.625, "starter", 48, 62, 70, 52, 74, 48, 55, True, "Balanced starting 5.56mm assault rifle.", "Fuzil de assalto 5.56mm inicial equilibrado.", platform="nato_556", forge_patterns=["W_ASR_P416"]),
    _w("wp_m4a1", "M4A1", "ar", "flor_de_oro", "Armadillo / Southern Unidad Outpost", "Posto Avançado da Unidad Sul (Flor de Oro)", 0.765, 0.855, "weapon_case", 54, 65, 68, 56, 82, 50, 58, platform="nato_556", forge_patterns=["W_CAR_M4A1"]),
    _w("wp_acr", "ACR", "ar", "media_luna", "Culta Outpost (Media Luna)", "Posto Avançado Culta (Media Luna)", 0.305, 0.145, "weapon_case", 56, 74, 66, 62, 68, 54, 58, platform="nato_556", forge_patterns=["W_ASR_ACR"]),
    _w("wp_mk17", "MK17 (SCAR-H)", "ar", "flor_de_oro", "M.O.B. Jaguar / Southern Bunker", "Bunker Sul / Base Unidad (Flor de Oro)", 0.802, 0.872, "weapon_case", 72, 70, 52, 68, 56, 72, 50, platform="scar_762", forge_patterns=["W_ASR_MK17"]),
    _w("wp_tar21", "TAR-21", "ar", "montuyoc", "Chavina Training Center Armory", "Arsenal do Centro de Treinamento Chavina", 0.215, 0.662, "weapon_case", 55, 68, 72, 58, 78, 52, 58, platform="bullpup_556", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail"], forge_patterns=["W_ASR_TAR-21"]),
    _w("wp_auga3", "AUG A3", "ar", "barvechos", "Barvechos Mine Compound", "Complexo da Mina de Barvechos", 0.342, 0.482, "weapon_case", 56, 72, 66, 60, 66, 52, 58, platform="bullpup_556", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail"], forge_patterns=["W_ASR_AUG"]),
    _w("wp_556xi", "556xi", "ar", "caimanes", "Caimanes Swamp Outpost", "Posto no Pântano de Caimanes", 0.855, 0.462, "weapon_case", 58, 64, 65, 60, 68, 55, 56, platform="nato_556", forge_patterns=["W_ASR_SIG556"]),
    _w("wp_ak47", "AK-47", "ar", "libertad", "Libertad City Cartel Barracks", "Quartel do Cartel em Libertad", 0.830, 0.672, "weapon_case", 66, 54, 58, 54, 60, 66, 48, platform="ak_762", forge_patterns=["W_ASR_AK47"]),
    _w("wp_ak12", "AK-12", "ar", "tabacal", "Tabacal Coca Processing Plant", "Usina de Processamento de Tabacal", 0.542, 0.128, "weapon_case", 60, 68, 62, 60, 64, 58, 54, platform="ak_762", forge_patterns=["W_ASR_AK-12"]),
    _w("wp_r5rgp", "R5 RGP", "ar", "remanzo", "Remanzo Cartel Depot", "Depósito do Cartel em Remanzo", 0.448, 0.742, "weapon_case", 57, 70, 64, 58, 62, 54, 56, platform="nato_556", forge_patterns=["W_SNP_R5"]),
    _w("wp_g2", "FAMAS G2", "ar", "inca_camina", "Inca Camina Southern Outpost", "Posto Avançado Sul de Inca Camina", 0.168, 0.875, "weapon_case", 52, 64, 74, 54, 86, 50, 56, platform="bullpup_556", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail"], forge_patterns=["W_ASR_FAMAS"]),
    _w("wp_805bren", "805 Bren A2", "ar", "villa_verde", "Villa Verde North Lab", "Laboratório Norte de Villa Verde", 0.682, 0.465, "weapon_case", 58, 70, 64, 60, 66, 55, 56, platform="nato_556", forge_patterns=["W_ASR_CZ805"]),
    _w("wp_l85a2", "L85A2", "ar", "espiritu_santo", "Espíritu Santo Shrine Compound", "Complexo do Santuário de Espíritu Santo", 0.812, 0.155, "weapon_case", 54, 73, 66, 62, 64, 54, 58, platform="bullpup_556", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail"], forge_patterns=["W_ASR_L85A2"]),
    _w("wp_sr3m", "SR3M", "ar", "agua_verde", "Arroyo Baya Northern Outpost", "Posto Norte de Arroyo Baya (Agua Verde)", 0.548, 0.295, "weapon_case", 62, 62, 70, 50, 74, 62, 64, platform="asval_9x39", supported_slots=["scope", "muzzle", "barrel", "magazine", "rail", "stock"], forge_patterns=["W_ASR_SR3M"]),
    _w("wp_ritmo", "Ritmo (Boss)", "ar", "ocoro", "Defeat El Emisario in Ocoro", "Derrote El Emisario em Ocoro", 0.530, 0.502, "boss_reward", 58, 66, 68, 56, 70, 56, 54, platform="ak_762", customizable=False, forge_patterns=["W_ASR_AK-12_Ritmo"]),

    # --- Sniper Rifles ---
    _w("wp_m40a5", "M40A5", "sniper", "itacua", "Itacua Echo Safe House Bunker", "Bunker Próximo a Itacua Echo", 0.502, 0.605, "weapon_case", 78, 82, 50, 82, 22, 74, 42, platform="bolt_338", supported_slots=["scope", "muzzle", "barrel", "magazine", "rail", "stock"], forge_patterns=["W_SNP_M40A5"]),
    _w("wp_hti", "HTI", "sniper", "montuyoc", "Chavina Training Center South", "Sul do Centro de Treinamento Chavina", 0.238, 0.692, "weapon_case", 98, 76, 30, 96, 16, 98, 28, True, "Anti-materiel .50 cal rifle capable of 1-shotting helicopters.", "Rifle antimaterial .50 capaz de destruir helicópteros com 1 tiro.", platform="bolt_50", supported_slots=["scope", "muzzle", "barrel", "magazine", "rail"], forge_patterns=["W_SNP_HTI"]),
    _w("wp_msr", "MSR", "sniper", "montuyoc", "Choza Padre Mine Outpost", "Posto da Mina Choza Padre (Montuyoc)", 0.195, 0.658, "weapon_case", 90, 86, 42, 94, 24, 88, 36, platform="bolt_338", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail", "stock"], forge_patterns=["W_SNP_MSR"]),
    _w("wp_l115a3", "L115A3", "sniper", "monte_puncu", "Monte Puncu Radio Outpost", "Posto de Rádio de Monte Puncu", 0.728, 0.292, "weapon_case", 88, 84, 46, 92, 22, 85, 38, platform="bolt_338", supported_slots=["scope", "muzzle", "barrel", "magazine", "rail", "stock"], forge_patterns=["W_SNP_L115"]),
    _w("wp_mk14", "Mk14", "sniper", "koani", "Koani Train Cemetery Outpost", "Posto do Cemitério de Trens de Koani", 0.132, 0.145, "weapon_case", 72, 78, 56, 80, 54, 70, 48, platform="dmr_762", forge_patterns=["W_SNP_MK14"]),
    _w("wp_g28", "G28", "sniper", "san_mateo", "San Mateo Cartel Camp", "Acampamento do Cartel em San Mateo", 0.342, 0.342, "weapon_case", 70, 80, 58, 78, 56, 68, 50, platform="dmr_762", forge_patterns=["W_SNP_G28"]),
    _w("wp_sr25", "SR25", "sniper", "caimanes", "Caimanes Base Building 2F", "Base de Caimanes (2º Andar)", 0.872, 0.495, "weapon_case", 74, 78, 54, 82, 52, 72, 48, platform="dmr_762", forge_patterns=["W_SNP_SR25"]),
    _w("wp_svd", "Dragunov SVD", "sniper", "agua_verde", "Agua Verde Eastern Dock", "Docas Leste de Agua Verde", 0.535, 0.315, "weapon_case", 76, 74, 52, 80, 50, 74, 46, platform="dmr_svd", supported_slots=["scope", "muzzle", "barrel", "magazine", "rail"], forge_patterns=["W_SNP_DRAGUNOV"]),
    _w("wp_srsa1", "SRSA1", "sniper", "mojocoyo", "Mojocoyo Lakeside Outpost", "Posto à Beira do Lago de Mojocoyo", 0.185, 0.515, "weapon_case", 82, 84, 60, 82, 24, 76, 45, platform="bolt_338", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail"], forge_patterns=["W_SNP_SRS-A1"]),
    _w("wp_m1891", "M1891", "sniper", "libertad", "Libertad Southern Mansion", "Mansão Sul de Libertad", 0.808, 0.692, "weapon_case", 84, 72, 52, 80, 26, 78, 40, platform="bolt_338", supported_slots=["scope", "muzzle", "barrel"], forge_patterns=["W_SNP_M1891"]),
    _w("wp_sr1", "SR-1", "sniper", "koani", "Koani Salt Flats Research Base", "Base de Pesquisa do Salar de Koani", 0.155, 0.112, "weapon_case", 85, 84, 48, 88, 22, 82, 42, platform="bolt_338", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail", "stock"], forge_patterns=["W_SNP_DSR-1"]),

    # --- Submachine Guns (SMGs) ---
    _w("wp_mp5", "MP5", "smg", "itacua", "Itacua Western Outpost", "Posto Oeste de Itacua", 0.488, 0.618, "weapon_case", 42, 68, 82, 40, 76, 38, 74, platform="smg_9mm", forge_patterns=["W_SMG_MP5"]),
    _w("wp_mp7", "MP7", "smg", "barvechos", "Barvechos Town Safe House", "Casa Segura da Cidade de Barvechos", 0.322, 0.512, "weapon_case", 44, 66, 84, 42, 84, 48, 74, platform="smg_pdw", forge_patterns=["W_SMG_MP7"]),
    _w("wp_vector", "Vector .45 ACP", "smg", "media_luna", "M.O.B. Condor Hangar (Media Luna)", "Hangar de M.O.B. Condor (Media Luna)", 0.325, 0.122, "weapon_case", 46, 68, 80, 38, 95, 40, 76, platform="smg_45", forge_patterns=["W_SMG_VECTOR"]),
    _w("wp_p90", "P90", "smg", "la_cruz", "La Cruz Town Outpost", "Posto da Cidade de La Cruz", 0.625, 0.635, "weapon_case", 43, 66, 82, 44, 86, 50, 72, platform="smg_pdw", supported_slots=["scope", "muzzle", "barrel", "rail"], forge_patterns=["W_SMG_P90"]),
    _w("wp_scorpion", "Scorpion EVO 3", "smg", "mojocoyo", "Mojocoyo Cartel Depot", "Depósito do Cartel em Mojocoyo", 0.158, 0.542, "weapon_case", 44, 70, 82, 42, 88, 42, 74, platform="smg_9mm", forge_patterns=["W_SMG_SCORPION-EVO3"]),
    _w("wp_pp19", "PP19", "smg", "agua_verde", "Agua Verde Island Casino", "Cassino da Ilha em Agua Verde", 0.495, 0.292, "weapon_case", 45, 66, 78, 42, 72, 40, 72, platform="smg_9mm", supported_slots=["scope", "muzzle", "barrel", "rail", "stock"], forge_patterns=["W_SMG_PP19"]),
    _w("wp_sr635", "SR-635", "smg", "ocoro", "Ocoro Northern Checkpoint", "Bloqueio Norte de Ocoro", 0.525, 0.472, "weapon_case", 46, 68, 80, 44, 76, 42, 72, platform="smg_9mm", forge_patterns=["W_SMG_SR635"]),
    _w("wp_psg", "PSG", "smg", "san_mateo", "La Carcel Del Pueblo (San Mateo)", "La Cárcel del Pueblo (San Mateo)", 0.318, 0.365, "weapon_case", 43, 72, 82, 42, 74, 40, 74, platform="smg_9mm", forge_patterns=["W_SMG_PSG"]),
    _w("wp_9x19vsn", "9x19VSN", "smg", "inca_camina", "Inca Camina Northern Camp", "Acampamento Norte de Inca Camina", 0.178, 0.835, "weapon_case", 44, 68, 80, 42, 76, 40, 74, platform="smg_9mm", forge_patterns=["W_SMG_VITYAZ"]),
    _w("wp_9mmc1", "9mm C1", "smg", "remanzo", "Remanzo Slaughterhouse", "Matadouro de Remanzo", 0.428, 0.768, "weapon_case", 45, 64, 78, 42, 68, 40, 72, platform="smg_9mm", supported_slots=["scope", "muzzle", "magazine", "stock"], forge_patterns=["W_SMG_SterlingC1"]),
    _w("wp_mpx", "MPX", "smg", "monte_puncu", "Monte Puncu Sawmill", "Serraria de Monte Puncu", 0.712, 0.268, "weapon_case", 44, 72, 84, 44, 78, 42, 74, platform="smg_9mm", forge_patterns=["W_SMG_MPX"]),
    _w("wp_smg11", "SMG-11", "smg", "pucara", "Pucara Ruins Compound", "Complexo das Ruínas de Pucara", 0.562, 0.835, "weapon_case", 40, 56, 90, 34, 96, 36, 76, platform="smg_9mm", supported_slots=["scope", "muzzle", "magazine", "rail"], forge_patterns=["W_SMG_MAC11"]),

    # --- Light Machine Guns (LMGs) ---
    _w("wp_mk48", "Mk 48", "lmg", "espiritu_santo", "Espíritu Santo Western Base", "Base Oeste de Espíritu Santo", 0.785, 0.145, "weapon_case", 64, 58, 36, 64, 68, 66, 38, platform="lmg_belt", forge_patterns=["W_LMG_MK48"]),
    _w("wp_stoner", "Stoner LMG A1", "lmg", "pucara", "Pucara Cartel Bunker", "Bunker do Cartel em Pucara", 0.578, 0.852, "weapon_case", 60, 64, 46, 60, 72, 62, 46, platform="lmg_belt", forge_patterns=["W_LMG_STONER"]),
    _w("wp_mk249", "Mk249", "lmg", "malca", "Malca Unidad Outpost", "Posto Avançado da Unidad em Malca", 0.352, 0.748, "weapon_case", 58, 60, 42, 58, 76, 60, 42, platform="lmg_belt", forge_patterns=["W_LMG_MK249"]),
    _w("wp_6p41", "6P41", "lmg", "media_luna", "Media Luna Airfield South", "Sul do Aeródromo de Media Luna", 0.295, 0.152, "weapon_case", 68, 56, 34, 66, 64, 70, 36, platform="lmg_belt", forge_patterns=["W_LMG_PKP-PECHENEG"]),
    _w("wp_type95", "Type 95", "lmg", "remanzo", "Remanzo Southern Ranch", "Fazenda Sul de Remanzo", 0.455, 0.778, "weapon_case", 60, 66, 48, 60, 68, 60, 44, platform="lmg_mag", supported_slots=["scope", "muzzle", "barrel", "magazine", "underbarrel", "rail"], forge_patterns=["W_LMG_QBB-T95"]),
    _w("wp_mg121", "MG121", "lmg", "itacua", "Itacua Southern Construction Site", "Obra / Heliponto Sul de Itacua", 0.532, 0.642, "weapon_case", 62, 58, 40, 60, 70, 64, 40, platform="lmg_belt", forge_patterns=["W_LMG_MG121"]),
    _w("wp_llamativo", "Llamativo (Boss)", "lmg", "agua_verde", "Defeat Carzita in Agua Verde", "Derrote Carzita em Agua Verde", 0.502, 0.305, "boss_reward", 64, 62, 42, 62, 72, 64, 40, platform="lmg_belt", customizable=False),

    # --- Shotguns ---
    _w("wp_supershorty", "Super Shorty", "shotgun", "itacua", "F.O.B. Armadillo Roof (Itacua)", "Telhado da F.O.B. Armadillo (Itacua)", 0.558, 0.618, "weapon_case", 78, 40, 74, 24, 30, 52, 42, platform="sg_tube", supported_slots=["scope", "muzzle"], forge_patterns=["W_SHG_SHORTY"]),
    _w("wp_sasg12", "SASG-12", "shotgun", "agua_verde", "Agua Verde NE Outpost", "Posto Nordeste de Agua Verde", 0.538, 0.275, "weapon_case", 76, 46, 60, 28, 58, 54, 40, platform="sg_mag", forge_patterns=["W_SHG_SAIGA-12"]),
    _w("wp_spas12", "SPAS-12", "shotgun", "la_cruz", "La Cruz Northern Warehouse", "Armazém Norte de La Cruz", 0.615, 0.618, "weapon_case", 82, 48, 56, 30, 48, 56, 38, platform="sg_tube", forge_patterns=["W_SHG_SPAS-12"]),
    _w("wp_m1014", "M1014", "shotgun", "koani", "Koani Train Yard", "Pátio Ferroviário de Koani", 0.148, 0.125, "weapon_case", 80, 48, 58, 30, 52, 56, 40, platform="sg_tube", forge_patterns=["W_SHG_M1014"]),
    _w("wp_elobsequio", "El Obsequio (Boss)", "shotgun", "barvechos", "Defeat El Pulpo in Barvechos", "Derrote El Pulpo em Barvechos", 0.342, 0.502, "boss_reward", 84, 52, 62, 32, 46, 58, 44, platform="sg_tube", customizable=False, forge_patterns=["W_SHG_SPAS-12_ElObseqio"]),

    # --- Handguns / Pistols ---
    _w("wp_p45t", "P45T", "pistol", "itacua", "Starter Sidearm", "Arma Secundária Inicial", 0.518, 0.628, "starter", 38, 60, 86, 26, 58, 32, 84, platform="pistol_45", forge_patterns=["W_HDG_FNP45"]),
    _w("wp_p12", "P12", "pistol", "tabacal", "Tabacal River Dock", "Doca Fluvial de Tabacal", 0.518, 0.148, "weapon_case", 40, 62, 86, 28, 58, 34, 84, platform="pistol_45", forge_patterns=["W_HDG_P12"]),
    _w("wp_m9", "M9", "pistol", "villa_verde", "Villa Verde River Outpost", "Posto Fluvial de Villa Verde", 0.695, 0.495, "weapon_case", 36, 64, 88, 28, 64, 30, 86, platform="pistol_std", forge_patterns=["W_HDG_BerettaM9"]),
    _w("wp_57usg", "5.7 USG", "pistol", "ocoro", "Ocoro Town Outpost", "Posto da Vila de Ocoro", 0.538, 0.502, "weapon_case", 42, 68, 88, 32, 64, 46, 84, platform="pistol_std", forge_patterns=["W_HDG_57USG"]),
    _w("wp_m1911", "M1911", "pistol", "ocoro", "Ocoro Southern Farm", "Fazenda Sul de Ocoro", 0.518, 0.515, "weapon_case", 44, 60, 84, 26, 54, 36, 82, platform="pistol_45", forge_patterns=["W_HDG_M1911A2"]),
    _w("wp_d50", "D-50 (Desert Eagle)", "pistol", "libertad", "Libertad Northern Outpost", "Posto Norte de Libertad", 0.818, 0.635, "weapon_case", 64, 54, 68, 34, 38, 58, 60, False, "Heavy .50 AE sidearm (cannot mount suppressor).", "Pistola pesada .50 AE (não aceita silenciador).", platform="pistol_50", suppressible=False, forge_patterns=["W_HDG_Deagle"]),
    _w("wp_p227", "P227", "pistol", "malca", "Malca Cartel House", "Casa do Cartel em Malca", 0.328, 0.772, "weapon_case", 41, 64, 86, 28, 60, 34, 84, platform="pistol_std", forge_patterns=["W_HDG_P227"]),
    _w("wp_ladykiller", "Lady Killer (Boss)", "pistol", "itacua", "Defeat La Yuri & El Polito in Itacua", "Derrote La Yuri e El Polito em Itacua", 0.524, 0.616, "boss_reward", 48, 66, 86, 28, 60, 38, 86, platform="pistol_std", customizable=False),
    _w("wp_skorpion", "Skorpion", "pistol", "remanzo", "Remanzo Unidad Outpost", "Posto da Unidad em Remanzo", 0.435, 0.752, "weapon_case", 36, 52, 86, 26, 84, 32, 80, platform="pistol_auto", forge_patterns=["W_SMG_SKORPION"]),
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
    platforms: list[str] | None = None,
    forge_patterns: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": aid,
        "kind": "attachment",
        "name": name,
        "slot": slot,
        "compatible_classes": compat,
        "platforms": list(platforms) if platforms else None,
        "forge_patterns": list(forge_patterns or []),
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
    _att("att_ar_long_barrel", "Long Barrel (AR)", "barrel", ["ar"], "itacua", "Itacua Northern Outpost", "Posto Norte de Itacua", 0.512, 0.595, "+Damage, +Accuracy, +Range, -Handling", "+Dano, +Precisão, +Alcance, -Manuseio", forge_patterns=["W_ASR_ACR-BarrelExtralong"]),
    _att("att_panoramic", "Panoramic Sight", "scope", ["ar", "smg", "lmg", "shotgun"], "itacua", "Itacua Central Village", "Vila Central de Itacua", 0.525, 0.620, "Clear 1x holographic reflex optic", "Mira holográfica limpa 1x", forge_patterns=["W_AT_scopeReflex_AC11704"]),
    _att("att_pkas", "PK-AS Sight", "scope", ["ar", "smg"], "itacua", "Itacua Eastern Farm", "Fazenda Leste de Itacua", 0.542, 0.628, "+Accuracy (1.5x Russian collimator)", "+Precisão (colimador russo 1.5x)", platforms=["ak_762", "asval_9x39", "smg_9mm"], forge_patterns=["W_AT_scopePKAS"]),
    # Ocoro
    _att("att_pistol_extmag", "Extended Mag 30 (Handgun)", "magazine", ["pistol"], "ocoro", "Ocoro East Checkpoint", "Bloqueio Leste de Ocoro", 0.548, 0.492, "+Magazine capacity, -Handling", "+Capacidade do carregador, -Manuseio", forge_patterns=["W_HDG_FNP45-MagExtended"]),
    _att("att_compm4", "CompM4 Scope", "scope", ["ar", "smg", "lmg"], "ocoro", "Ocoro Central Outpost", "Posto Central de Ocoro", 0.532, 0.488, "+Accuracy (Red dot reflex)", "+Precisão (Ponto vermelho)", forge_patterns=["W_AT_scopeCompM4"]),
    _att("att_sr_comp_stock", "Compensated Buttstock (Sniper)", "stock", ["sniper"], "ocoro", "Ocoro West Camp", "Acampamento Oeste de Ocoro", 0.512, 0.495, "+Accuracy, +Handling", "+Precisão, +Manuseio"),
    _att("att_smg_atpial", "ATPIAL Laser Sight (SMG)", "rail", ["smg"], "ocoro", "Ocoro River Base", "Base do Rio de Ocoro", 0.526, 0.506, "+Hip-fire Accuracy & Handling", "+Precisão sem mira e Manuseio", forge_patterns=["W_AT_ATPIAL_laser"]),
    # Tabacal
    _att("att_ar_ext30", "Extended Mag 30 (AR 5.56)", "magazine", ["ar"], "tabacal", "Tabacal North Farm", "Fazenda Norte de Tabacal", 0.515, 0.125, "+Magazine capacity (30 rds)", "+Capacidade (30 munições)", platforms=["nato_556", "bullpup_556"], forge_patterns=["WG_AT_PMAG_Long"]),
    _att("att_sg_long_barrel", "Long Barrel (Shotgun)", "barrel", ["shotgun"], "tabacal", "Tabacal Eastern Village", "Vila Leste de Tabacal", 0.548, 0.142, "+Damage, +Range, +Accuracy", "+Dano, +Alcance, +Precisão"),
    _att("att_smg_folded", "Folded Buttstock (SMG)", "stock", ["smg"], "tabacal", "Tabacal South Outpost", "Posto Sul de Tabacal", 0.532, 0.158, "+Handling, -Accuracy", "+Manuseio, -Precisão", forge_patterns=["WG_SMG_MP5_Stock_Folded"]),
    _att("att_smg_3dot", "Laser 3Dot (SMG)", "rail", ["smg"], "tabacal", "Tabacal West Ridge", "Crista Oeste de Tabacal", 0.505, 0.140, "+Hip-fire spread control", "+Controle de dispersão no quadril", forge_patterns=["WG_AT_laser_3DOT"]),
    # Agua Verde
    _att("att_sg_suppressor", "Shotgun Suppressor", "muzzle", ["shotgun"], "agua_verde", "Agua Verde North Villa", "Vila Norte de Agua Verde", 0.512, 0.278, "Reduces shotgun gunshot hearing to ~41m", "Reduz audibilidade da escopeta para ~41m", forge_patterns=["WG_12Gauge_Suppressor"]),
    _att("att_ar_micro_t1", "Micro T-1 Scope", "scope", ["ar", "smg"], "agua_verde", "Agua Verde West Shore", "Margem Oeste de Agua Verde", 0.478, 0.305, "+Handling, compact 1x reflex", "+Manuseio, mira reflex compacta", forge_patterns=["W_AT_scopeMicroT1"]),
    # Barvechos
    _att("att_hg_atpial", "ATPIAL Laser Sight (Handgun)", "rail", ["pistol"], "barvechos", "Barvechos North Quarry", "Pedreira Norte de Barvechos", 0.335, 0.475, "+Handling, +Accuracy", "+Manuseio, +Precisão", forge_patterns=["WG_AT_PistolLaser"]),
    _att("att_lmg_long", "Long Barrel (LMG)", "barrel", ["lmg"], "barvechos", "Barvechos East Mine", "Mina Leste de Barvechos", 0.358, 0.498, "+Damage, +Range", "+Dano, +Alcance", forge_patterns=["W_LMG_MK48-BarrelLong"]),
    _att("att_smg_comp", "Compensator (SMG)", "muzzle", ["smg"], "barvechos", "Barvechos South Depot", "Depósito Sul de Barvechos", 0.328, 0.522, "+Recoil control, unsuppressed (~61m noise)", "+Controle de recuo, sem silenciador (~61m)", forge_patterns=["WG_AT_SmallCalibreCompensator"]),
    _att("att_smg_short", "Short Barrel (SMG)", "barrel", ["smg"], "barvechos", "Barvechos Central Camp", "Acampamento Central de Barvechos", 0.345, 0.505, "+Handling, +Mobility", "+Manuseio, +Mobilidade"),
    _att("att_afg", "Angled Foregrip (AFG)", "underbarrel", ["ar", "smg", "sniper"], "barvechos", "Barvechos West Pass", "Passagem Oeste de Barvechos", 0.312, 0.495, "+Handling, +ADS speed", "+Manuseio e velocidade de mira", forge_patterns=["W_AT_Angled_ForeGrip"]),
    _att("att_shift_grip", "Shift Short Angled Grip", "underbarrel", ["ar", "smg"], "barvechos", "Barvechos Outpost Delta", "Posto Delta de Barvechos", 0.352, 0.518, "+Handling, +Mobility", "+Manuseio, +Mobilidade", forge_patterns=["W_AT_Angled_ForeGrip_V2"]),
    # Mojocoyo
    _att("att_ar_stanag30", "5.56 STANAG 30 Mag", "magazine", ["ar"], "mojocoyo", "Mojocoyo North Outpost", "Posto Norte de Mojocoyo", 0.168, 0.508, "Standard 30-round STANAG magazine", "Carregador STANAG 30 munições", platforms=["nato_556", "bullpup_556"], forge_patterns=["WG_AT_SATNAG_Long"]),
    _att("att_lmg_3dot", "Laser 3Dot (LMG)", "rail", ["lmg"], "mojocoyo", "Mojocoyo East Village", "Vila Leste de Mojocoyo", 0.188, 0.532, "+Hip-fire control", "+Controle de tiro no quadril", forge_patterns=["WG_AT_laser_3DOT"]),
    _att("att_sr_atpial", "ATPIAL Laser Sight (Sniper)", "rail", ["sniper"], "mojocoyo", "Mojocoyo West Camp", "Acampamento Oeste de Mojocoyo", 0.148, 0.525, "+Handling, +Accuracy", "+Manuseio, +Precisão", forge_patterns=["W_AT_ATPIAL_laser"]),
    _att("att_smg_ext30", "Extended Mag 30 (SMG)", "magazine", ["smg"], "mojocoyo", "Mojocoyo South Depot", "Depósito Sul de Mojocoyo", 0.172, 0.555, "+Magazine capacity", "+Capacidade do carregador"),
    # San Mateo
    _att("att_sr_long_barrel", "Long Barrel (Sniper)", "barrel", ["sniper"], "san_mateo", "San Mateo North Checkpoint", "Bloqueio Norte de San Mateo", 0.330, 0.325, "+Damage, +Range, +Bullet Velocity", "+Dano, +Alcance, +Velocidade de projétil"),
    _att("att_ar_3dot", "Laser 3Dot (AR)", "rail", ["ar"], "san_mateo", "San Mateo East Base", "Base Leste de San Mateo", 0.352, 0.352, "+Accuracy, +Handling", "+Precisão, +Manuseio", forge_patterns=["WG_AT_laser_3DOT"]),
    _att("att_pks07", "PKS-07 Sniper Scope", "scope", ["sniper"], "san_mateo", "San Mateo Canyon Ridge", "Crista do Cânion de San Mateo", 0.312, 0.348, "Long-range tactical sniper optic", "Mira telescópica de longo alcance", forge_patterns=["WG_AT_Scope_PKS07"]),
    _att("att_ar_folded", "Folded Buttstock (AR)", "stock", ["ar"], "san_mateo", "San Mateo South Camp", "Acampamento Sul de San Mateo", 0.338, 0.372, "+Handling, +Mobility", "+Manuseio, +Mobilidade", forge_patterns=["W_ASR_ACR-StockFolded"]),
    # Monte Puncu
    _att("att_ar_comp_v2", "Compensator V2 (AR)", "muzzle", ["ar"], "monte_puncu", "Monte Puncu North Bunker", "Bunker Norte de Monte Puncu", 0.715, 0.258, "+Recoil & Penetration, loud (~93m)", "+Recuo e Penetração, alto (~93m)", forge_patterns=["W_AT_Compensator_V2_556"]),
    _att("att_digital_scope", "Digital Scope", "scope", ["ar", "smg", "lmg"], "monte_puncu", "Monte Puncu Central Town", "Cidade de Monte Puncu", 0.725, 0.282, "2.0x/4.0x variable zoom optic", "Mira com zoom variável 2x/4x", forge_patterns=["WG_AT_scopeSpecterDR"]),
    _att("att_exps_g33", "EXPS & G33 Flip Magnifier", "scope", ["ar", "smg", "lmg"], "monte_puncu", "Monte Puncu East Outpost", "Posto Leste de Monte Puncu", 0.742, 0.288, "1x Holo + 3.5x flip magnifier", "Mira holográfica 1x + ampliador 3.5x", forge_patterns=["W_AT_EXPS3-4_withMagnifier"]),
    _att("att_fg_v4", "Foregrip V4", "underbarrel", ["ar", "lmg"], "monte_puncu", "Monte Puncu South Ridge", "Crista Sul de Monte Puncu", 0.718, 0.305, "+Accuracy, +Recoil control", "+Precisão, +Controle de recuo", forge_patterns=["WG_AT_foregrip_V4"]),
    _att("att_lmg_comp", "Compensator (LMG)", "muzzle", ["lmg"], "monte_puncu", "Monte Puncu West Lab", "Laboratório Oeste de Monte Puncu", 0.698, 0.278, "+Stability, loud (~109m)", "+Estabilidade, alto (~109m)", forge_patterns=["W_AT_Compensator_V2_762"]),
    # Espiritu Santo
    _att("att_ta31h", "TA31H ACOG Scope", "scope", ["ar", "lmg", "sniper"], "espiritu_santo", "Espíritu Santo North Outpost", "Posto Norte de Espíritu Santo", 0.798, 0.132, "4x tactical ACOG optic", "Mira tática ACOG 4x", forge_patterns=["WG_AT_scopeAcog_TA31H"]),
    _att("att_sr_rangefinder", "Range Finder (Sniper)", "rail", ["sniper"], "espiritu_santo", "Espíritu Santo East Shrine", "Santuário Leste de Espíritu Santo", 0.818, 0.165, "+Range, +Bullet drop compensation", "+Alcance e compensação balística", forge_patterns=["WG_AT_rangefinder"]),
    _att("att_lmg_folded", "Folded Buttstock (LMG)", "stock", ["lmg"], "espiritu_santo", "Espíritu Santo South Camp", "Acampamento Sul de Espíritu Santo", 0.792, 0.168, "+Handling, +ADS speed", "+Manuseio e velocidade de mira"),
    # Caimanes
    _att("att_ar_short_barrel", "Short Barrel (AR)", "barrel", ["ar"], "caimanes", "Caimanes North Swamp", "Pântano Norte de Caimanes", 0.848, 0.448, "+Handling, +Mobility", "+Manuseio, +Mobilidade", forge_patterns=["W_ASR_ACR-BarrelShort"]),
    _att("att_ar_mag50", "Large 50-Round Mag (AR)", "magazine", ["ar"], "caimanes", "Caimanes Submarine Dock", "Doca de Submarinos de Caimanes", 0.875, 0.475, "+50 round capacity", "+Capacidade de 50 munições", platforms=["nato_556", "scar_762"], forge_patterns=["WG_AT_Drummag"]),
    _att("att_exps3", "EXPS3 Holographic Sight", "scope", ["ar", "smg", "lmg", "shotgun"], "caimanes", "Caimanes Central Outpost", "Posto Central de Caimanes", 0.858, 0.482, "+Accuracy, clear CQB reticle", "+Precisão, retículo CQB limpo", forge_patterns=["W_AT_EXPS3-4"]),
    _att("att_sr_comp_stock2", "Compensated Buttstock (Sniper)", "stock", ["sniper"], "caimanes", "Caimanes South Island", "Ilha Sul de Caimanes", 0.865, 0.512, "+Stability, +Accuracy", "+Estabilidade, +Precisão"),
    # Flor de Oro
    _att("att_ar_rangefinder", "Range Finder (AR)", "rail", ["ar"], "flor_de_oro", "Flor de Oro North Watchtower", "Torre Norte de Flor de Oro", 0.772, 0.832, "+Range, +Accuracy", "+Alcance, +Precisão", forge_patterns=["WG_AT_rangefinder"]),
    _att("att_lmg_suppressor", "LMG Suppressor", "muzzle", ["lmg"], "flor_de_oro", "M.O.B. Jaguar East Hangar", "Hangar Leste M.O.B. Jaguar", 0.798, 0.848, "Reduces LMG gunshot hearing to ~40m", "Reduz audibilidade de LMG para ~40m", forge_patterns=["WG_AT_MediumCalibreSuppresor"]),
    _att("att_sr_ext30", "Extended Mag 30 (Sniper/DMR)", "magazine", ["sniper"], "flor_de_oro", "Flor de Oro Border Camp", "Acampamento da Fronteira", 0.785, 0.868, "+DMR/Sniper capacity", "+Capacidade para DMR/Sniper", platforms=["dmr_762", "dmr_svd"]),
    _att("att_sr_3dot", "Laser 3Dot (Sniper)", "rail", ["sniper"], "flor_de_oro", "Flor de Oro West Jungle", "Selva Oeste de Flor de Oro", 0.758, 0.845, "+Handling, +Accuracy", "+Manuseio, +Precisão", forge_patterns=["WG_AT_laser_3DOT"]),
    # Libertad
    _att("att_ar_762_30", "Extended Mag 30 (AK 7.62)", "magazine", ["ar"], "libertad", "Libertad North Factory", "Fábrica Norte de Libertad", 0.818, 0.648, "+30rd 7.62x39 capacity", "+30 munições 7.62x39", platforms=["ak_762"], forge_patterns=["W_ASR_AK47_EpicMag"]),
    _att("att_ar_comp_stock", "Compensated Buttstock (AR)", "stock", ["ar"], "libertad", "Libertad East Compound", "Complexo Leste de Libertad", 0.835, 0.662, "+Accuracy, +Recoil control", "+Precisão, +Controle de recuo", forge_patterns=["W_ASR_ACR-FixedStock"]),
    _att("att_sg_ext_tube", "Large Magazine / Tube (Shotgun)", "magazine", ["shotgun"], "libertad", "Libertad South Outpost", "Posto Sul de Libertad", 0.812, 0.682, "+Shell capacity", "+Capacidade de cartuchos"),
    # Malca
    _att("att_lmg_atpial", "ATPIAL Laser Sight (LMG)", "rail", ["lmg"], "malca", "Malca North Quarry", "Pedreira Norte de Malca", 0.335, 0.742, "+Handling, +Accuracy", "+Manuseio, +Precisão", forge_patterns=["W_AT_ATPIAL_laser"]),
    _att("att_sg_comp", "Compensator (Shotgun)", "muzzle", ["shotgun"], "malca", "Malca Cathedral Outpost", "Posto da Catedral de Malca", 0.348, 0.765, "+Tighter spread, loud (~109m)", "+Menor dispersão, alto (~109m)", forge_patterns=["W_AT_12Gauge_Compensator"]),
    _att("att_sr_comp", "Compensator (Sniper)", "muzzle", ["sniper"], "malca", "Malca South Canyon", "Cânion Sul de Malca", 0.322, 0.778, "+Stability, loud (~130m)", "+Estabilidade, alto (~130m)", forge_patterns=["W_AT_Compensator_V2_762"]),
    # Pucara
    _att("att_ar_atpial", "ATPIAL Laser Sight (AR)", "rail", ["ar"], "pucara", "Pucara North Outpost", "Posto Norte de Pucara", 0.562, 0.822, "+Handling, +Hip-fire", "+Manuseio, +Tiro no quadril", forge_patterns=["W_AT_ATPIAL_laser"]),
    _att("att_tars101", "TARS101 Sniper Scope", "scope", ["sniper"], "pucara", "Pucara Western Ruins", "Ruínas Oeste de Pucara", 0.548, 0.842, "4.5x/5.5x variable long-range sniper optic", "Mira telescópica variável 4.5x/5.5x", forge_patterns=["W_AT_scope_TARS101"]),
    _att("att_fg_v2", "Foregrip V2", "underbarrel", ["ar", "lmg", "smg"], "pucara", "Pucara East Village", "Vila Leste de Pucara", 0.582, 0.838, "+Accuracy, +Stability", "+Precisão, +Estabilidade", forge_patterns=["WG_AT_foregrip_RVG"]),
    # Remanzo
    _att("att_m203", "M203 Grenade Launcher", "underbarrel", ["ar"], "remanzo", "Remanzo Central Farm", "Fazenda Central de Remanzo", 0.442, 0.758, "40mm underbarrel grenade launcher", "Lança-granadas 40mm acoplado", platforms=["nato_556", "scar_762", "ak_762"], forge_patterns=["WG_AT_grenadeLauncher"]),
    _att("att_sr_comp_v2", "Compensator V2 (Sniper)", "muzzle", ["sniper"], "remanzo", "Remanzo East Outpost", "Posto Leste de Remanzo", 0.462, 0.768, "+Damage & Penetration, loud (~130m)", "+Dano e Penetração, alto (~130m)", forge_patterns=["W_AT_Compensator_V2_RUSS"]),
    _att("att_sr_ext10", "Extended Mag 10 (.338 Sniper)", "magazine", ["sniper"], "remanzo", "Remanzo West Ranch", "Rancho Oeste de Remanzo", 0.425, 0.748, "+10rd sniper capacity", "+10 munições para rifle sniper", platforms=["bolt_338", "bolt_50"]),
    # Koani
    _att("att_t5xi", "T5Xi Tactical Scope (6x)", "scope", ["sniper"], "koani", "Koani Train Depot North", "Norte do Pátio de Trens de Koani", 0.138, 0.105, "Highest-zoom 6x sniper optic in base game", "Mira sniper 6x de maior alcance do jogo base", forge_patterns=["W_AT_scopeT5XI"]),
    _att("att_posp", "POSP Scope", "scope", ["sniper", "ar"], "koani", "Koani Salt Flats Outpost", "Posto do Salar de Koani", 0.155, 0.135, "4x Eastern Bloc optic", "Mira tática russa 4x", platforms=["ak_762", "asval_9x39", "dmr_svd"], forge_patterns=["W_AT_scopePOSP"]),
    _att("att_micro_g33", "Micro T-1 & G33 Magnifier", "scope", ["ar", "smg", "lmg"], "koani", "Koani Airbase East", "Base Aérea Leste de Koani", 0.165, 0.118, "Compact reflex + 3x flip magnifier", "Reflex compacta + ampliador 3x", forge_patterns=["W_AT_scopeMicroT1_withMagnifier"]),
    _att("att_hg_ext15", "Extended Mag 15 (Handgun)", "magazine", ["pistol"], "koani", "Koani Southwest Checkpoint", "Bloqueio Sudoeste de Koani", 0.125, 0.155, "+Pistol capacity", "+Capacidade de pistola", forge_patterns=["W_HDG_BerettaM9-Mag"]),
    # Media Luna
    _att("att_sr_suppressor", "Sniper Suppressor", "muzzle", ["sniper"], "media_luna", "Media Luna Western Outpost", "Posto Oeste de Media Luna", 0.288, 0.135, "Reduces sniper gunshot hearing to ~48m", "Reduz audibilidade de sniper para ~48m", forge_patterns=["WG_AT_HighCalibreSuppresor", "WG_AT_50BGM_Suppressor"]),
    _att("att_ar_suppressor", "AR Suppressor", "muzzle", ["ar"], "media_luna", "Media Luna Central Base", "Base Central de Media Luna", 0.312, 0.132, "Reduces AR gunshot hearing to ~34m", "Reduz audibilidade de fuzil para ~34m", forge_patterns=["WG_AT_AK_Suppressor"]),
    _att("att_smg_rangefinder", "Range Finder (SMG)", "rail", ["smg"], "media_luna", "Media Luna Eastern Canyon", "Cânion Leste de Media Luna", 0.338, 0.145, "+Range, +Accuracy", "+Alcance, +Precisão", forge_patterns=["WG_AT_rangefinder"]),
    # Inca Camina
    _att("att_g28_scope", "G28 Scope (5x + Red Dot)", "scope", ["sniper", "ar"], "inca_camina", "Inca Camina Airfield", "Aeródromo de Inca Camina", 0.175, 0.858, "Dual-role 5x sniper + top red dot", "Mira dupla 5x sniper + red dot superior", forge_patterns=["W_AT_scopeG28"]),
    _att("att_lmg_ext200", "200-Round Ammo Box (LMG)", "magazine", ["lmg"], "inca_camina", "Inca Camina Peak Outpost", "Posto do Pico de Inca Camina", 0.195, 0.872, "+200rd LMG box", "+Caixa de 200 munições LMG", platforms=["lmg_belt"]),
    # Montuyoc
    _att("att_hg_3dot", "Laser 3Dot (Handgun)", "rail", ["pistol"], "montuyoc", "Montuyoc South Pass", "Passagem Sul de Montuyoc", 0.222, 0.688, "+Hip-fire pistol accuracy", "+Precisão de pistola sem mira", forge_patterns=["WG_AT_PistolLaser"]),
    _att("att_lmg_comp_v2", "Compensator V2 (LMG)", "muzzle", ["lmg"], "montuyoc", "Montuyoc East Checkpoint", "Bloqueio Leste de Montuyoc", 0.242, 0.672, "+Damage & Stability, loud (~109m)", "+Dano e Estabilidade, alto (~109m)", forge_patterns=["W_AT_Compensator_V2_762"]),
    # La Cruz & Villa Verde
    _att("att_std_gl", "STD Grenade Launcher", "underbarrel", ["ar"], "la_cruz", "La Cruz South Warehouse", "Armazém Sul de La Cruz", 0.618, 0.652, "High-explosive underbarrel launcher", "Lança-granadas acoplado", platforms=["nato_556", "scar_762", "ak_762"], forge_patterns=["W_AT_G320"]),
    _att("att_ar_flash_hider", "Flash Hider (AR)", "muzzle", ["ar"], "la_cruz", "La Cruz West Farm", "Fazenda Oeste de La Cruz", 0.602, 0.638, "Hides muzzle flash, loud (~93m)", "Oculta clarão do disparo, alto (~93m)", forge_patterns=["W_ASR_ACR-FlashHider"]),
    _att("att_vv_grip", "Vertical Foregrip", "underbarrel", ["ar", "smg", "lmg"], "villa_verde", "Villa Verde South Camp", "Acampamento Sul de Villa Verde", 0.692, 0.488, "+Accuracy, +Handling", "+Precisão, +Manuseio", forge_patterns=["WG_AT_foregrip_V3"]),
]

# Medalhas de Bônus (todas as 30 medalhas passivas permanentes verificadas no GRN_WorldMap / Game Bootstrap Settings)
BONUS_MEDALS: list[dict[str, Any]] = [
    {"id": "med_air_vhc_dmg", "vid": 565442030236, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_AirVHCDamage", "kind": "medal", "name_en": "Aircraft Destruction Medal", "name_pt": "Medalha de Destruição Aérea", "province": "barvechos", "location_en": "Barvechos Northwest Outpost", "location_pt": "Posto Noroeste de Barvechos", "u": 0.2598, "v": 0.385, "bonus_en": "+20% Damage to Aircraft", "bonus_pt": "+20% de Dano contra Aeronaves"},
    {"id": "med_ammo", "vid": 894883027816, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_AmmoCapacity", "kind": "medal", "name_en": "Munitions Medal (Ammo Capacity)", "name_pt": "Medalha de Munição (Capacidade)", "province": "barvechos", "location_en": "Barvechos West Mine", "location_pt": "Mina Oeste de Barvechos", "u": 0.2614, "v": 0.4315, "bonus_en": "+25% Max Reserve Ammo", "bonus_pt": "+25% de Munição Reserva Máxima"},
    {"id": "med_c4", "vid": 557284981349, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_C4", "kind": "medal", "name_en": "Demolitions Medal (C4 Capacity)", "name_pt": "Medalha de Demolição (Capacidade C4)", "province": "koani", "location_en": "Koani West Salt Flats", "location_pt": "Salar Oeste de Koani", "u": 0.0805, "v": 0.0952, "bonus_en": "+2 Extra C4 Charges", "bonus_pt": "+2 Cargas Extras de C4"},
    {"id": "med_car_dmg", "vid": 557284981350, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_CarDamage", "kind": "medal", "name_en": "Anti-Convoy Medal (Vehicle Damage)", "name_pt": "Medalha Anticomboio (Dano Veicular)", "province": "koani", "location_en": "Koani East Train Graveyard", "location_pt": "Cemitério de Trens de Koani", "u": 0.2402, "v": 0.1027, "bonus_en": "+20% Damage to Ground Vehicles", "bonus_pt": "+20% de Dano contra Veículos Terrestres"},
    {"id": "med_drone_mark", "vid": 702366581357, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_DroneMarkArea", "kind": "medal", "name_en": "Drone Recon Medal (Mark Area)", "name_pt": "Medalha de Reconhecimento de Drone", "province": "media_luna", "location_en": "Media Luna North Ridge", "location_pt": "Crista Norte de Media Luna", "u": 0.2956, "v": 0.0914, "bonus_en": "+50% Drone Marking Cone", "bonus_pt": "+50% de Área de Marcação do Drone"},
    {"id": "med_flare", "vid": 758868234459, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_Flare", "kind": "medal", "name_en": "Signal Flare Medal", "name_pt": "Medalha de Sinalizador", "province": "media_luna", "location_en": "Media Luna South Canyon", "location_pt": "Cânion Sul de Media Luna", "u": 0.357, "v": 0.2191, "bonus_en": "+2 Extra Flares", "bonus_pt": "+2 Sinalizadores Extras"},
    {"id": "med_drone_range", "vid": 565442030375, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_DroneRange", "kind": "medal", "name_en": "Tech Specialist Medal (Drone Range)", "name_pt": "Medalha Especialista Tech (Alcance do Drone)", "province": "mojocoyo", "location_en": "Mojocoyo Northwest Camp", "location_pt": "Acampamento Noroeste de Mojocoyo", "u": 0.1413, "v": 0.2949, "bonus_en": "+25% Drone Signal Range", "bonus_pt": "+25% de Alcance do Drone"},
    {"id": "med_flash", "vid": 565442030381, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_FlashGrenade", "kind": "medal", "name_en": "Breacher Medal (Flashbang)", "name_pt": "Medalha de Invasão (Granada deLuz)", "province": "mojocoyo", "location_en": "Mojocoyo North Base", "location_pt": "Base Norte de Mojocoyo", "u": 0.1883, "v": 0.2766, "bonus_en": "+2 Extra Flashbang Grenades", "bonus_pt": "+2 Granadas de Luz Extras"},
    {"id": "med_hipfire", "vid": 647264435473, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_HipFire", "kind": "medal", "name_en": "Close Quarters Medal (Hip Fire)", "name_pt": "Medalha CQB (Tiro Livre)", "province": "montuyoc", "location_en": "Montuyoc West Bunker", "location_pt": "Bunker Oeste de Montuyoc", "u": 0.1292, "v": 0.6017, "bonus_en": "-20% Hip-Fire Spread", "bonus_pt": "-20% de Dispersão em Tiro Livre"},
    {"id": "med_squad_res", "vid": 580754923830, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_SquadResilience", "kind": "medal", "name_en": "Squad Resilience Medal", "name_pt": "Medalha de Resiliência do Esquadrão", "province": "remanzo", "location_en": "Remanzo Valley Compound", "location_pt": "Complexo do Vale de Remanzo", "u": 0.2494, "v": 0.3075, "bonus_en": "+25% AI Teammate Health", "bonus_pt": "+25% de Resistência dos Aliados"},
    {"id": "med_stable_aim", "vid": 548390523313, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_StableAiming", "kind": "medal", "name_en": "Sharpshooter Medal (Stable Aim)", "name_pt": "Medalha de Atirador de Elite (Mira Estável)", "province": "san_mateo", "location_en": "San Mateo East Watchtower", "location_pt": "Torre Leste de San Mateo", "u": 0.3777, "v": 0.3599, "bonus_en": "-25% Weapon Sway", "bonus_pt": "-25% de Oscilação da Mira"},
    {"id": "med_time_aim", "vid": 556371017062, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_TimeToAim", "kind": "medal", "name_en": "Quick Draw Medal (ADS Speed)", "name_pt": "Medalha de Saque Rápido (Velocidade de Mira)", "province": "tabacal", "location_en": "Tabacal North Plantation", "location_pt": "Plantação Norte de Tabacal", "u": 0.5766, "v": 0.0946, "bonus_en": "+20% Aim Down Sights Speed", "bonus_pt": "+20% de Velocidade ao Mirar"},
    {"id": "med_bino_mark", "vid": 553387872434, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_BinocularMarkArea", "kind": "medal", "name_en": "Spotter Medal (Binocular Area)", "name_pt": "Medalha de Observador (Binóculos)", "province": "caimanes", "location_en": "Caimanes South Swamp Base", "location_pt": "Base Sul do Pântano de Caimanes", "u": 0.7897, "v": 0.5897, "bonus_en": "+50% Binocular Marking Cone", "bonus_pt": "+50% de Área de Marcação dos Binóculos"},
    {"id": "med_quiet_run", "vid": 1055056516419, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_SilentRunning", "kind": "medal", "name_en": "Quiet Running Medal", "name_pt": "Medalha de Corrida Silenciosa", "province": "espiritu_santo", "location_en": "Espíritu Santo East Ridge", "location_pt": "Crista Leste de Espíritu Santo", "u": 0.8324, "v": 0.1456, "bonus_en": "-25% Footstep Noise", "bonus_pt": "-25% de Ruído ao Correr"},
    {"id": "med_thermal", "vid": 535924038003, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_BinocularZoom", "kind": "medal", "name_en": "Recon Medal (Binocular Zoom)", "name_pt": "Medalha de Reconhecimento (Zoom Binóculos)", "province": "flor_de_oro", "location_en": "Flor de Oro South FOB", "location_pt": "FOB Sul de Flor de Oro", "u": 0.7627, "v": 0.8942, "bonus_en": "+2x Binocular Zoom Level", "bonus_pt": "+2x de Zoom nos Binóculos"},
    {"id": "med_born_leader", "vid": 563505218278, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_BornLeader", "kind": "medal", "name_en": "Born Leader Medal", "name_pt": "Medalha Líder Nato", "province": "itacua", "location_en": "Itacua North Ruins", "location_pt": "Ruínas Norte de Itacua", "u": 0.5066, "v": 0.6028, "bonus_en": "+20% Squad Combat Efficiency", "bonus_pt": "+20% de Eficiência do Esquadrão"},
    {"id": "med_bullet_res", "vid": 647884648840, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_BulletResist", "kind": "medal", "name_en": "Ballistic Vest Medal (Bullet Resistance)", "name_pt": "Medalha de Proteção Balística", "province": "itacua", "location_en": "Itacua Northeast Outpost", "location_pt": "Posto Nordeste de Itacua", "u": 0.543, "v": 0.5562, "bonus_en": "+10% Bullet Damage Resistance", "bonus_pt": "+10% de Resistência a Disparos"},
    {"id": "med_detection", "vid": 553387872494, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_Detection", "kind": "medal", "name_en": "Stealth Medal (Enemy Detection)", "name_pt": "Medalha de Furtividade (Detecção)", "province": "la_cruz", "location_en": "La Cruz East Ridge", "location_pt": "Crista Leste de La Cruz", "u": 0.7989, "v": 0.746, "bonus_en": "Slows enemy visual detection speed", "bonus_pt": "Reduz velocidade de detecção visual inimiga"},
    {"id": "med_diversion", "vid": 554164921902, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_DiversionGrenade", "kind": "medal", "name_en": "Deception Medal (Diversion Lure)", "name_pt": "Medalha de Distração (Isca Sonora)", "province": "libertad", "location_en": "Libertad Central Outpost", "location_pt": "Posto Central de Libertad", "u": 0.8383, "v": 0.7971, "bonus_en": "+2 Extra Diversion Lures", "bonus_pt": "+2 Granadas de Distração Extras"},
    {"id": "med_drone_armor", "vid": 554164921908, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_DroneArmor", "kind": "medal", "name_en": "Armored Drone Medal", "name_pt": "Medalha de Blindagem do Drone", "province": "libertad", "location_en": "Libertad Southeast Border", "location_pt": "Fronteira Sudeste de Libertad", "u": 0.8747, "v": 0.9398, "bonus_en": "+50% Drone Durability", "bonus_pt": "+50% de Resistência do Drone"},
    {"id": "med_explosion", "vid": 568996212235, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_ExplosionResistance", "kind": "medal", "name_en": "Flak Jacket Medal (Blast Resistance)", "name_pt": "Medalha Antiexplosão", "province": "malca", "location_en": "Malca Shrine Hill", "location_pt": "Colina do Santuário de Malca", "u": 0.6079, "v": 0.8393, "bonus_en": "+20% Explosion Damage Resistance", "bonus_pt": "+20% de Resistência a Explosões"},
    {"id": "med_drone_speed", "vid": 556371017240, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_DroneSpeed", "kind": "medal", "name_en": "High-Speed Drone Medal", "name_pt": "Medalha de Velocidade do Drone", "province": "monte_puncu", "location_en": "Monte Puncu North Relay", "location_pt": "Antena Norte de Monte Puncu", "u": 0.6916, "v": 0.1517, "bonus_en": "+25% Drone Flight Speed", "bonus_pt": "+25% de Velocidade do Drone"},
    {"id": "med_frag", "vid": 904007965557, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_FragGrenade", "kind": "medal", "name_en": "Grenadier Medal (Frag Capacity)", "name_pt": "Medalha de Granadeiro (Fragmentação)", "province": "monte_puncu", "location_en": "Monte Puncu Northwest Valley", "location_pt": "Vale Noroeste de Monte Puncu", "u": 0.6375, "v": 0.1094, "bonus_en": "+2 Extra Frag Grenades", "bonus_pt": "+2 Granadas de Fragmentação Extras"},
    {"id": "med_mine", "vid": 538107133074, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_Mine", "kind": "medal", "name_en": "Sapper Medal (Mine Capacity)", "name_pt": "Medalha de Sapador (Minas)", "province": "ocoro", "location_en": "Ocoro North River Camp", "location_pt": "Acampamento Norte do Rio Ocoro", "u": 0.5624, "v": 0.3704, "bonus_en": "+2 Extra Mines", "bonus_pt": "+2 Minas Terrestres Extras"},
    {"id": "med_rebel_icon", "vid": 648457331000, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_RebelIcon", "kind": "medal", "name_en": "Kataris 26 Medal (Rebel Support)", "name_pt": "Medalha Kataris 26 (Apoio Rebelde)", "province": "agua_verde", "location_en": "Agua Verde East Island", "location_pt": "Ilha Leste de Agua Verde", "u": 0.5631, "v": 0.2681, "bonus_en": "-20% Rebel Support Cooldown", "bonus_pt": "-20% de Recarga de Apoio Rebelde"},
    {"id": "med_no_pain", "vid": 648458011036, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_NoPain", "kind": "medal", "name_en": "Endurance Medal (Pain Suppression)", "name_pt": "Medalha de Vigor (Supressão de Dor)", "province": "agua_verde", "location_en": "Agua Verde Central Resort", "location_pt": "Resort Central de Agua Verde", "u": 0.5044, "v": 0.2779, "bonus_en": "+25% Health Regeneration Speed", "bonus_pt": "+25% de Velocidade de Regeneração"},
    {"id": "med_revive", "vid": 567831377574, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_ReviveSpeed", "kind": "medal", "name_en": "Medic Medal (Revive Speed)", "name_pt": "Medalha Médica (Velocidade de Reanimação)", "province": "pucara", "location_en": "Pucara Dam Outpost", "location_pt": "Posto da Represa de Pucara", "u": 0.3834, "v": 0.704, "bonus_en": "+25% Teammate Revive Speed", "bonus_pt": "+25% de Velocidade de Reanimação"},
    {"id": "med_vehicle_armor", "vid": 543318942909, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_VHCDestruction", "kind": "medal", "name_en": "Heavy Ordnance Medal (Vehicle Destruction)", "name_pt": "Medalha de Artilharia Pesada (Destruição Veicular)", "province": "villa_verde", "location_en": "Villa Verde Northeast Jungle", "location_pt": "Selva Nordeste de Villa Verde", "u": 0.9289, "v": 0.1282, "bonus_en": "+25% Vehicle & Turret Damage", "bonus_pt": "+25% de Dano contra Blindados"},
    {"id": "med_drone_cd", "vid": 543318942910, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_DroneCooldown", "kind": "medal", "name_en": "Drone Battery Medal (Cooldown)", "name_pt": "Medalha de Bateria de Drone (Recarga)", "province": "villa_verde", "location_en": "Villa Verde North Quarry", "location_pt": "Pedreira Norte de Villa Verde", "u": 0.8744, "v": 0.2271, "bonus_en": "-25% Drone Cooldown", "bonus_pt": "-25% de Tempo de Recarga do Drone"},
    {"id": "med_bleedout", "vid": 903029104411, "gbs_name": "DBLootConfig_SpecificBonusUpgrade_BleedOutTime", "kind": "medal", "name_en": "Survivor Medal (Bleed Out Time)", "name_pt": "Medalha de Sobrevivência (Tempo de Sangramento)", "province": "inca_camina", "location_en": "Inca Camina South Peak", "location_pt": "Pico Sul de Inca Camina", "u": 0.286, "v": 0.808, "bonus_en": "+50% Bleed Out Time Before Death", "bonus_pt": "+50% de Tempo para Reanimação"},
]

# Categorias do Mapa Tático (12 categorias GRW com ícones oficiais)
MAP_CATEGORIES: list[dict[str, Any]] = [
    {"id": "weapon_case", "name_en": "Weapon Cases", "name_pt": "Caixas de Armas", "color": "#f59e0b", "icon": "weapon_case"},
    {"id": "attachment_case", "name_en": "Weapon Attachments", "name_pt": "Acessórios de Arma", "color": "#38bdf8", "icon": "attachment_case"},
    {"id": "bonus_medal", "name_en": "Bonus Medals", "name_pt": "Medalhas de Bônus", "color": "#eab308", "icon": "bonus_medal"},
    {"id": "skill_point", "name_en": "Skill Points", "name_pt": "Pontos de Habilidade", "color": "#34d399", "icon": "skill_point"},
    {"id": "kingslayer", "name_en": "Documents (Kingslayer Files)", "name_pt": "Documentos (Kingslayer)", "color": "#cbd5e1", "icon": "kingslayer"},
    {"id": "rebel_op", "name_en": "Rebel Ops & Intel", "name_pt": "Operações & Informações", "color": "#22c55e", "icon": "rebel_op"},
    {"id": "sb_base", "name_en": "Santa Blanca Bases", "name_pt": "Bases Santa Blanca", "color": "#d4a017", "icon": "sb_base"},
    {"id": "unidad_base", "name_en": "Unidad Fortresses", "name_pt": "Fortalezas Unidad", "color": "#9333ea", "icon": "unidad_base"},
    {"id": "sam_site", "name_en": "SAM Launchers", "name_pt": "Baterias SAM", "color": "#fb7185", "icon": "sam_site"},
    {"id": "jammer", "name_en": "Drone Jammers", "name_pt": "Bloqueadores de Drone", "color": "#f43f5e", "icon": "jammer"},
    {"id": "rally_point", "name_en": "Rally Points (Fast Travel)", "name_pt": "Pontos de Encontro", "color": "#60a5fa", "icon": "rally_point"},
    {"id": "boss_hq", "name_en": "Buchón / Cartel Bosses", "name_pt": "Chefes / Buchones", "color": "#dc2626", "icon": "boss_hq"},
]


def _is_attachment_compatible(weapon: dict[str, Any], attachment: dict[str, Any]) -> bool:
    """Determina compatibilidade real Arma <-> Acessório (Armeiro do GRW)."""
    if not weapon.get("customizable", True):
        return False
    if weapon["weapon_class"] not in (attachment.get("compatible_classes") or []):
        return False
    if attachment["slot"] not in (weapon.get("supported_slots") or []):
        return False
    if "suppressor" in attachment["id"] and not weapon.get("suppressible", True):
        return False
    platforms = attachment.get("platforms")
    if platforms and weapon.get("platform") not in platforms:
        return False
    return True


def build_static_databases(
    lang: str = "pt-BR",
    wm_collectibles: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Gera map_data, catalog (com compatibilidade bidirecional) e cartel (com missões e tarefas por província)."""
    is_pt = lang.lower().startswith("pt")
    prov_by_id = {p["id"]: p for p in PROVINCES}
    slot_labels = {s["id"]: (s["label_pt"] if is_pt else s["label_en"]) for s in ATTACHMENT_SLOTS}
    class_labels = {c["id"]: (c["label_pt"] if is_pt else c["label_en"]) for c in WEAPON_CLASSES}
    pois: list[dict[str, Any]] = []
    wm_docs = list((wm_collectibles or {}).get("documents") or [])
    wm_skills = list((wm_collectibles or {}).get("skill_points") or [])

    # 1. Prepara armas e acessórios localizados
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
            "compatible_attachments": [],
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
            "compatible_weapons": [],
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

    # Calcula compatibilidade bidirecional Arma <-> Acessório agrupada por categoria
    for w_entry in catalog_weapons:
        by_slot: dict[str, list[dict[str, Any]]] = {}
        for a_entry in catalog_attachments:
            if _is_attachment_compatible(w_entry, a_entry):
                by_slot.setdefault(a_entry["slot"], []).append({
                    "id": a_entry["id"],
                    "name": a_entry["name"],
                    "slot": a_entry["slot"],
                    "province": a_entry["province"],
                    "province_name": a_entry["province_name"],
                    "location": a_entry["location"],
                    "u": a_entry["u"],
                    "v": a_entry["v"],
                })
        groups = []
        for slot_meta in ATTACHMENT_SLOTS:
            sid = slot_meta["id"]
            if sid in by_slot:
                groups.append({
                    "slot": sid,
                    "slot_label": slot_labels[sid],
                    "items": by_slot[sid],
                })
        w_entry["compatible_attachments"] = groups

    for a_entry in catalog_attachments:
        by_cls: dict[str, list[dict[str, Any]]] = {}
        for w_entry in catalog_weapons:
            if _is_attachment_compatible(w_entry, a_entry):
                by_cls.setdefault(w_entry["weapon_class"], []).append({
                    "id": w_entry["id"],
                    "name": w_entry["name"],
                    "weapon_class": w_entry["weapon_class"],
                    "province": w_entry["province"],
                    "province_name": w_entry["province_name"],
                    "location": w_entry["location"],
                    "u": w_entry["u"],
                    "v": w_entry["v"],
                })
        groups = []
        for cls_meta in WEAPON_CLASSES:
            cid = cls_meta["id"]
            if cid in by_cls:
                groups.append({
                    "weapon_class": cid,
                    "class_label": class_labels[cid],
                    "items": by_cls[cid],
                })
        a_entry["compatible_weapons"] = groups

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
            "vid": m.get("vid"),
            "gbs_name": m.get("gbs_name"),
            "desc": f"{loc} — {bon}",
        })

    # 3b. Documentos (Kingslayer Files) e Pontos de Habilidade extraídos do GRN_WorldMap (com fallback sintético caso offline)
    docs_by_prov: dict[str, list[dict[str, Any]]] = {}
    for d in wm_docs:
        pr = str(d.get("province") or "")
        if pr in prov_by_id:
            docs_by_prov.setdefault(pr, []).append(d)

    skills_by_prov: dict[str, list[dict[str, Any]]] = {}
    for sp in wm_skills:
        pr = str(sp.get("province") or "")
        if pr in prov_by_id:
            skills_by_prov.setdefault(pr, []).append(sp)

    # 4. Bases, Pontos de Encontro, SAMs, Jammers, Rebel Ops, Documentos & Pontos de Habilidade por província
    for idx, p in enumerate(PROVINCES):
        pid = p["id"]
        u, v = p["u"], p["v"]
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

        p_skills = skills_by_prov.get(pid) or []
        if p_skills:
            for s_idx, sp in enumerate(p_skills, 1):
                tier = str(sp.get("tier") or "")
                pts_txt = "+5" if "Hard" in tier else ("+3" if "Medium" in tier else "+1")
                pois.append({
                    "id": str(sp.get("id") or f"skill_{pid}_{s_idx:02d}"),
                    "cat": "skill_point",
                    "name": f"{'Ponto de Habilidade' if is_pt else 'Skill Point'} #{s_idx:02d} ({pts_txt})",
                    "province": pid,
                    "province_name": p["name"],
                    "u": float(sp["u"]),
                    "v": float(sp["v"]),
                    "vid": sp.get("vid"),
                    "desc": f"{p['name']} — {pts_txt} {'Pontos de Habilidade' if is_pt else 'Skill Points'}",
                })
        else:
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

        p_docs = docs_by_prov.get(pid) or []
        if p_docs:
            for d_idx, doc in enumerate(p_docs, 1):
                gbs_nm = str(doc.get("gbs_name") or "")
                is_leg = "_LEG_" in gbs_nm
                if is_pt:
                    d_title = f"Lenda Boliviana #{d_idx:02d} — {p['name']}" if is_leg else f"Documento Kingslayer #{d_idx:02d} — {p['name']}"
                    d_desc = f"Lenda regional ({gbs_nm})" if is_leg else f"Arquivo da Op. Regicida / Dossiê ({gbs_nm})"
                else:
                    d_title = f"Bolivian Legend #{d_idx:02d} — {p['name']}" if is_leg else f"Kingslayer Document #{d_idx:02d} — {p['name']}"
                    d_desc = f"Regional Legend ({gbs_nm})" if is_leg else f"Kingslayer File / Intel Dossier ({gbs_nm})"
                pois.append({
                    "id": str(doc.get("id") or f"ks_{pid}_{d_idx:02d}"),
                    "cat": "kingslayer",
                    "name": d_title,
                    "province": pid,
                    "province_name": p["name"],
                    "u": float(doc["u"]),
                    "v": float(doc["v"]),
                    "vid": doc.get("vid"),
                    "gbs_name": gbs_nm,
                    "desc": d_desc,
                })
        else:
            pois.append({
                "id": f"ks_{pid}",
                "cat": "kingslayer",
                "name": f"{'Documento Kingslayer' if is_pt else 'Kingslayer Document'} — {p['name']}",
                "province": pid,
                "province_name": p["name"],
                "u": round(max(0.03, min(0.97, u + 0.015)), 4),
                "v": round(max(0.03, min(0.97, v - 0.018)), 4),
                "desc": ("Dossiê de inteligência sobre o cartel e a região" if is_pt else "Cartel & regional intelligence dossier"),
            })
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

    # Constrói resumo detalhado de tarefas e missões por província para a aba Cartel & Províncias
    provs_out: list[dict[str, Any]] = []
    for p in PROVINCES:
        pid = p["id"]
        missions_out = [
            {
                "id": m["id"],
                "name": m["name_pt"] if is_pt else m["name_en"],
                "is_boss": m["is_boss"],
                "u": m["u"],
                "v": m["v"],
            }
            for m in p["missions"]
        ]
        p_weapons = [
            {
                "id": w["id"],
                "item_id": w["id"],
                "poi_id": f"poi_{w['id']}",
                "cat": "weapon_case",
                "name": w["name"],
                "location": w["location"],
                "obtain_type": w["obtain_type"],
                "u": w["u"],
                "v": w["v"],
            }
            for w in catalog_weapons
            if w["province"] == pid
        ]
        p_atts = [
            {
                "id": a["id"],
                "item_id": a["id"],
                "poi_id": f"poi_{a['id']}",
                "cat": "attachment_case",
                "name": a["name"],
                "location": a["location"],
                "u": a["u"],
                "v": a["v"],
            }
            for a in catalog_attachments
            if a["province"] == pid
        ]
        p_medals = [
            {
                "id": m["id"],
                "item_id": m["id"],
                "poi_id": f"poi_{m['id']}",
                "vid": m.get("vid"),
                "gbs_name": m.get("gbs_name"),
                "cat": "bonus_medal",
                "name": m["name"],
                "location": m["location"],
                "u": m["u"],
                "v": m["v"],
            }
            for m in catalog_medals
            if m["province"] == pid
        ]

        def _poi_tasks(cat_id: str) -> list[dict[str, Any]]:
            return [
                {
                    "id": poi["id"],
                    "item_id": poi.get("item_id"),
                    "poi_id": poi["id"],
                    "vid": poi.get("vid"),
                    "gbs_name": poi.get("gbs_name"),
                    "cat": poi["cat"],
                    "name": poi["name"],
                    "location": poi.get("desc", ""),
                    "u": poi["u"],
                    "v": poi["v"],
                }
                for poi in pois
                if poi["province"] == pid and poi["cat"] == cat_id
            ]

        provs_out.append({
            "id": pid,
            "name": p["name"],
            "wing": p["wing"],
            "boss": p["boss"],
            "skulls": p["skulls"],
            "u": p["u"],
            "v": p["v"],
            "biome": p["biome_pt"] if is_pt else p["biome_en"],
            "desc": p["desc_pt"] if is_pt else p["desc_en"],
            "missions": missions_out,
            "tasks": {
                "missions": missions_out,
                "weapons": p_weapons,
                "attachments": p_atts,
                "medals": p_medals,
                "skill_points": _poi_tasks("skill_point"),
                "kingslayer": _poi_tasks("kingslayer"),
                "rebel_ops": _poi_tasks("rebel_op"),
                "rally_points": _poi_tasks("rally_point"),
                "bases": _poi_tasks("sb_base") + _poi_tasks("unidad_base") + _poi_tasks("sam_site") + _poi_tasks("jammer"),
            },
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
        "weapon_classes": [
            {"id": c["id"], "label": c["label_pt"] if is_pt else c["label_en"]}
            for c in WEAPON_CLASSES
        ],
        "attachment_slots": [
            {"id": s["id"], "label": s["label_pt"] if is_pt else s["label_en"]}
            for s in ATTACHMENT_SLOTS
        ],
    }
    cartel_data = {
        "leader": "El Sueño",
        "wings": wings_out,
        "provinces": provs_out,
    }
    return map_data, catalog_data, cartel_data


_WEAPON_GBS_PREFIXES = ("ASR_", "SMG_", "LMG_", "SNR_", "SNP_", "STG_", "SHG_", "HDG_", "CMG_", "CRB_", "LEG_")

_GBS_WEAPON_EXACT_MAP: dict[str, str] = {
    "ASR_P416": "wp_p416",
    "ASR_M4A1": "wp_m4a1",
    "ASR_ACR": "wp_acr",
    "ASR_MK17": "wp_mk17",
    "ASR_TAR21": "wp_tar21",
    "ASR_AUG-A3": "wp_auga3",
    "ASR_SIG556": "wp_556xi",
    "ASR_AK47": "wp_ak47",
    "ASR_AK47_LEG_HIS": "wp_ak47",
    "ASR_AK47_LEG_HERS": "wp_ak47",
    "ASR_AK-12": "wp_ak12",
    "ASR_R5GP": "wp_r5rgp",
    "ASR_FAMAS": "wp_g2",
    "ASR_805 BREN A2": "wp_805bren",
    "ASR_L85A2": "wp_l85a2",
    "ASR_SR3M": "wp_sr3m",
    "LEG_ASR_AK-12_RITMO": "wp_ritmo",
    "SNR_M40A5": "wp_m40a5",
    "SNR_HTI": "wp_hti",
    "SNR_MSR": "wp_msr",
    "SNR_L115A3": "wp_l115a3",
    "SNR_MK14": "wp_mk14",
    "SNR_G28": "wp_g28",
    "SNR_SR25": "wp_sr25",
    "SNR_DRAGUNOV": "wp_svd",
    "SNR_SRSA1": "wp_srsa1",
    "SNR_M1891": "wp_m1891",
    "SNR_DSR1": "wp_sr1",
    "SMG_MP5": "wp_mp5",
    "SMG_MP7": "wp_mp7",
    "SMG_Vector": "wp_vector",
    "SMG_P90": "wp_p90",
    "SMG_SCPN-EVO3": "wp_scorpion",
    "SMG_PP19": "wp_pp19",
    "SMG_PP19_Executioner": "wp_pp19",
    "LEG_SMG_PP19_RESIDUOS": "wp_pp19",
    "SMG_KAC-PDW": "wp_sr635",
    "SMG_KAC-PDW_SR635_Apparition": "wp_sr635",
    "SMG_PSG": "wp_psg",
    "SMG_VITYAZ": "wp_9x19vsn",
    "SMG_STERLING": "wp_9mmc1",
    "SMG_MPX": "wp_mpx",
    "CMG_MAC11": "wp_smg11",
    "LMG_MK48": "wp_mk48",
    "LMG_STONER": "wp_stoner",
    "LMG_STONER_Armored": "wp_stoner",
    "LMG_KRYTAC": "wp_mk249",
    "LMG_KRYTAC_EPIC_PATON": "wp_mk249",
    "LMG_Pecheneg": "wp_6p41",
    "LMG_T95": "wp_type95",
    "LMG_HK121": "wp_mg121",
    "LEG_LMG_KRYTAC_LLAMATIVO": "wp_llamativo",
    "STG_SuperShorty": "wp_supershorty",
    "STG_SuperShorty_Legacy": "wp_supershorty",
    "STG_SAIGA12": "wp_sasg12",
    "STG_SAIGA12_LEG_SILENCIO": "wp_sasg12",
    "STG_SPAS-12": "wp_spas12",
    "STG_M1014": "wp_m1014",
    "LEG_STG_SPAS-12_OBSEQUIO": "wp_elobsequio",
    "HDG_P45T": "wp_p45t",
    "HDG_P12": "wp_p12",
    "HDG_M9": "wp_m9",
    "HDG_Five-Seven": "wp_57usg",
    "HDG_M1911": "wp_m1911",
    "HDG_DEAGLE": "wp_d50",
    "HDG_P227": "wp_p227",
    "LEG_HDG_57_LADYKILLER": "wp_ladykiller",
    "CMG_SKORPION": "wp_skorpion",
}

_CLS_ALIASES = {
    "ar": ("ASR", "CAR", "AR"),
    "smg": ("SMG", "CMG"),
    "lmg": ("LMG",),
    "sniper": ("SNP", "SNR"),
    "shotgun": ("STG", "SHG"),
    "pistol": ("HDG", "HND"),
}


def match_gbs_weapon_ids(unlocked_names: set[str]) -> set[str]:
    """Mapeia nomes internos GBS Table 2 de armas para IDs de `WEAPONS_DB` sem falso-positivo em acessórios."""
    valid_ids = {w["id"] for w in WEAPONS_DB}
    found: set[str] = set()
    norm_exact = {k.strip().upper(): v for k, v in _GBS_WEAPON_EXACT_MAP.items()}
    for raw_name in unlocked_names:
        name = raw_name.strip()
        if not name.startswith(_WEAPON_GBS_PREFIXES):
            continue
        if "_PVP_" in name.upper():
            continue
        wid = norm_exact.get(name.upper())
        if wid and wid in valid_ids:
            found.add(wid)
    return found


def match_gbs_attachment_ids(unlocked_names: set[str]) -> set[str]:
    """Mapeia nomes internos GBS Table 2 de acessórios para IDs de `ATTACHMENTS_DB`."""
    att_tokens = [nm.strip() for nm in unlocked_names if not nm.strip().startswith(_WEAPON_GBS_PREFIXES)]
    if not att_tokens:
        return set()

    upper_tokens = [t.upper() for t in att_tokens]
    found: set[str] = set()

    def _has_cls(tok: str, classes: list[str]) -> bool:
        if "_BASE" in tok:
            return True
        for c in classes:
            for al in _CLS_ALIASES.get(c, ()):
                if f"_{al}_" in tok or tok.endswith(f"_{al}"):
                    return True
        return False

    for a in ATTACHMENTS_DB:
        aid = a["id"]
        slot = a["slot"]
        classes = a.get("compatible_classes") or []
        matched = False

        if aid == "att_panoramic":
            matched = any(t.startswith("AC11704_") for t in upper_tokens)
        elif aid == "att_pkas":
            matched = any(t.startswith("PKAS_") for t in upper_tokens)
        elif aid == "att_compm4":
            matched = any(t.startswith("COMPM4_") for t in upper_tokens)
        elif aid == "att_ar_micro_t1":
            matched = any(t.startswith("MICROT1_") and not t.startswith("MICROT1XG33") for t in upper_tokens)
        elif aid == "att_micro_g33":
            matched = any(t.startswith("MICROT1XG33") or "MICROT1_WITHMAGNIFIER" in t for t in upper_tokens)
        elif aid == "att_exps3":
            matched = any(t.startswith("EXPS3_") and not t.startswith("EXPS3XG33") for t in upper_tokens)
        elif aid == "att_exps_g33":
            matched = any(t.startswith("EXPS3XG33") for t in upper_tokens)
        elif aid == "att_pks07":
            matched = any(t.startswith("PKS07_") for t in upper_tokens)
        elif aid == "att_ta31h":
            matched = any(t.startswith("TA31H_") for t in upper_tokens)
        elif aid == "att_tars101":
            matched = any(t.startswith("TARS101_") for t in upper_tokens)
        elif aid == "att_t5xi":
            matched = any(t.startswith("T5XI_") for t in upper_tokens)
        elif aid == "att_posp":
            matched = any(t.startswith("POSP_") for t in upper_tokens)
        elif aid == "att_g28_scope":
            matched = any(t.startswith("G28_") for t in upper_tokens)
        elif aid == "att_digital_scope":
            matched = any("SPECTER_" in t for t in upper_tokens)
        elif aid == "att_ar_long_barrel":
            matched = any(t.startswith("BARRELATTACHMENT_LONGBARREL_ASR_") for t in upper_tokens)
        elif aid == "att_ar_short_barrel":
            matched = any(t.startswith("BARRELATTACHMENT_SHORTBARREL_ASR_") for t in upper_tokens)
        elif aid == "att_smg_short":
            matched = any(t.startswith("BARRELATTACHMENT_SHORTBARREL_SMG_") for t in upper_tokens)
        elif aid == "att_sg_long_barrel":
            matched = any(t.startswith("BARRELATTACHMENT_LONGBARREL_STG_") for t in upper_tokens)
        elif aid == "att_lmg_long":
            matched = any(t.startswith("BARRELATTACHMENT_LONGBARREL_LMG_") for t in upper_tokens)
        elif aid == "att_sr_long_barrel":
            matched = any(t.startswith(("BARRELATTACHMENT_LONGBARREL_SNP_", "BARRELATTACHMENT_LONGBARREL_SNR_")) for t in upper_tokens)
        elif aid in ("att_ar_atpial", "att_smg_atpial", "att_lmg_atpial", "att_sr_atpial", "att_hg_atpial"):
            matched = any(t.startswith("RAILATTACHMENT_ATPIAL") and _has_cls(t, classes) for t in upper_tokens)
        elif aid in ("att_ar_3dot", "att_smg_3dot", "att_lmg_3dot", "att_sr_3dot", "att_hg_3dot"):
            matched = any(
                (t.startswith(("RAILATTACHMENT_PISTOLLASER", "UNDERBARRELATTACHMENT_PISTOLLASER")) or "3DOT" in t)
                and _has_cls(t, classes)
                for t in upper_tokens
            )
        elif aid in ("att_ar_rangefinder", "att_smg_rangefinder", "att_sr_rangefinder"):
            matched = any(t.startswith("RAILATTACHMENT_RANGEFINDER") and _has_cls(t, classes) for t in upper_tokens)
        elif aid in ("att_ar_folded", "att_smg_folded", "att_lmg_folded"):
            matched = any(t.startswith("STOCK_FOLDED") and _has_cls(t, classes) for t in upper_tokens)
        elif aid in ("att_ar_comp_stock", "att_sr_comp_stock", "att_sr_comp_stock2"):
            matched = any(t.startswith("STOCK_ALT") and _has_cls(t, classes) for t in upper_tokens)
        elif aid == "att_fg_v2":
            matched = any("FOREGRIP_TYPE1_" in t for t in upper_tokens)
        elif aid in ("att_fg_v4", "att_vv_grip"):
            matched = any("FOREGRIP_TYPE2_" in t or "FOREGRIP_TYPE3_" in t or "FOREGRIP_V" in t for t in upper_tokens)
        elif aid in ("att_afg", "att_shift_grip"):
            matched = any("ANGLEDFOREGRIP" in t for t in upper_tokens)
        elif aid == "att_m203":
            matched = any("UBGL_SMALL" in t or "M203" in t for t in upper_tokens)
        elif aid == "att_std_gl":
            matched = any("UBGL" in t and "SMOKE" not in t and "SMALL" not in t for t in upper_tokens)
        elif aid == "att_ar_flash_hider":
            matched = any(t.startswith("MUZZLE HIDDER") and _has_cls(t, ["ar"]) for t in upper_tokens)
        elif aid in ("att_ar_comp_v2", "att_smg_comp", "att_lmg_comp", "att_lmg_comp_v2", "att_sr_comp", "att_sr_comp_v2", "att_sg_comp"):
            matched = any(t.startswith("COMPENSATOR") and _has_cls(t, classes) for t in upper_tokens)
        elif aid in ("att_ar_suppressor", "att_lmg_suppressor", "att_sr_suppressor", "att_sg_suppressor"):
            matched = any(
                (t.startswith(("WPN_AT_MUZZLE_SUPPRESSOR", "MUZZLE_SIL")) and _has_cls(t, classes))
                for t in upper_tokens
            )
        elif aid == "att_ar_stanag30":
            matched = any("MAGAZINE_ASR_XTD_STANAG" in t for t in upper_tokens)
        elif aid == "att_ar_ext30":
            matched = any("MAGAZINE_ASR_XTD" in t and "STANAG" not in t for t in upper_tokens)
        elif aid == "att_ar_762_30":
            matched = any("MAGAZINE_ASR_XTD_AK" in t or "MAGAZINE_ASR_XTD_762" in t for t in upper_tokens)
        elif aid == "att_ar_mag50":
            matched = any("MAGAZINE_ASR" in t and ("DRM" in t or "50" in t or "BIG" in t) for t in upper_tokens)
        elif aid == "att_hg_ext15":
            matched = any(t.startswith("MAGAZINE_HDG_XTD") and ("M9" in t or "BERETTA" in t or "15" in t) for t in upper_tokens)
        elif aid == "att_pistol_extmag":
            matched = any(t.startswith("MAGAZINE_HDG_XTD") and ("FNP" in t or "45" in t or "57" in t or "30" in t or "BASE" in t) for t in upper_tokens)
        elif aid == "att_smg_ext30":
            matched = any(t.startswith("MAGAZINE_SMG_XTD") for t in upper_tokens)
        elif aid in ("att_sr_ext10", "att_sr_ext30"):
            matched = any(t.startswith(("MAGAZINE_SNP_XTD", "MAGAZINE_SNR_XTD")) for t in upper_tokens)
        elif aid == "att_lmg_ext200":
            matched = any(t.startswith("MAGAZINE_LMG_XTD") for t in upper_tokens)
        elif aid == "att_sg_ext_tube":
            matched = any(t.startswith(("MAGAZINE_STG_XTD", "MAGAZINE_SHG_XTD")) for t in upper_tokens)
        else:
            matched = False

        if matched and slot:
            found.add(aid)
    return found

