#!/usr/bin/env python3
"""Génération d'images VAMOS STRAP en image-to-image avec l'API Gemini.

Lit un CSV de prompts (séparateur `;`), et pour chaque ligne :
  - résout la ou les photos de référence indiquées dans la colonne
    `image_reference_a_utiliser` (« Photo 1 », « Photo 1 + Photo 5 », « Photo 1 x2 »,
    « idem P01 », …) ;
  - appelle Gemini en image-to-image avec ces photos + le prompt ;
  - enregistre l'image générée dans `output/<categorie>/<id>.png`.

Usage :
    export GEMINI_API_KEY="votre_cle"
    python generate_images.py                     # tout le CSV
    python generate_images.py --dry-run           # vérifie sans appeler l'API
    python generate_images.py --only P02 A01      # seulement certaines lignes
    python generate_images.py --overwrite         # regénère les images existantes
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import mimetypes
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import requests

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.1-flash-image"

# Ratios acceptés par l'API pour imageConfig.aspectRatio.
SUPPORTED_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}

# Consigne produit ajoutée à chaque prompt : c'est elle qui force la fidélité
# au produit des photos de référence. À adapter librement.
PRODUCT_GUARDRAIL = (
    "Contrainte produit impérative : la coudière visible doit être exactement celle "
    "des images de référence fournies (sangle noire, liseré gris clair, boucles "
    "plates noires, bande velcro, graduations chiffrées imprimées en blanc). "
    "Ne modifie ni sa forme, ni ses couleurs, ni ses inscriptions, ni ses proportions. "
    "N'ajoute aucun texte, logo, filigrane ni interface d'application dans l'image. "
    "Rendu photoréaliste, sans artefact ni déformation anatomique."
)

PROMPT_TEMPLATE = """{prompt}

{extra}Format de sortie : {fmt}.

{guardrail}"""


def slugify(value: str) -> str:
    """« Problème → Solution » -> « probleme-solution » (nom de dossier sûr)."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "sans-categorie"


@dataclass
class Row:
    id: str
    categorie: str
    angle_marketing: str
    format: str
    avatar: str
    prompt: str
    reference_raw: str
    references: list[int] = field(default_factory=list)

    @property
    def output_path_parts(self) -> tuple[str, str]:
        return slugify(self.categorie), self.id


def clean(value: str | None) -> str:
    value = (value or "").strip()
    return "" if value in {"-", "—", ""} else value


def parse_references(raw: str, by_id: dict[str, str], seen: set[str] | None = None) -> list[int]:
    """Extrait les numéros de photos d'une cellule `image_reference_a_utiliser`.

    Gère « Photo 1 », « Photo 1 + Photo 5 », « Photo 1 x2 », « Photo 1 (commentaire) »
    et « idem P01 » (renvoi vers la référence d'une autre ligne).
    """
    raw = (raw or "").strip()
    if not raw:
        return []

    seen = seen or set()
    idem = re.search(r"idem\s+([A-Za-z]\d+)", raw, re.IGNORECASE)
    if idem:
        target = idem.group(1).upper()
        if target in by_id and target not in seen:
            return parse_references(by_id[target], by_id, seen | {target})
        return []  # ligne référencée absente du CSV -> repli géré par l'appelant

    refs: list[int] = []
    # « Photo 1 x2 » = la même photo utilisée deux fois (pack duo).
    for number, repeat in re.findall(r"photos?\s*(\d+)\s*(?:x\s*(\d+))?", raw, re.IGNORECASE):
        refs.extend([int(number)] * max(1, int(repeat or 1)))
    return refs


def load_rows(csv_path: Path) -> list[Row]:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        raw_rows = [r for r in csv.DictReader(handle, delimiter=";") if clean(r.get("id"))]

    by_id = {r["id"].strip().upper(): (r.get("image_reference_a_utiliser") or "") for r in raw_rows}

    rows: list[Row] = []
    for raw in raw_rows:
        row = Row(
            id=raw["id"].strip(),
            categorie=clean(raw.get("categorie")) or "sans-categorie",
            angle_marketing=clean(raw.get("angle_marketing")),
            format=clean(raw.get("format")),
            avatar=clean(raw.get("avatar")),
            prompt=clean(raw.get("prompt")),
            reference_raw=clean(raw.get("image_reference_a_utiliser")),
        )
        row.references = parse_references(row.reference_raw, by_id)
        rows.append(row)
    return rows


def resolve_reference_files(refs: list[int], references_dir: Path, fallback: int) -> list[Path]:
    """Numéros de photos -> chemins de fichiers (photo_1.png, photo_1.jpg, …)."""
    if not refs:
        refs = [fallback]

    paths: list[Path] = []
    for number in refs:
        matches = sorted(references_dir.glob(f"photo_{number}.*"))
        if not matches:
            raise FileNotFoundError(
                f"photo de référence {number} introuvable dans {references_dir} "
                f"(attendu : photo_{number}.png ou photo_{number}.jpg)"
            )
        paths.append(matches[0])
    return paths


def build_prompt(row: Row) -> str:
    details = []
    if row.avatar:
        details.append(f"Sujet / avatar : {row.avatar}.")
    if row.angle_marketing:
        details.append(f"Angle marketing : {row.angle_marketing}.")
    extra = (" ".join(details) + "\n\n") if details else ""
    return PROMPT_TEMPLATE.format(
        prompt=row.prompt,
        extra=extra,
        fmt=row.format or "1:1",
        guardrail=PRODUCT_GUARDRAIL,
    )


def build_payload(row: Row, image_paths: list[Path]) -> dict:
    parts: list[dict] = [{"text": build_prompt(row)}]
    for path in image_paths:
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                }
            }
        )

    generation_config: dict = {"responseModalities": ["IMAGE"]}
    if row.format in SUPPORTED_ASPECT_RATIOS:
        generation_config["imageConfig"] = {"aspectRatio": row.format}

    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": generation_config,
    }


class GeminiError(RuntimeError):
    pass


def extract_image(response: dict) -> tuple[bytes, str]:
    """Récupère la première image inline de la réponse."""
    for candidate in response.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                return base64.b64decode(inline["data"]), mime

    # Pas d'image : on remonte la raison (filtre de sécurité, quota, etc.).
    reasons = [c.get("finishReason") for c in response.get("candidates", []) if c.get("finishReason")]
    blocked = (response.get("promptFeedback") or {}).get("blockReason")
    detail = ", ".join(filter(None, [*reasons, blocked])) or "réponse sans image"
    raise GeminiError(f"aucune image renvoyée ({detail})")


def call_gemini(payload: dict, api_key: str, model: str, retries: int, timeout: int) -> tuple[bytes, str]:
    url = f"{API_ROOT}/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code == 404:
                raise GeminiError(
                    f"modèle « {model} » introuvable pour cette clé API. "
                    "Vérifiez le nom (option --model) ou listez les modèles disponibles :\n"
                    f"  curl -H 'x-goog-api-key: $GEMINI_API_KEY' {API_ROOT}/models"
                )
            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {response.status_code}: {response.text[:300]}")
            if response.status_code != 200:
                raise GeminiError(f"HTTP {response.status_code}: {response.text[:500]}")
            return extract_image(response.json())
        except GeminiError:
            raise
        except (requests.RequestException, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == retries:
                break
            delay = 2 ** (attempt + 1)  # 2s, 4s, 8s, 16s
            print(f"    ! {exc} — nouvelle tentative dans {delay}s", file=sys.stderr)
            time.sleep(delay)

    raise GeminiError(f"échec après {retries + 1} tentatives : {last_error}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", type=Path, default=here / "prompts.csv", help="CSV des prompts (séparateur ;)")
    parser.add_argument("--references-dir", type=Path, default=here / "references", help="dossier des photos de référence")
    parser.add_argument("--output-dir", type=Path, default=here / "output", help="dossier de sortie")
    parser.add_argument("--model", default=os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY"), help="par défaut : $GEMINI_API_KEY")
    parser.add_argument("--only", nargs="+", metavar="ID", help="ne traiter que ces ids (ex : P02 A01)")
    parser.add_argument("--overwrite", action="store_true", help="regénérer même si le fichier existe déjà")
    parser.add_argument("--dry-run", action="store_true", help="tout vérifier sans appeler l'API")
    parser.add_argument("--fallback-reference", type=int, default=1, help="photo utilisée si la ligne n'en indique aucune")
    parser.add_argument("--delay", type=float, default=2.0, help="pause entre deux appels, en secondes")
    parser.add_argument("--retries", type=int, default=4, help="nombre de nouvelles tentatives en cas d'erreur réseau/quota")
    parser.add_argument("--timeout", type=int, default=180, help="timeout HTTP par appel, en secondes")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.dry_run and not args.api_key:
        print("Erreur : clé API manquante. Faites `export GEMINI_API_KEY=...` ou passez --api-key.", file=sys.stderr)
        return 2
    if not args.csv.exists():
        print(f"Erreur : CSV introuvable : {args.csv}", file=sys.stderr)
        return 2

    rows = load_rows(args.csv)
    if args.only:
        wanted = {i.upper() for i in args.only}
        rows = [r for r in rows if r.id.upper() in wanted]
        missing = wanted - {r.id.upper() for r in rows}
        if missing:
            print(f"Attention : ids absents du CSV : {', '.join(sorted(missing))}", file=sys.stderr)

    print(f"{len(rows)} ligne(s) à traiter — modèle : {args.model}")
    if args.dry_run:
        print("Mode --dry-run : aucun appel à l'API.\n")

    ok, skipped, failed = 0, 0, []
    report: list[dict] = []

    for index, row in enumerate(rows, start=1):
        folder, name = row.output_path_parts
        destination_dir = args.output_dir / folder
        existing = sorted(destination_dir.glob(f"{name}.*"))
        print(f"[{index}/{len(rows)}] {row.id} → {folder}/{name}")

        if existing and not args.overwrite:
            print(f"    ↷ déjà généré ({existing[0].name}), ignoré (--overwrite pour refaire)")
            skipped += 1
            continue

        try:
            images = resolve_reference_files(row.references, args.references_dir, args.fallback_reference)
        except FileNotFoundError as exc:
            print(f"    ✗ {exc}", file=sys.stderr)
            failed.append((row.id, str(exc)))
            continue

        origin = row.references or [args.fallback_reference]
        print(f"    référence(s) : {', '.join(p.name for p in images)} (colonne CSV : « {row.reference_raw or '—'} »)")

        if args.dry_run:
            report.append({"id": row.id, "categorie": row.categorie, "references": origin, "statut": "dry-run"})
            ok += 1
            continue

        try:
            payload = build_payload(row, images)
            data, mime = call_gemini(payload, args.api_key, args.model, args.retries, args.timeout)
        except GeminiError as exc:
            print(f"    ✗ {exc}", file=sys.stderr)
            failed.append((row.id, str(exc)))
            report.append({"id": row.id, "categorie": row.categorie, "references": origin, "statut": f"erreur: {exc}"})
            continue

        extension = mimetypes.guess_extension(mime) or ".png"
        if extension == ".jpe":  # normalisation
            extension = ".jpg"
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{name}{extension}"
        destination.write_bytes(data)
        print(f"    ✓ {destination.relative_to(args.output_dir.parent)} ({len(data) // 1024} Ko)")
        ok += 1
        report.append({"id": row.id, "categorie": row.categorie, "references": origin, "statut": str(destination)})

        if args.delay and index < len(rows):
            time.sleep(args.delay)

    if report:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report_path = args.output_dir / "rapport.csv"
        with report_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "categorie", "references", "statut"], delimiter=";")
            writer.writeheader()
            for entry in report:
                writer.writerow({**entry, "references": " + ".join(f"Photo {n}" for n in entry["references"])})
        print(f"\nRapport : {report_path}")

    print(f"\nTerminé — {ok} générée(s), {skipped} ignorée(s), {len(failed)} en échec.")
    for identifier, message in failed:
        print(f"  ✗ {identifier} : {message}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
