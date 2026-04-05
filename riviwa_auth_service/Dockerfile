# ==============================================================================
# STAGE 1: BUILDER
# Installs build tools, creates a virtual environment, and installs dependencies.
# ==============================================================================
FROM python:3.11-slim as builder

# Prevent python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/riviwa_auth_service

# 1. Install system build dependencies
# 'build-essential' is required to compile C-extensions for packages
# like 'argon2-cffi' or 'psycopg2' if binary wheels are unavailable.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# 2. Install 'uv' (The modern, fast package manager)
RUN pip install uv

# 3. Create a virtual environment
# We install into a dedicated folder (/opt/venv) to easily copy it later.
RUN uv venv /opt/venv

# 4. Install Dependencies
# Activate the venv for the installation command via VIRTUAL_ENV env var
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .

# Install from the lock file using uv.
# --no-cache prevents storing download caches in the layer, keeping it small.
RUN uv pip install --no-cache -r requirements.txt


# ==============================================================================
# STAGE 2: RUNNER
# The final, minimal, and secure runtime image.
# ==============================================================================
FROM python:3.11-slim

# 1. Security: Create a non-root user
# Running as root is a security risk. We create a user named 'josako'.
RUN groupadd -r josako && useradd -r -g josako josako

# Crucial step: Install the PostgreSQL client libraries (libpq)
# This is required by the psycopg Python driver to connect to the DB.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

# 2. Runtime Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
    # Add the virtual environment to the PATH so we can run 'uvicorn' directly
ENV PATH="/opt/venv/bin:$PATH"

# --- CRITICAL FIX: Add the application root to the Python Path ---
# This tells Python to look in the /app directory when resolving imports like 'from auth_service...'
#ENV PYTHONPATH=/app:$PYTHONPATH

WORKDIR /app/riviwa_auth_service

# 3. Copy the Virtual Environment from the Builder Stage
# This brings over all installed Python packages (FastAPI, SQLModel, Argon2, etc.)
COPY --from=builder /opt/venv /opt/venv

# 4. Copy Application Code
# We copy the code last to maximize Docker layer caching during development.
COPY . /app/riviwa_auth_service

# 5. Copy the entrypoint script
# entrypoint.sh: waits for DB → runs alembic upgrade head → exec uvicorn.
# Placing it at the root keeps it outside the bind-mounted app folder so it
# is never accidentally overwritten by docker-compose.override.yml volumes.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 6. Set Permissions
# Ensure the non-root user owns the application files and entrypoint.
RUN chown -R josako:josako /app /entrypoint.sh

# 7. Switch to Non-Root User
USER josako

# 8. Expose the Application Port
EXPOSE 8000

# 9. Entrypoint runs on every container start (dev + prod):
#      wait for DB → alembic upgrade head → exec "$@"
#    CMD is the default passed to exec in production (no --reload).
#    docker-compose.override.yml overrides CMD with --reload for dev.
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]