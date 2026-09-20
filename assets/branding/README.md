# Raqmi branding

Part of one identity system shared across [Abdulelah Alkhathami's public
repositories](https://github.com/Abdulel3h). The canonical rules - palette,
material, motion, accessibility and the prohibited patterns - live in
[the brand system](https://github.com/Abdulel3h/Abdulel3h/blob/main/docs/github-brand-system.md).

## Source of truth

`tools/build_brand_assets.py` generates every file below. Never hand-edit the
generated SVGs; edit the generator and regenerate:

```
python3 tools/build_brand_assets.py
```

It is dependency-free and deterministic: two runs produce byte-identical files.

| Asset | Use |
|---|---|
| `hero.svg` | Wide README hero, 1200 x 360 |
| `hero-mobile.svg` | Portrait README hero for viewports at or below 600px |
| `cover.svg` | Editorial cover, 1280 x 640 |
| `social-preview.svg` | Editable master for the social card |
| `social-preview.png` | 1280 x 640 upload for Settings -> General -> Social preview |
| `authorization.svg` | The boundary diagram used in the README |

## This project's sculpture

A luminous payload waits outside an arched glass threshold until the application authorizes it to cross. The boundary is the subject; the payload only moves once the threshold ignites.

Every repository shares the material, lighting and palette; each keeps its own
silhouette, so the account reads as one system without the projects looking
alike.

## Constraints

No scripts, no event handlers, no `foreignObject`, no remote images, no remote
fonts, no tracking. System fonts only. Every SVG carries `<title>` and `<desc>`,
every README image carries alternative text, and `prefers-reduced-motion`
switches the motion off while leaving a complete composition behind.

## Social preview upload

Creating the PNG does not configure the repository setting. Upload it at
**Settings -> General -> Social preview -> Edit -> Upload an image**.
