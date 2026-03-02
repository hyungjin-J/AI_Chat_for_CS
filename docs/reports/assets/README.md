# Buyer PDF Cover Image

`scripts/generate_nondev_blueprint_pdf.py` supports a custom cover architecture image.

## Default lookup order

1. `--architecture-image <path>` argument
2. `docs/reports/assets/buyer_architecture_diagram.png` (recommended)
3. `docs/architecture/diagrams/cs_rag_system_architecture_v1.png` (fallback)

## Usage

```bash
python scripts/generate_nondev_blueprint_pdf.py \
  --input docs/reports/BUYER_READY_PRODUCT_GUIDE_KR.md \
  --output docs/reports/BUYER_READY_PRODUCT_GUIDE_KR_20260227.pdf \
  --architecture-image docs/reports/assets/buyer_architecture_diagram.png
```

## In-body explainer images

The buyer guide supports inline markdown image syntax:

```md
![캡션](assets/explainers/01_rag_pipeline.png)
```

Generated explainer assets are stored under:

- `docs/reports/assets/explainers/01_rag_pipeline.png`
- `docs/reports/assets/explainers/02_fail_closed_compare.png`
- `docs/reports/assets/explainers/03_tenant_rbac.png`
- `docs/reports/assets/explainers/04_traceid_observability.png`

Regenerate them with:

```bash
python scripts/generate_buyer_explainer_images.py
```
