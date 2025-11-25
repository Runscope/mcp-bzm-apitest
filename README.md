# BlazeMeter API Test MCP Server

The BlazeMeter API Test MCP Server connects AI tools directly to cloud-based BlazeMeter API Testing & Monitoring platform (Runscope). 
This gives AI agents, assistants, and chatbots the ability to read and manage teams, buckets and tests, analyze test and its results, and automate workflows. All through natural language interactions.

## **Use Cases**
**Team Operations**
- List all teams the user is a member of to establish the organizational context.
- Retrieve details of a specific team, including team ID, name, and associated permissions.
- This serves as the root entity for all downstream resources such as buckets, tests, and results.

**Bucket Management**
- List all buckets belonging to a team.
- Retrieve a specific bucket by ID or name to inspect its metadata and structure.
- Create new buckets to organize API tests under logical projects or services.
- Run bucket-level test suites, executing all tests defined within the bucket and retrieving their aggregated results.

**Test Management**
- List all tests within a bucket to get visibility into available API tests.
- Retrieve a single test by ID or name to view its configuration, steps, and environment references.
- Create new tests programmatically via MCP tools for automation or migration workflows.
- Run an individual test and obtain its execution results, including pass/fail status and timestamps.

**Test Scheduling Management**
- Create a new test schedules to automate test execution at predefined intervals.
- View existing schedules to manage or audit automated test runs.
- Retrieve associated schedules for a test to understand its execution context and frequency.

**Test Step Management**
- List all steps within a test to understand its workflow and structure.
- Retrieve a single step’s details to inspect API request/response configuration, conditions, and validations.
- Create a new test step (Pause or Request) to modify or extend test workflows.

> [!NOTE]
> **For detailed documentation including use cases, available tools, integration points, and troubleshooting, see the [BlazeMeter API Test MCP Server documentation](https://help.blazemeter.com/docs/guide/integrations-blazemeter-mcp-server.html).**

---

## Prerequisites

- BlazeMeter API Monitoring Access Token
- Comply [Blazemeter API Monitoring AI Consent](https://help.blazemeter.com/docs/guide/api-monitoring-ai-consent.html?Highlight=AI%20consent)
- Compatible MCP host (VS Code, Claude Desktop, Cursor, Windsurf, etc.)
- Docker (only for Docker-based deployment)
- [uv](https://docs.astral.sh/uv/) and Python 3.11+ (only for installation from source code distribution)

## Setup

### **Get BlazeMeter API Monitoring token**
Follow the [BlazeMeter API Token guide](https://help.blazemeter.com/apidocs/api-monitoring/authentication.htm?tocpath=API%20Monitoring%7CAuthentication%20Process%7C_____0#applications) to obtain your Access Token. Once access token is obtained, following are the ways to provide it to the MCP client.
 
### **Via Environment Variable**
You can provide the API token to the MCP client using one of the following methods:
- Set the `BZM_API_TEST_TOKEN` env variable to the token value directly.
- Set the `BZM_API_TEST_TOKEN_FILE` env variable to the path of a `<file_name>.env` file with the following content:

    ```
    BZM_API_TEST_TOKEN=your_api_test_token_here
    ``` 

### **Via Env file**
- Create a `bzm_api_test_token.env` file in the same directory where the executable/binary is located with the following content:

    ```
    BZM_API_TEST_TOKEN=your_api_test_token_here
    ```

### **Quick Setup with CLI Tool** ⚡

The easiest way to configure your MCP client is using our interactive CLI tool:

1. **Download the appropriate binary** for your operating system from the [Releases](https://github.com/Runscope/mcp-bzm-apitest/releases) page

> [!NOTE]
> Choose the binary that matches your OS (Windows, macOS, Linux)
2. **Execute or Double-click the binary** to launch the interactive configuration tool
3. **The tool automatically generates** the JSON configuration file for you

> [!IMPORTANT]
> For macOS: You may encounter a security alert saying "Apple could not verify 'mcp-bzm-apitest-darwin' is free of malware." To resolve this:
> 1. Go to **System Settings** → **Privacy & Security** → **Security**
> 2. Look for the blocked application and click **"Allow Anyway"**
> 3. Try running the binary again
---

**Manual Client Configuration (Binary Installation)**

1. **Download the binary** for your operating system from the [Releases](https://github.com/Runscope/mcp-bzm-apitest/releases) page
2. **Configure your MCP client** with the following settings:

```json
{
  "mcpServers": {
    "BlazeMeter API Test MCP": {
      "command": "/path/to/mcp-bzm-apitest-binary",
      "args": ["--mcp"],
      "env": {
        "BZM_API_TEST_TOKEN_FILE": "/path/to/your/bzm_api_test_token.env"
      }
    }
  }
}
```
---

**Manual Client Configuration (From Remote Source Code)**

1. **Prerequisites:** [uv](https://docs.astral.sh/uv/) and Python 3.11+
2. **Configure your MCP client** with the following settings:

```json
{
  "mcpServers": {
    "BlazeMeter API Test MCP": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/Runscope/mcp-bzm-apitest.git@v1.0.0",
        "-q", "mcp-bzm-apitest", "--mcp"
      ],
      "env": {
        "BZM_API_TEST_TOKEN_FILE": "/path/to/your/bzm_api_test_token.env"
      }
    }
  }
}
```

> [!NOTE]
> uvx installs and runs the package and its dependencies in a temporary environment.
> You can change to any version that has been released or any branch you want.
> For more details on the uv/uvx arguments used, please refer to the official [uv documentation](https://docs.astral.sh/uv/).

</details>

---

**Docker MCP Client Configuration**

```json
{
  "mcpServers": {
    "Docker BlazeMeter API Test MCP": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "BZM_API_TEST_TOKEN=your_api_token",
        "ghcr.io/blazemeter/mcp-bzm-apitest:latest"
      ]
    }
  }
}
```

---

**Custom CA Certificates (Corporate Environments) for Docker**

**When you need this:**
- Your organization uses self-signed certificates
- You're behind a corporate proxy with SSL inspection
- You have a custom Certificate Authority (CA)
- You encounter SSL certificate verification errors when running tests

**Required Configuration:**

When using custom CA certificate bundles, you must configure both:

1. **Certificate Volume Mount**: Mount your custom CA certificate bundle into the container
2. **SSL_CERT_FILE Environment Variable**: Explicitly set the `SSL_CERT_FILE` environment variable to point to the certificate location inside the container

<details><summary><strong>Example Configuration</strong></summary>

```json
{
  "mcpServers": {
    "Docker BlazeMeter API TEST MCP": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "SSL_CERT_FILE=/etc/ssl/certs/custom-ca-bundle.crt",
        "-e",
        "BZM_API_TEST_TOKEN=your_api_token",
        "ghcr.io/blazemeter/mcp-bzm-apitest:latest"
      ]
    }
  }
}
```

**Replace:**
- `/path/to/your/ca-bundle.crt` with your host system's CA certificate file path
- The container path `/etc/ssl/certs/custom-ca-bundle.crt` can be any path you prefer (just ensure it matches `SSL_CERT_FILE`)

> The `SSL_CERT_FILE` environment variable must be set to point to your custom CA certificate bundle. The `httpx` library [automatically respects the `SSL_CERT_FILE` environment variable](https://www.python-httpx.org/advanced/ssl/#working-with-ssl_cert_file-and-ssl_cert_dir) for SSL certificate verification.
</details>


---

## Tools
The BlazeMeter API Test MCP Server provides the following tools for interacting with the BlazeMeter API Test & Monitoring platform:
- **blazmeter_apitest_teams**: List teams within your BlazeMeter account, Read team details, and Get a list of all team users.
- **blazmeter_apitest_buckets**: List all the buckets, Read bucket details, and Create a new bucket.
- **blazmeter_apitest_tests**: List all API tests within a bucket, Read test details, Create a new API test, and Get the test metrics.
- **blazmeter_apitest_schedules**: List all schedules within a test, Read schedule details, and Create a new schedule.
- **blazmeter_apitest_steps**: List all steps within a test, Read test step details, and Add a new Pause and Request step( with URL, Method, Body and Assertions) to a test.
- **blazmeter_apitest_environments**: List all test environments, and Read test environment details.
- **blazmeter_apitest_results**: Execute an individual test or all bucket-level tests, List last 50 test results, and Read test result and bucket-level result details.

## Security
- Never share API tokens
- Recommended to use token in .env file rather than directly in environment variables
- Keep .env files secure and private

## License

This project is licensed under the Apache License, Version 2.0. Please refer to [LICENSE](./LICENSE) for the full terms.

---

## Support

- **MCP Server Documentation**: [BlazeMeter API Test MCP Server Guide](https://help.blazemeter.com/docs/guide/integrations-blazemeter-mcp-server.html)
- **API Documentation**: [BlazeMeter API Test API Documentation](https://help.blazemeter.com/apidocs/api-monitoring/index.htm?tocpath=API%20Monitoring%7C_____1)
- **Issues**: [GitHub Issues](https://github.com/Runscope/mcp-bzm-apitest/issues)
- **Support**: Contact BlazeMeter support for enterprise assistance
