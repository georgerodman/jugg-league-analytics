FROM node:22.18.0-bookworm-slim AS node_runtime

FROM python:3.12.11-slim-bookworm

COPY --from=node_runtime /usr/local/ /usr/local/

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        git \
        poppler-utils \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 developer \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash developer

WORKDIR /workspace

USER developer

CMD ["sleep", "infinity"]
