from datetime import date

SEGUNDOS_24_HORAS = 60 * 60 * 24

WORLD_CUP_START_DATE = date(2026, 6, 4)
WORLD_CUP_END_DATE = date(2026, 7, 20)

WORLD_CUP_PERIOD_CHOICES = [
    ("geral", "Geral"),
    ("rodada_1", "1ª Rodada (Fase de Grupos)"),
    ("rodada_2", "2ª Rodada (Fase de Grupos)"),
    ("rodada_3", "3ª Rodada (Fase de Grupos)"),
    ("rodada_32", "Rodada de 32 (Segunda Fase)"),
    ("oitavas", "Oitavas de final"),
    ("quartas", "Quartas de final"),
    ("semifinais", "Semifinais"),
    ("terceiro", "Disputa do 3º Lugar"),
    ("final", "Final"),
]

WORLD_CUP_PERIOD_DATE_RANGES = {
    "geral": (date(2026, 6, 10), date(2026, 7, 20)),
    "rodada_1": (date(2026, 6, 10), date(2026, 6, 17)),
    "rodada_2": (date(2026, 6, 18), date(2026, 6, 23)),
    "rodada_3": (date(2026, 6, 24), date(2026, 6, 27)),
    "rodada_32": (date(2026, 6, 28), date(2026, 7, 3)),
    "oitavas": (date(2026, 7, 4), date(2026, 7, 7)),
    "quartas": (date(2026, 7, 9), date(2026, 7, 11)),
    "semifinais": (date(2026, 7, 14), date(2026, 7, 15)),
    "terceiro": (date(2026, 7, 18), date(2026, 7, 18)),
    "final": (date(2026, 7, 19), date(2026, 7, 19)),
}
