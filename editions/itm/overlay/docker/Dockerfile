# Metis for ITM — test image.
#
# Metis for ITM is installed on Windows with MetisSetup-ITM.exe. This image is
# for TESTING the same software anywhere Docker runs: it installs the edition
# the way the Windows installer does (same packages, same version lock, same
# database definition, same wizard step), as a new colleague who has just
# answered the setup questions, and then checks every surface and the ITM pack.
#
#   docker compose -f docker/docker-compose.yml up --build dashboard   → http://localhost:8080
#   docker compose -f docker/docker-compose.yml run --rm test          → the smoke test
#
# Build context: the repository root.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /metis
# Packages first, so a code change does not re-download them.
COPY system/mcp-server/pyproject.toml system/mcp-server/requirements.txt system/mcp-server/
COPY system/mcp-server/src system/mcp-server/src
COPY system/app-py/requirements.txt system/app-py/requirements.txt
# The extras the Windows installer adds (install.ps1 $Extras), minus `library`
# and `ocr`, which are heavy and not needed to test the edition.
RUN pip install --no-cache-dir -c system/mcp-server/requirements.txt \
        "./system/mcp-server[embedding,office]" \
    && pip install --no-cache-dir -r system/app-py/requirements.txt \
    && pip install --no-cache-dir httpx

COPY . /metis

ENV METIS_RC_ROOT=/metis \
    METIS_DATA_DIR=/data \
    PYTHONPATH=/metis/system/mcp-server/src:/metis/system/app-py \
    METIS_VERIFY_SANDBOX=1
VOLUME ["/data"]
EXPOSE 8080
RUN chmod +x /metis/docker/entrypoint.sh
ENTRYPOINT ["/metis/docker/entrypoint.sh"]
CMD ["dashboard"]
