#!/usr/bin/env python3
"""Génération des visuels VAMOS STRAP via l'API Gemini (image-to-image).

Le script lit un CSV de prompts (séparateur `;`), résout pour chaque ligne la ou
les photos de référence à envoyer au modèle, appelle
`models/<modele>:generateContent` en mode image-to-image, puis enregistre
l'image produite dans `output/<categorie>/<id>.png`.

Aucune dépendance externe : uniquement la bibliothèque standard.

Exemples
--------
    export GEMINI_API_KEY="..."
    python3 generate_images.py --dry-run              # vérifie le mapping
    python3 generate_images.py                        # génère tout
    python3 generate_images.py --only P08,A01         # génère 2 visuels
    python3 generate_images.py --skip-existing        # reprend une série
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
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.1-flash-image"
DEFAULT_CSV = "prompts/vamos_strap_prompts_selection5.csv"
DEFAULT_REFERENCES_DIR = "references"
DEFAULT_OUTPUT_DIR = "output"

# Photo utilisée quand une ligne ne référence explicitement aucune photo.
FALLBACK_PHOTO = 1

# Ratios acceptés par l'API ; le CSV n'en utilise que trois.
SUPPORTED_ASPECT_RATIOS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
}

# Consignes ajoutées à chaque prompt : fidélité produit et absence d'habillage
# marketing hérité des captures d'écran de référence.
GLOBAL_GUIDELINES = """Les images jointes sont des photographies de référence de la coudière VAMOS STRAP, \
fournies comme modèle visuel du produit à représenter.

Contraintes impératives :
- Le produit doit être reproduit fidèlement d'après la ou les images de référence fournies : sangle noire, liseré gris réfléchissant sur les bords, boucle de serrage métallique, coussinet de compression, fermeture velcro, graduations blanches imprimées sur la sangle.
- Aucun logo, aucune marque tierce, aucun texte superposé, aucun filigrane, aucune interface de navigateur : ignore complètement les textes marketing et les éléments d'interface présents sur les images de référence, ne conserve que le produit.
- Rendu photographique réaliste, haute définition, anatomie humaine correcte (mains, doigts, bras).
- Peau, textiles et lumière naturels et crédibles, pas de rendu 3D ni d'illustration."""


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------

def slugify(value: str) -> str:
    """`Douleur / Problème` -> `douleur-probleme`."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or "divers"


def is_empty(value: str | None) -> bool:
    return value is None or value.strip() in ("", "-", "—")


def log(message: str) -> None:
    print(message, flush=True)


# --------------------------------------------------------------------------
# Lecture du CSV
# --------------------------------------------------------------------------

@dataclass
class Row:
    id: str
    categorie: str
    angle: str
    format: str
    avatar: str
    prompt: str
    reference_raw: str
    photos: list[int] = field(default_factory=list)


def read_rows(csv_path: Path) -> list[Row]:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        rows: list[Row] = []
        for raw in reader:
            row_id = (raw.get("id") or "").strip()
            if not row_id:
                continue  # ligne vide en fin de fichier
            rows.append(
                Row(
                    id=row_id,
                    categorie=(raw.get("categorie") or "").strip(),
                    angle=(raw.get("angle_marketing") or "").strip(),
                    format=(raw.get("format") or "").strip(),
                    avatar=(raw.get("avatar") or "").strip(),
                    prompt=(raw.get("prompt") or "").strip(),
                    reference_raw=(raw.get("image_reference_a_utiliser") or "").strip(),
                )
            )
    return rows


def resolve_photos(rows: list[Row]) -> None:
    """Renseigne `row.photos` à partir de la colonne de référence.

    Gère `Photo 1`, `Photo 1 + Photo 5`, `Photo 1 x2`, `idem P01` (renvoi vers
    une autre ligne) et les cellules vides.
    """
    by_id = {row.id: row for row in rows}

    def resolve(row: Row, seen: set[str]) -> list[int]:
        found = [int(n) for n in re.findall(r"photos?\s*(\d+)", row.reference_raw, re.I)]
        # dédoublonnage en conservant l'ordre (`Photo 1 x2` -> une seule image)
        photos = list(dict.fromkeys(n for n in found if 1 <= n <= 5))
        if photos:
            return photos

        match = re.search(r"idem\s+([A-Z]\d+)", row.reference_raw, re.I)
        if match:
            target = match.group(1).upper()
            if target in by_id and target not in seen:
                return resolve(by_id[target], seen | {row.id})
            log(f"  ! {row.id}: renvoi vers '{target}' introuvable, "
                f"utilisation de Photo {FALLBACK_PHOTO}")
        elif row.reference_raw:
            log(f"  ! {row.id}: référence '{row.reference_raw}' non reconnue, "
                f"utilisation de Photo {FALLBACK_PHOTO}")
        return [FALLBACK_PHOTO]

    for row in rows:
        row.photos = resolve(row, set())


# --------------------------------------------------------------------------
# Construction de la requête
# --------------------------------------------------------------------------

def build_prompt(row: Row) -> str:
    parts = [row.prompt, ""]
    context: list[str] = []
    if not is_empty(row.avatar):
        context.append(f"- Sujet / avatar : {row.avatar}.")
    if not is_empty(row.angle):
        context.append(f"- Angle marketing : {row.angle}.")
    if not is_empty(row.format):
        context.append(f"- Format de sortie : {row.format}.")
    if context:
        parts.append("Contexte de la création :")
        parts.extend(context)
        parts.append("")
    parts.append(GLOBAL_GUIDELINES)
    return "\n".join(parts)


def load_reference(references_dir: Path, number: int) -> tuple[str, str]:
    """Retourne (mime_type, données base64) pour `photo_<n>`."""
    matches = sorted(references_dir.glob(f"photo_{number}.*"))
    if not matches:
        raise FileNotFoundError(
            f"Photo de référence {number} introuvable dans {references_dir} "
            f"(attendu : photo_{number}.png)"
        )
    path = matches[0]
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return mime, base64.b64encode(path.read_bytes()).decode("ascii")


def build_payload(row: Row, references_dir: Path, response_modalities: list[str]) -> dict:
    parts: list[dict] = []
    for number in row.photos:
        mime, data = load_reference(references_dir, number)
        parts.append({"inline_data": {"mime_type": mime, "data": data}})
    parts.append({"text": build_prompt(row)})

    generation_config: dict = {"responseModalities": response_modalities}
    if row.format in SUPPORTED_ASPECT_RATIOS:
        generation_config["imageConfig"] = {"aspectRatio": row.format}
    elif not is_empty(row.format):
        log(f"  ! {row.id}: format '{row.format}' non supporté par l'API, ignoré")

    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": generation_config,
    }


# --------------------------------------------------------------------------
# Appel API
# --------------------------------------------------------------------------

class ApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


def call_api(model: str, api_key: str, payload: dict, timeout: int) -> dict:
    url = f"{API_ROOT}/models/{model}:generateContent"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            body = json.loads(body)["error"]["message"]
        except Exception:
            body = body[:500]
        raise ApiError(exc.code, body) from exc
    except urllib.error.URLError as exc:
        raise ApiError(0, f"erreur réseau : {exc.reason}") from exc


def call_api_with_retries(model: str, api_key: str, payload: dict, timeout: int,
                          max_retries: int) -> dict:
    delay = 4.0
    for attempt in range(1, max_retries + 1):
        try:
            return call_api(model, api_key, payload, timeout)
        except ApiError as exc:
            retryable = exc.status in (0, 408, 429, 500, 502, 503, 504)
            if not retryable or attempt == max_retries:
                raise
            log(f"  … tentative {attempt}/{max_retries} échouée ({exc}), "
                f"nouvel essai dans {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    raise AssertionError("unreachable")


def extract_images(response: dict) -> list[tuple[str, bytes]]:
    """Retourne la liste des (mime_type, octets) présents dans la réponse."""
    images: list[tuple[str, bytes]] = []
    for candidate in response.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                mime = blob.get("mimeType") or blob.get("mime_type") or "image/png"
                images.append((mime, base64.b64decode(blob["data"])))
    return images


def describe_refusal(response: dict) -> str:
    """Message d'erreur lisible quand la réponse ne contient aucune image."""
    candidates = response.get("candidates", [])
    if not candidates:
        feedback = response.get("promptFeedback", {})
        reason = feedback.get("blockReason")
        return f"prompt bloqué ({reason})" if reason else "aucun candidat renvoyé"
    candidate = candidates[0]
    reason = candidate.get("finishReason", "?")
    texts = [
        part["text"].strip()
        for part in candidate.get("content", {}).get("parts", [])
        if part.get("text")
    ]
    detail = " | ".join(texts)[:300]
    return f"aucune image (finishReason={reason})" + (f" : {detail}" if detail else "")


# --------------------------------------------------------------------------
# Boucle principale
# --------------------------------------------------------------------------

def resolve_api_key(cli_key: str | None, script_dir: Path) -> str:
    if cli_key:
        return cli_key
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(name)
        if value:
            return value
    env_file = script_dir / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                return value.strip().strip("'\"")
    sys.exit(
        "Clé API introuvable. Renseignez GEMINI_API_KEY dans l'environnement, "
        "dans un fichier .env à côté du script, ou via --api-key."
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Génère les visuels VAMOS STRAP avec Gemini (image-to-image).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--csv", type=Path, default=script_dir / DEFAULT_CSV,
                        help="Fichier CSV des prompts (séparateur ';').")
    parser.add_argument("--references", type=Path,
                        default=script_dir / DEFAULT_REFERENCES_DIR,
                        help="Dossier contenant photo_1.png … photo_5.png.")
    parser.add_argument("--output", type=Path, default=script_dir / DEFAULT_OUTPUT_DIR,
                        help="Dossier racine des images générées.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Modèle Gemini image.")
    parser.add_argument("--api-key", default=None,
                        help="Clé API (sinon GEMINI_API_KEY ou .env).")
    parser.add_argument("--only", default=None,
                        help="Liste d'ids à traiter, séparés par des virgules (ex. P08,A01).")
    parser.add_argument("--categorie", default=None,
                        help="Ne traite que les lignes d'une catégorie (comparaison sur le slug).")
    parser.add_argument("--limit", type=int, default=0,
                        help="Nombre maximum de lignes à traiter (0 = toutes).")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Ignore les lignes dont l'image existe déjà.")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Pause en secondes entre deux appels API.")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout par appel API, en secondes.")
    parser.add_argument("--max-retries", type=int, default=4,
                        help="Nombre de tentatives par ligne (429, 5xx, réseau).")
    parser.add_argument("--response-modalities", default="TEXT,IMAGE",
                        help="Modalités demandées, séparées par des virgules (IMAGE ou TEXT,IMAGE).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche le plan de génération sans appeler l'API.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    script_dir = Path(__file__).resolve().parent

    if not args.csv.is_file():
        sys.exit(f"CSV introuvable : {args.csv}")
    if not args.references.is_dir():
        sys.exit(f"Dossier de références introuvable : {args.references}")

    rows = read_rows(args.csv)
    resolve_photos(rows)

    if args.only:
        wanted = {value.strip().upper() for value in args.only.split(",") if value.strip()}
        rows = [row for row in rows if row.id.upper() in wanted]
        missing = wanted - {row.id.upper() for row in rows}
        if missing:
            log(f"! ids absents du CSV : {', '.join(sorted(missing))}")
    if args.categorie:
        wanted_cat = slugify(args.categorie)
        rows = [row for row in rows if slugify(row.categorie) == wanted_cat]

    planned: list[tuple[Row, Path]] = []
    for row in rows:
        destination = args.output / slugify(row.categorie) / f"{row.id}.png"
        # L'API peut renvoyer du JPEG comme du PNG : on cherche toutes extensions.
        existing = sorted(destination.parent.glob(f"{row.id}.*"))
        if args.skip_existing and existing:
            log(f"= {row.id}: déjà généré ({existing[0]}), ignoré")
            continue
        planned.append((row, destination))
        if args.limit and len(planned) >= args.limit:
            break

    if not planned:
        log("Rien à générer.")
        return 0

    log(f"{len(planned)} visuel(s) à générer avec le modèle '{args.model}'.\n")

    if args.dry_run:
        for row, destination in planned:
            refs = ", ".join(f"Photo {n}" for n in row.photos)
            log(f"- {row.id} [{row.categorie}] {row.format or '-'} <- {refs}")
            log(f"    -> {destination}")
        return 0

    api_key = resolve_api_key(args.api_key, script_dir)
    modalities = [m.strip().upper() for m in args.response_modalities.split(",") if m.strip()]

    results: list[dict[str, str]] = []
    failures = 0

    for index, (row, destination) in enumerate(planned, start=1):
        refs = ", ".join(f"Photo {n}" for n in row.photos)
        log(f"[{index}/{len(planned)}] {row.id} [{row.categorie}] "
            f"{row.format or '-'} <- {refs}")
        entry = {
            "id": row.id,
            "categorie": row.categorie,
            "format": row.format,
            "references": refs,
            "fichier": "",
            "statut": "",
            "erreur": "",
        }
        try:
            payload = build_payload(row, args.references, modalities)
            response = call_api_with_retries(
                args.model, api_key, payload, args.timeout, args.max_retries
            )
            images = extract_images(response)
            if not images:
                raise RuntimeError(describe_refusal(response))

            destination.parent.mkdir(parents=True, exist_ok=True)
            saved: list[Path] = []
            for position, (mime, data) in enumerate(images):
                extension = mimetypes.guess_extension(mime) or ".png"
                if extension == ".jpe":
                    extension = ".jpg"
                path = destination.with_suffix(extension)
                if position:  # plusieurs images pour une même ligne
                    path = path.with_name(f"{destination.stem}_{position + 1}{extension}")
                path.write_bytes(data)
                saved.append(path)

            entry["statut"] = "ok"
            entry["fichier"] = " | ".join(str(p.relative_to(args.output)) for p in saved)
            log(f"  ✓ {entry['fichier']}")
        except Exception as exc:  # noqa: BLE001 - on veut poursuivre la série
            failures += 1
            entry["statut"] = "erreur"
            entry["erreur"] = str(exc)
            log(f"  ✗ {exc}")

        results.append(entry)
        if index < len(planned) and args.delay > 0:
            time.sleep(args.delay)

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = args.output / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "categorie", "format", "references", "fichier", "statut", "erreur"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(results)

    log(f"\nTerminé : {len(results) - failures} réussite(s), {failures} échec(s).")
    log(f"Récapitulatif : {manifest}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
