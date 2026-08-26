"""Scraper OPZIONALE del listone (best-effort) — DA LANCIARE SULLA TUA MACCHINA.

Perche' opzionale/best-effort:
  - Da questo ambiente cloud il dominio fantacalcio.it e' BLOCCATO dalla policy
    di rete aziendale (egress proxy 403), quindi qui non si puo' scaricare nulla.
  - Il percorso affidabile e ToS-friendly e' scaricare a mano il file ufficiale
    "Quotazioni/Listone" (xlsx) e importarlo con `ingest.listone.load_listone`.

Questo modulo prova a scaricare l'export ufficiale dei prezzi. Gli URL sono
CONFIGURABILI perche' cambiano di stagione: verificali dal browser (tasto
"Scarica" nella pagina quotazioni) prima di affidartici.

Uso tipico (sul tuo PC):
    python -m camantra.ingest.scraper --url "<URL_EXPORT_XLSX>" --out data/listone.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
}


def download_file(url: str, out: str | Path, timeout: int = 30) -> Path:
    """Scarica `url` in `out`. Richiede `requests`. Solleva con messaggio chiaro
    se la rete blocca il dominio (tipico in ambienti con egress proxy)."""
    try:
        import requests
    except ImportError as e:  # pragma: no cover
        raise SystemExit("Installa 'requests': pip install requests") from e

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001 - vogliamo un messaggio umano
        raise SystemExit(
            f"Download fallito ({e}).\n"
            f"- Se sei in un ambiente con proxy/egress bloccato, questo dominio "
            f"potrebbe non essere raggiungibile: scarica il file a mano dal "
            f"browser e importalo dalla dashboard.\n"
            f"- Verifica anche che l'URL di export sia ancora valido."
        ) from e

    out.write_bytes(resp.content)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scarica il listone ufficiale (best-effort).")
    ap.add_argument("--url", required=True, help="URL export xlsx/csv del listone")
    ap.add_argument("--out", default="data/listone.xlsx", help="file di destinazione")
    args = ap.parse_args(argv)
    dest = download_file(args.url, args.out)
    print(f"OK: salvato {dest} ({dest.stat().st_size} byte)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
