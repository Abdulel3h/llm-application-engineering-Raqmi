# Raqmi branding assets

Repository-native presentation assets for the product case study. These files are visual documentation, not application components or evaluation evidence.

## Image reference map

| Asset | Used by | Purpose / source |
|---|---|---|
| [hero.svg](hero.svg) | Root `README.md`, introductory image | Original editable SVG: navy/teal banner, R monogram and product promise |
| Shields.io badges | Root `README.md`, badge row | External presentation labels for language, artifact and evidence type; not CI status or measured metrics |
| Mermaid architecture | Root `README.md`, architecture section | Text-based diagram rendered by GitHub; no separate image dependency |

No existing image assets were present at the time of this presentation update. No screenshots, provider logos or third-party brand assets are implied by the hero. All local image references use relative paths; the SVG has no scripts, external fonts, remote resources or embedded raster images.

## Visual conventions

- Background: `#0B1220`; secondary surface: `#112C36`.
- Accent: `#5EEAD4`; primary text: `#F8FAFC`; supporting text: `#B8C9D6`.
- Typography: system sans-serif (`Arial`, `Helvetica`, `sans-serif`).
- Keep the hero free of evaluation numbers, so the notebook and linked evidence remain the source for metrics.
- Keep readable alt text in the root README; the SVG also includes a title and description.
- Add future presentation images here with descriptive filenames and update this reference map. Keep execution evidence in its existing location.

## Suggested GitHub About metadata

These values are prepared for repository settings if the connected GitHub interface supports metadata updates; this document does not imply they have been applied.

**Description:** Arabic-first retail support AI case study: grounded answers, native tool calling, authorization outside the LLM, guardrails, and captured DeepSeek/ALLaM evaluations.

**Website:** https://abdulelah.de

**Topics:** `llm-application-engineering`, `arabic-nlp`, `retail-support`, `tool-calling`, `authorization`, `guardrails`, `structured-outputs`, `llm-evaluation`, `deepseek`, `allam`, `vllm`, `pydantic`, `google-colab`.
