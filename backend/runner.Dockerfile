# LegacyLift runner image: GnuCOBOL + Python. Runs uploaded COBOL and generated Python.
# Build from the repository root:
#   docker build -f backend/runner.Dockerfile -t legacylift-runner .
FROM python:3.15-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends gnucobol \
    && rm -rf /var/lib/apt/lists/*

# Only the runner and the helpers generated Python imports; no API code or settings.
WORKDIR /opt/runner
COPY backend/src/legacylift/__init__.py legacylift/
COPY backend/src/legacylift/cobol/__init__.py backend/src/legacylift/cobol/runtime.py legacylift/cobol/
COPY backend/src/legacylift/runner legacylift/runner/
# A .pth file keeps legacylift importable under `python -I`, which ignores PYTHONPATH.
RUN echo /opt/runner > "$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')/legacylift-runner.pth"

RUN useradd --create-home --uid 1001 runner
USER runner
WORKDIR /tmp

ENV PYTHONUNBUFFERED=1 \
    RUNNER_PORT=8001
EXPOSE 8001
CMD ["python", "-m", "legacylift.runner.server"]
