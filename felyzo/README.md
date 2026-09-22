# FELYZO — fiche produit

Page statique construite d'après `docs/FELYZO_structure_fiche_produit.pdf`
(version mobile, thème Shopify Shrine Pro). Servie par GitHub Pages sur
**https://sodev16.github.io/felyzo/**

```
felyzo/
├── index.html              → les 15 sections, dans l'ordre mobile du document
├── docs/                   → le document de structure de référence
└── assets/
    ├── style.css           → DA beige chaud / vert forêt / blanc cassé, mobile-first
    ├── app.js              → galerie, variantes, offres, barre collante, FAQ, tailles
    └── img/                → 28 visuels de remplacement à remplacer
```

## Les 15 sections

| # | Section | État |
|---|---|---|
| 1 | Hero — promesse | ✅ |
| 2 | Fiche produit — galerie, options, offres, CTA, réassurance | ✅ |
| 3 | Bandeau 4 bénéfices | ✅ |
| 4 | Le problème | ✅ |
| 5 | La solution — packshot annoté 01/02/03 | ✅ |
| 6 | Démonstration vidéo | emplacement à brancher |
| 7 | Les bénéfices | ✅ |
| 8 | Avant / après | ✅ |
| 9 | Preuve sociale | **gabarits vides — avis à fournir** |
| 10 | Pour quels chats ? | ✅ |
| 11 | Comment l'utiliser — 3 étapes | ✅ |
| 12 | Rappel de l'offre + CTA | ✅ |
| 13 | Réassurance | **conditions à définir** |
| 14 | FAQ — 6 questions | ✅ |
| 15 | Dernier CTA + footer | ✅ |

Un ajout hors document : une **barre d'achat collante** apparaît dès que le
visiteur dépasse le sélecteur d'offre et disparaît sur le dernier CTA. Sur une
page de cette longueur, c'est le principal levier de conversion sur mobile.

## À faire avant publication

**1. Remplacer les 28 visuels.** Même nom de fichier, rien à changer dans le
HTML. Les noms disent ce qu'ils attendent : `galerie-3-poitrail.jpg`,
`etape-2-ajustez.jpg`, `chat-voyage.jpg`… Le document impose **le même modèle de
harnais sur tous les visuels**.

**2. Les avis (section 9).** Les trois blocs sont des gabarits vides. Le bloc de
note ★ 4,8/5 en haut de fiche est volontairement **commenté** dans `index.html` :
décommentez-le une fois la note et le nombre d'avis réels. Le document est
explicite sur ce point : ne rien inventer.

**3. La réassurance (sections 2, 12 et 13).** « Retours sous X jours » est un
marqueur à remplacer. N'affichez un délai de livraison, une durée de retour ou
une garantie qu'une fois ces conditions définies et tenables.

**4. Le guide des tailles.** S 20–28 / M 28–36 / L 36–44 / XL 44–52 cm reprend le
prototype. Ces mesures sont **à confirmer auprès du fournisseur** : elles ne
correspondent pas à celles du harnais Houdini d'OutdoorBengal pris en référence
(3 tailles, de 18 à 69 cm).

**5. Le prix.** La page suit le document : 34,90 € pour un harnais, 49,90 € pour
le pack aventure. La fiche Shopify est actuellement à 39,99 € avec une seule
variante « Default Title ». À aligner. Le contenu du pack (« harnais + laisse +
accessoire ») reste à préciser : l'accessoire n'est pas défini.

**6. La vidéo (section 6).** Le bouton de lecture est un emplacement. Prévoir une
vidéo verticale 9:16 style UGC : installation → ajustement → sortie → marche →
exploration.

## Points techniques

- Aucun framework ni build : ouvrez `index.html` dans un navigateur.
- Polices Google Fonts (`Fraunces` pour les titres, `Inter` pour le corps) ;
  hors ligne, la page bascule sur les polices système.
- Panier, compteur et newsletter sont des **démonstrations front-end**, à
  brancher sur Shopify.
- Icônes : sprite SVG en bas de `index.html` (`<symbol id="i-…">`).
