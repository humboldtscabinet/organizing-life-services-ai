# Vision/XO Local Workflow

The old browser helper endpoints under `/api/vision/gallery-structure`, `/save-file`, `/store-token`, `/get-token`, and `/xo-proxy` are retired. They accepted browser-supplied file writes, persisted XO tokens, or proxied arbitrary requests through the API.

Use this local-only workflow instead:

1. Export first-party vision results from the API with `GET /api/vision/export/csv`.
2. If you have a local `data/xo_gallery_images.json` manifest, flatten it with:

```bash
python scripts/export_xo_gallery_manifest.py \
  --input data/xo_gallery_images.json \
  --output data/xo_gallery_manifest.csv
```

3. Build any spreadsheet or XLSX artifacts locally from the CSV outputs.
4. Perform XO admin actions directly in the browser session that already has access to XO Gallery.

Rules:

- Do not send XO `id_token` values, bearer tokens, or session cookies to the FastAPI service.
- Do not persist XO browser tokens in repo files.
- Keep any temporary browser-export artifacts in gitignored local files only.
