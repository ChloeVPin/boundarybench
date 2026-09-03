# BoundaryBench public research site

This directory contains the public research studio site for BoundaryBench. It is intentionally dependency free so the same source can be served from a static host, a repository preview, or a custom domain without a build step.

## Local preview

From the repository root:

```bash
python -m http.server 4173 --directory site
```

Then open `http://localhost:4173`.

For a hosted package, run `bash scripts/build-site.sh` from the repository root. The generated output is kept in `dist/client` and is ignored by Git.

The site uses the repository as its source of truth. Research links point back to the versioned record, protocol, results, and responsible disclosure policy in the root project. The [site design audit](../docs/site-design-audit.md) records the visual references and translation decisions behind the layout.
