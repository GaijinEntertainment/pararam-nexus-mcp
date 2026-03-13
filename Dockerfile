FROM python:3.14-alpine

WORKDIR /app

ARG SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0

# Install build dependencies needed for some Python packages
RUN apk add --no-cache git gcc musl-dev python3-dev libffi-dev openssl-dev

# Copy pyproject.toml and README first to leverage Docker cache
COPY pyproject.toml README.md ./

# Copy source code
COPY src/ src/

# Install the package with pip
RUN SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION} pip install --no-cache-dir .

# Default environment variables (will be overridden at runtime)
ENV MCP_SERVER_NAME="pararam-nexus-mcp"
ENV MCP_DEBUG="false"

# Run the MCP server in stdio mode for Claude integration by default
ENTRYPOINT ["python", "-m", "pararam_nexus_mcp.server"]
