#!/usr/bin/env python3
"""Nettoie les photos de référence issues de captures d'écran.

Les photos 1 à 3 sont des captures d'écran de fiche Amazon : elles contiennent
la barre du navigateur, le titre du produit, etc. Envoyer ça tel quel au modèle
dégrade la génération (le modèle peut reproduire l'interface). Ce script recadre
la zone de l'image produit et remplace le fichier, l'original étant conservé
dans `references/originaux/`.

Usage :
    python prepare_references.py                 # recadre photo_1, photo_2, photo_3
    python prepare_references.py --photos 1 2     # seulement certaines
    python prepare_references.py --box 0.1 0.38 0.91 0.75   # recadrage manuel
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image

# Zone à conserver dans chaque capture (fractions de la largeur/hauteur) :
# gauche, haut, droite, bas. Les bornes hautes/basses excluent aussi les
# bandeaux de texte marketing incrustés sur les visuels Amazon.
DEFAULT_BOX = (0.098, 0.380, 0.911, 0.750)
PHOTO_BOXES = {
    1: (0.098, 0.380, 0.911, 0.685),  # texte incrusté en bas
    2: (0.098, 0.455, 0.911, 0.750),  # texte incrusté en haut
    3: (0.098, 0.445, 0.911, 0.650),  # bandeaux en haut et en bas
}


def crop(path: Path, box: tuple[float, float, float, float], backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / path.name
    if not backup.exists():
        shutil.copy2(path, backup)

    with Image.open(backup) as image:
        width, height = image.size
        left, top, right, bottom = box
        cropped = image.convert("RGB").crop(
            (int(left * width), int(top * height), int(right * width), int(bottom * height))
        )
        cropped.save(path)
        print(f"{path.name} : {width}x{height} → {cropped.width}x{cropped.height} (original : {backup})")


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--references-dir", type=Path, default=here / "references")
    parser.add_argument("--photos", nargs="+", type=int, default=[1, 2, 3], help="numéros de photos à recadrer")
    parser.add_argument(
        "--box",
        nargs=4,
        type=float,
        metavar=("GAUCHE", "HAUT", "DROITE", "BAS"),
        help="recadrage manuel appliqué à toutes les photos (défaut : réglage par photo)",
    )
    args = parser.parse_args()

    backup_dir = args.references_dir / "originaux"
    for number in args.photos:
        matches = sorted(p for p in args.references_dir.glob(f"photo_{number}.*") if p.is_file())
        if not matches:
            print(f"photo_{number} introuvable dans {args.references_dir}, ignorée")
            continue
        box = tuple(args.box) if args.box else PHOTO_BOXES.get(number, DEFAULT_BOX)
        crop(matches[0], box, backup_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
