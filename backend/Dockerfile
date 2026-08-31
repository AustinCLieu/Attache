# Production image for the Attaché backend (API + worker).
# Built and tested from M1 so the M8 deploy to ECR/App Runner holds no surprises.

FROM python:3.12-slim

# PYTHONUNBUFFERED: log lines reach CloudWatch immediately instead of sitting
#   in a buffer. PYTHONDONTWRITEBYTECODE: no .pyc files, which a container
#   throws away anyway.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# The build backend needs the package source present to resolve the project,
# so pyproject.toml and app/ are copied before the install.
COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

# Migrations ship with the image so `alembic upgrade head` can be run against
# RDS from this same container in M8.
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

# Run as a non-root user: a container process should not be root.
RUN useradd --create-home --uid 1000 attache && chown -R attache:attache /srv
USER attache

EXPOSE 8000

# No --reload: that is a development convenience and would be a liability here.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
