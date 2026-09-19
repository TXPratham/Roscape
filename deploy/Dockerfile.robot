FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/amr-fleet

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY comms ./comms
COPY planning ./planning
COPY sim ./sim
COPY tasks ./tasks
COPY deploy/robot_entrypoint.py ./deploy/robot_entrypoint.py

RUN addgroup --system amr && adduser --system --ingroup amr amr \
    && chown -R amr:amr /opt/amr-fleet
USER amr

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os; os.kill(1, 0)"]

CMD ["python", "-m", "deploy.robot_entrypoint"]
