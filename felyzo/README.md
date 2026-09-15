# FELYZO — page produit « Harnais Anti-Fugue pour Chat »

Page statique servie par GitHub Pages : **https://sodev16.github.io/felyzo/**

```
felyzo/
├── index.html          → la page (HTML seul, aucune dépendance de build)
├── README.md           → ce fichier
└── assets/
    ├── style.css       → styles
    ├── app.js          → galerie, variantes, accordéon, guide des tailles
    └── img/            → 20 images de remplacement à remplacer
```

## 1. Remplacer les images

Les 20 fichiers de `assets/img/` sont des **placeholders** générés (fond sage +
nom du fichier). Écrasez-les par vos vraies photos en gardant **exactement le
même nom** : rien à modifier dans le HTML.

| Fichier | Format | Contenu attendu |
|---|---|---|
| `hero-1.jpg` … `hero-4.jpg` | carré 1000×1000 | photos produit / chat portant le harnais |
| `lifestyle-montagne.jpg` | 900×700 | scène « explorer ensemble » |
| `detail-portrait.jpg` | 800×1000 (portrait) | gros plan du harnais porté |
| `usage-promenade / voyage / ville / quotidien.jpg` | 600×600 | 4 contextes d'usage |
| `communaute-1.jpg` … `communaute-6.jpg` | 400×400 | photos clients façon Instagram |
| `avis-1.jpg` … `avis-3.jpg` | 200×200 | avatars des avis |
| `cta-aventure.jpg` | 1000×640 | visuel du bloc final |

## 2. Contenu à valider avant mise en ligne

Ces éléments sont repris de la maquette ou des informations publiques du
fabricant : **à confirmer avant de vendre.**

- **Prix** `39,90 € / 59,90 € barré / -33 %` → valeurs de la maquette, à ajuster
  (dans `index.html`, bloc `.price`).
- **Couleurs** : Noir, Rouge, Turquoise. Ajoutez un `<button class="swatch">`
  par coloris supplémentaire (les couleurs sont dans l'attribut `style`).
- **Avis clients** (« 4,8/5, 1 250 avis », les 3 témoignages) : textes de
  démonstration. À remplacer par de vrais avis — un avis inventé est une
  pratique commerciale trompeuse.
- **Mentions légales, CGV, confidentialité** : liens du pied de page à créer.

### Caractéristiques du harnais (source : fabricant OutdoorBengal, modèle Houdini™)

- Encolure à **cordon bloquant** : se resserre si le chat recule → anti-fugue.
- Plastron en **mesh léger** qui répartit la pression, poitrail rembourré.
- Sangles et boucles de réglage sur le tour de poitrine.
- **Laisse de 127 cm** (50") incluse, mousqueton métal rotatif 360°.
- Tailles (tour de poitrine) : Chaton 18–28 cm · M 28–51 cm · L 51–69 cm ·
  XL au-delà (Maine Coon). Converties depuis les pouces du fabricant.

## 3. Points techniques

- Aucun framework : ouvrez `index.html` dans un navigateur, c'est tout.
- Polices Google Fonts (`Outfit`, `Caveat`) chargées par CDN ; hors ligne, la
  page bascule sur les polices système.
- Le bouton « Ajouter au panier », le compteur et le formulaire newsletter sont
  des **démonstrations front-end** : à brancher sur Shopify, Stripe ou un
  prestataire d'e-mailing.
- Icônes : sprite SVG en bas de `index.html` (`<symbol id="i-…">`).
