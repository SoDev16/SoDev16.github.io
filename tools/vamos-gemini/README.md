# VAMOS STRAP — génération de visuels avec Gemini (image-to-image)

Script Python qui lit un CSV de prompts, envoie à l'API Gemini la ou les photos de
référence indiquées sur chaque ligne, et enregistre l'image générée dans un dossier
nommé d'après la catégorie, avec l'id de la ligne comme nom de fichier.

Aucune dépendance externe : uniquement la bibliothèque standard de Python 3.10+.

## Installation

```bash
cd tools/vamos-gemini
export GEMINI_API_KEY="votre_clé"        # ou créez un fichier .env (voir plus bas)
```

La clé est lue dans cet ordre : `--api-key`, puis `GEMINI_API_KEY` /
`GOOGLE_API_KEY` dans l'environnement, puis un fichier `.env` placé à côté du
script. **Le `.env` n'est pas versionné** (voir `.gitignore`).

```
# tools/vamos-gemini/.env
GEMINI_API_KEY=votre_clé
```

## Utilisation

```bash
python3 generate_images.py --dry-run          # affiche le plan sans appeler l'API
python3 generate_images.py                    # génère les 21 visuels
python3 generate_images.py --only P08,A01     # génère seulement ces deux ids
python3 generate_images.py --categorie UGC    # génère une seule catégorie
python3 generate_images.py --skip-existing    # reprend une série interrompue
```

Principales options :

| Option | Rôle |
| --- | --- |
| `--csv` | Fichier de prompts (défaut : `prompts/vamos_strap_prompts_selection5.csv`) |
| `--references` | Dossier des photos de référence (défaut : `references/`) |
| `--output` | Dossier racine de sortie (défaut : `output/`) |
| `--model` | Modèle image (défaut : `gemini-3.1-flash-image`) |
| `--only` / `--categorie` / `--limit` | Filtres de sélection des lignes |
| `--skip-existing` | Ignore les lignes déjà générées |
| `--delay` | Pause entre deux appels (défaut : 2 s) |
| `--max-retries` | Nouvelles tentatives sur 429 / 5xx / erreur réseau (backoff exponentiel) |
| `--dry-run` | Vérifie le mapping CSV → photos sans consommer de quota |

## Format du CSV

Séparateur `;`, encodage UTF-8, colonnes :

`id` · `categorie` · `angle_marketing` · `format` · `avatar` · `prompt` · `image_reference_a_utiliser`

- **`format`** est transmis à l'API comme ratio d'image (`1:1`, `4:5`, `9:16`…).
  Un format non supporté est signalé et ignoré.
- **`image_reference_a_utiliser`** est analysé de façon tolérante :
  - `Photo 1` → envoie `references/photo_1.png`
  - `Photo 1 + Photo 5` → envoie les deux images
  - `Photo 1 x2` → une seule image (le doublon est inutile, le prompt décrit déjà le pack duo)
  - `idem P01` → reprend la référence de la ligne `P01`, ou la photo 1 si cet id est absent du CSV
  - cellule vide ou libellé non reconnu → photo 1, avec un avertissement
- **`avatar`**, **`angle_marketing`** et **`format`** sont ajoutés au prompt comme
  contexte quand ils ne valent pas `-`.

Chaque prompt est complété par un bloc de contraintes communes (fidélité produit :
sangle noire, liseré gris, boucle, coussinet, velcro, graduations ; interdiction
de tout texte, logo ou filigrane superposé ; rendu photographique réaliste).

## Photos de référence

`references/photo_1.png` … `photo_5.png` :

| Fichier | Contenu | Utilisé pour |
| --- | --- | --- |
| `photo_1.png` | Coudière sur le bras, sangle relevée, graduations 5–10 et velcro visibles | Fidélité produit, position sur le bras, chiffres, velcro |
| `photo_2.png` | Coude de profil, coussinet de compression sous l'articulation | Positionnement du coussinet |
| `photo_3.png` | Double visuel joueur de tennis équipé | Contexte sportif |
| `photo_4.png` | Gros plan sur un terrain de padel, ajustement de la sangle | Contexte padel réaliste |
| `photo_5.png` | Joueur de padel en plein smash | Silhouette, morphologie, ambiance terrain |

> **Important :** les références doivent être des photos **du produit seul**, pas des
> captures d'écran. Les photos 1 à 3 sont des recadrages des captures d'écran d'origine
> (conservées dans `references/raw/`) : envoyées en pleine capture, avec la barre d'état
> du téléphone et l'interface du navigateur, le modèle refuse de générer et répond
> « le lien fourni est une capture d'écran d'un site de vente en ligne ».
> Le recadrage appliqué est `(106, 912, 982, 1790)` sur les captures 1080 × 2400.

## Sortie

```
output/
├── produit/            P02.jpg P06.jpg P08.jpg P09.jpg P13.jpg P14.jpg
├── douleur-probleme/   D01.jpg D05.jpg
├── probleme-solution/  S01.jpg S04.jpg S06.jpg
├── padel-action/       A01.jpg A06.jpg A09.jpg A11.jpg
├── ugc/                U02.jpg U05.jpg U08.jpg U10.jpg U11.jpg U12.jpg
└── manifest.csv        récapitulatif : id, catégorie, format, références, fichier, statut, erreur
```

L'extension suit le type MIME renvoyé par l'API (`.jpg` en pratique avec
`gemini-3.1-flash-image`). Si l'API renvoie plusieurs images pour une même ligne,
les suivantes sont suffixées `_2`, `_3`, etc.

`output/` n'est pas versionné.

## Comportement en cas d'erreur

Une ligne en échec n'interrompt pas la série : l'erreur est affichée, consignée dans
`manifest.csv`, et le script continue. Le code de sortie vaut `1` si au moins une
ligne a échoué.

Les erreurs `429`, `5xx` et réseau sont réessayées automatiquement (4 tentatives,
backoff 4 s → 8 s → 16 s). Quand le modèle refuse de produire une image, le texte de
sa réponse est repris dans le message d'erreur, ce qui permet de comprendre le refus.
