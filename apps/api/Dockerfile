# Builds the FastAPI service (and, via start.sh, the ARQ worker in the same
# container) for a single free-tier host (docs/DEPLOYMENT.md) that gives one
# process slot per service. Build context is the REPO ROOT, not apps/api/ --
# `coolblock-engine` (the `engine/` package) is a uv workspace root dependency
# of `coolblock-api` (apps/api/pyproject.toml's `[tool.uv.sources]`), and
# `data/derived/edison-eastlake/` (docs/adr/0030-*.md) is what the app reads
# at request time -- both have to be in the build context, so a plain
# `apps/api/` context can't build this image.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# rasterio's manylinux wheel bundles GDAL itself, but GDAL still dynamically
# links a handful of ordinary system libraries at import time that
# `-slim`'s minimal image doesn't ship -- confirmed by actually building and
# running this image, not assumed: it failed on `libexpat.so.1` first, then
# the rest of this list one shared-object error at a time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 libsqlite3-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /repo

# Manifests *and* source together, before `uv sync` -- confirmed by actually
# building this image, not assumed: `coolblock-api`/`coolblock-engine` are
# local workspace path-dependencies (`[tool.uv.sources]`), not published
# wheels, so `uv sync` has to build them from real source at sync time.
# Manifests-only (the usual Docker-cache trick, valid for real third-party
# deps) produced *valid-looking* dist-info for both with no actual module
# inside -- everything appeared to succeed, then every import of either
# package failed at container start. `--mount=type=cache` keeps this from
# costing a full third-party redownload on every source-code change: the
# uv package cache persists across builds even though this COPY+RUN layer
# itself can't.
COPY pyproject.toml uv.lock ./
COPY apps/api/ apps/api/
COPY engine/ engine/
COPY config/ config/
COPY data/derived/edison-eastlake/ data/derived/edison-eastlake/
# Three small (~80 KB total), public-only raw-cache sources request-time
# code still reads directly: Census block-group boundaries (constrained
# solves' zone assignment), Census ACS5 and Tree Equity Score block-group
# aggregates (the baseline comparison). docs/adr/0032-*.md is why
# `maricopa_parcels/` -- real names and home addresses -- is deliberately
# NOT one of these.
COPY data/cache/tiger_block_groups/ data/cache/tiger_block_groups/
COPY data/cache/census_acs5/ data/cache/census_acs5/
COPY data/cache/tree_equity_score/ data/cache/tree_equity_score/

# rasterio/geopandas/highspy ship GDAL and their other native libraries
# inside their own manylinux wheels -- no `apt-get install gdal-bin` needed.
# `--no-dev`: this container never runs pytest/ruff/mypy, only the app.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package coolblock-api

ENV PATH="/repo/.venv/bin:$PATH"
WORKDIR /repo/apps/api

# start.sh was already copied in with the rest of apps/api/ above.
RUN chmod +x /repo/apps/api/start.sh

# Render (and most free-tier hosts) inject $PORT at runtime -- start.sh
# reads it, so this EXPOSE is documentation, not a binding.
EXPOSE 8000

CMD ["/repo/apps/api/start.sh"]
