# Copyright 2025 BlazeMeter author
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.11-slim

WORKDIR /app

# Update system packages for security patches
RUN apt-get update -y && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r mcp-bzm-apitest && useradd -r -g mcp-bzm-apitest mcp-bzm-apitest

# Copy source and install dependencies
COPY pyproject.toml ./
COPY main.py ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

RUN chown -R mcp-bzm-apitest:mcp-bzm-apitest /app

# Switch to non-root user
USER mcp-bzm-apitest

ENV MCP_DOCKER=true

# Command to run the application
ENTRYPOINT ["python", "main.py"]
CMD ["--mcp"]
