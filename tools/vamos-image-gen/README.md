# Génération d'images VAMOS STRAP (Gemini image-to-image)

Génère les visuels publicitaires décrits dans `prompts.csv` en appelant
`gemini-3.1-flash-image` en **image-to-image** : chaque ligne du CSV est envoyée
au modèle avec la ou les photos de référence qu'elle indique, et l'image obtenue
est enregistrée dans `output/<categorie>/<id>.jpg`.

## 1. Installation

```bash
cd tools/vamos-image-gen
pip install -r requirements.txt
export GEMINI_API_KEY="votre_cle_api"      # jamais dans le code ni dans git
```

## 2. Photos de référence

Placez les 5 photos dans `references/`, nommées `photo_1` à `photo_5`
(`.png` ou `.jpg`). C'est ce numéro que la colonne `image_reference_a_utiliser`
du CSV désigne :

| Fichier | Contenu |
| --- | --- |
| `photo_1` | Coudière portée, sangle relevée : velcro + graduations chiffrées 5-10 visibles (référence produit principale, utilisée par 17 lignes sur 21) |
| `photo_2` | Coudière portée sur avant-bras, vue rapprochée avec zone de douleur en surbrillance |
| `photo_3` | Deux joueurs de tennis équipés de la coudière |
| `photo_4` | Packshot studio sur bras, fond beige |
| `photo_5` | Joueur de padel sur terrain, vue plongeante, raquette en main |

Les photos 1 à 3 sont des captures d'écran de fiche produit Amazon. Recadrez-les
avant usage pour retirer l'interface du navigateur et les textes incrustés,
sinon le modèle risque de les reproduire :

```bash
python prepare_references.py          # recadre photo_1, photo_2, photo_3
```

Les originaux sont conservés dans `references/originaux/`. Les cadrages par
défaut sont réglés pour des captures Android 1080x2400 ; ajustez-les avec
`--box GAUCHE HAUT DROITE BAS` (fractions de la taille de l'image) si vos
captures ont un autre format.

## 3. Génération

```bash
python generate_images.py                 # les 21 lignes du CSV
python generate_images.py --dry-run       # vérifie CSV + références, sans appel API
python generate_images.py --only P02 A01  # quelques lignes seulement
python generate_images.py --overwrite     # regénère par-dessus l'existant
```

Options utiles : `--model`, `--csv`, `--references-dir`, `--output-dir`,
`--delay` (pause entre appels, 2 s par défaut), `--retries`, `--timeout`,
`--fallback-reference`.

Par défaut, une ligne dont l'image existe déjà est **ignorée** : on peut donc
relancer la commande après un échec partiel sans tout repayer.

### Résultat

```
output/
├── produit/            P02.jpg P06.jpg P08.jpg P09.jpg P13.jpg P14.jpg
├── douleur-probleme/   D01.jpg D05.jpg
├── probleme-solution/  S01.jpg S04.jpg S06.jpg
├── padel-action/       A01.jpg A06.jpg A09.jpg A11.jpg
├── ugc/                U02.jpg U05.jpg U08.jpg U10.jpg U11.jpg U12.jpg
└── rapport.csv         (id, catégorie, références utilisées, statut)
```

Le nom de dossier est la catégorie « slugifiée » (`Problème → Solution`
devient `probleme-solution`), le nom de fichier est l'`id` de la ligne.

## 4. Format du CSV

Séparateur `;`, encodage UTF-8, colonnes :
`id`, `categorie`, `angle_marketing`, `format`, `avatar`, `prompt`,
`image_reference_a_utiliser`.

- `format` est transmis à l'API comme ratio d'image (`1:1`, `4:5`, `9:16`, …) ;
  une valeur vide ou `-` laisse le modèle décider.
- `avatar` et `angle_marketing` sont ajoutés au prompt quand ils sont renseignés.
- `image_reference_a_utiliser` accepte les écritures du fichier d'origine :
  - `Photo 1`, `Photo 5`
  - `Photo 1 (commentaire libre)` — le commentaire est ignoré
  - `Photo 1 + Photo 5` — les deux images sont envoyées
  - `Photo 1 x2` — la même image envoyée deux fois (pack duo)
  - `idem P01` — reprend la référence de la ligne `P01` ; si cet id est absent
    du CSV, on retombe sur `--fallback-reference` (photo 1 par défaut)

## 5. Réglage de la fidélité produit

La constante `PRODUCT_GUARDRAIL` en haut de `generate_images.py` est ajoutée à
chaque prompt : c'est elle qui impose au modèle de ne pas réinventer la
coudière (couleurs, boucles, graduations imprimées). C'est le premier endroit à
modifier si un détail du produit dérive dans les rendus.

## Notes

- La clé API est lue depuis `GEMINI_API_KEY` (ou `--api-key`). Ne la committez
  pas : une clé publiée sur GitHub doit être révoquée dans Google AI Studio.
- `references/` et `output/` sont exclus de git (voir `.gitignore`) : ce dépôt
  est publié sur GitHub Pages, tout fichier committé y serait accessible
  publiquement.
- Coût : un appel par ligne, 21 lignes pour ce CSV. Les lignes en échec sont
  listées en fin d'exécution et dans `output/rapport.csv`.
