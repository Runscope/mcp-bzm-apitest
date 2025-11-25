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

FROM ubuntu:25.10


WORKDIR /app

# Update system packages for security patches
RUN apt-get update -y && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r mcp-bzm-apitest && useradd -r -g mcp-bzm-apitest mcp-bzm-apitest

ARG TARGETPLATFORM

# Copy all pre-built binaries
COPY dist/ ./dist/

# Select and copy the appropriate binary based on target platform
RUN case "${TARGETPLATFORM}" in \
    "linux/amd64") cp ./dist/mcp-bzm-apitest-linux-amd64 ./mcp-bzm-apitest ;; \
    "linux/arm64") cp ./dist/mcp-bzm-apitest-linux-arm64 ./mcp-bzm-apitest ;; \
    *) echo "Unsupported platform: ${TARGETPLATFORM}. Supported: linux/amd64, linux/arm64" && exit 1 ;; \
    esac && \
    echo "Selected binary for platform: ${TARGETPLATFORM}" && \
    rm -rf ./dist/


RUN chmod +x ./mcp-bzm-apitest && \
    chown mcp-bzm-apitest:mcp-bzm-apitest ./mcp-bzm-apitest

# Switch to non-root user
USER mcp-bzm-apitest

ENV MCP_DOCKER=true

# Command to run the application
ENTRYPOINT ["./mcp-bzm-apitest"]
CMD ["--mcp"]