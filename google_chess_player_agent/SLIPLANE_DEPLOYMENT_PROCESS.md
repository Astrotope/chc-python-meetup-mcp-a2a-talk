# Sliplane.io Deployment Process Documentation

## Overview
This document outlines the step-by-step process for deploying services on Sliplane.io, both through the web GUI and our automated script equivalent.

## Web GUI Deployment Process

### Step-by-Step Workflow

1. **Deploy Service**
   - Click "Deploy Service" button in Sliplane dashboard

2. **Choose Server**
   - Select from available servers in your organization
   - Consider location, instance type, and current load

3. **Choose Deploy from Repository**
   - Select "Deploy from Repository" option
   - **Important**: Configure repository access for Sliplane in GitHub (done offline)
   - Grant Sliplane GitHub app access to your repositories

4. **Choose Branch**
   - Default: `main`
   - Can select any available branch from the repository

5. **Set Path in Repo to Dockerfile**
   - Default: `Dockerfile`
   - For monorepos: `{sub-folder}/Dockerfile`
   - Example: `google_chess_player_agent/Dockerfile`

6. **Set Docker Context Path for Build**
   - Default: `.` (root directory)
   - For monorepos: `{sub-folder}/`
   - Example: `google_chess_player_agent/`

7. **Choose Service Visibility**
   - **Public**: Accessible from internet
   - **Private**: Internal access only within server network

8. **Choose Protocol**
   - **HTTP**: Web services, APIs (our default choice)
   - **TCP**: Raw TCP connections
   - **UDP**: UDP-based services

9. **Add Health Check Path**
   - Default: `/`
   - For A2A agents: `/.well-known/agent-card.json`
   - Custom endpoints like `/health` or `/status`

10. **Add Environment Variables**
    - Import from `.env` file one by one
    - **CRITICAL**: Add `PORT` environment variable with the deployed port value
    - Each variable has:
      - **Key**: Environment variable name
      - **Value**: Environment variable value
      - **Secret**: Mark sensitive values as secrets (encrypted)
    - **Important**: No `.env` file exists in deployment - apps must use `os.getenv()`

11. **Add Persistent Volume**
    - **Volume Name**: Unique identifier for the volume
    - **Mount Path**: Where volume is mounted in container
    - Example: `/app/data` for application data storage

12. **Give Service a Name**
    - Format: `{repo_name}-{subfolder}`
    - Example: `google_chess_player_agent-main`
    - Must be unique within the project

13. **Optional CMD Override**
    - Override the Docker CMD instruction
    - Leave blank to use Dockerfile's default CMD
    - Example: `python app.py --host 0.0.0.0 --port 10000`

14. **Deploy**
    - Click "Deploy" to start the deployment process
    - Service status changes to "pending" → "live" or "failed"

15. **Check Logs**
    - Monitor deployment logs for success/failure
    - Debug build issues or runtime errors
    - Verify service startup and health checks

16. **Obtain Deployment URLs**
    - **Public Domain URL**: `https://service-name.sliplane.app`
    - **Deploy Hook URL**: Secret URL for triggering re-deployments
    - **Internal Host URL**: For service-to-service communication

## Monorepo Deployment Configuration

### For Subfolder Deployments

```
Repository Structure:
├── project-root/
│   ├── service-a/
│   │   ├── Dockerfile
│   │   └── src/
│   └── service-b/
│       ├── Dockerfile
│       └── src/
```

**Configuration:**
- **Dockerfile Path**: `service-a/Dockerfile`
- **Docker Context Path**: `service-a/`
- **Service Name**: `project-root-service-a`

### For Root Level Deployments

**Configuration:**
- **Dockerfile Path**: `Dockerfile`
- **Docker Context Path**: `.`
- **Service Name**: `repository-name`

## Automation Script Equivalents

### Required Script Features

1. **Interactive Server Selection**
   - List available servers with status
   - Allow user to choose target server

2. **Repository Configuration**
   - GitHub URL input
   - Branch selection (default: main)
   - Dockerfile path configuration
   - Docker context path configuration

3. **Service Configuration**
   - Public/private visibility
   - Protocol selection (HTTP/TCP/UDP)
   - Health check endpoint
   - Environment variable management
   - Volume configuration
   - Service naming
   - CMD override option

4. **Deployment Management**
   - Trigger deployment
   - Monitor deployment status
   - Stream deployment logs
   - Report final URLs and status

### Environment Variable Handling

```bash
# Example .env processing
GOOGLE_API_KEY=secret_value:secret
DATABASE_URL=postgres://user:pass@host:5432/db
DEBUG=false
CHESS_MCP_SERVER_URL=http://chess-mcp:5000/mcp
# PORT will be added automatically by script
```

**Script should:**
- Parse `:secret` suffix to mark variables as secrets
- **Automatically add `PORT` environment variable** with the service port
- Prompt user to confirm each variable
- Allow editing or skipping variables

**⚠️ Critical Deployment Requirement:**
- **No `.env` file exists in Sliplane deployments**
- Applications must use `os.getenv()` fallbacks
- Cannot rely on `python-dotenv` or `.env` files in production

### Volume Configuration

**Interactive Prompts:**
- Volume name (default: `{service-name}-data`)
- Mount path (default: `/app/data`)
- Volume size (if supported)

### Service Naming Convention

**Format**: `{repo-name}-{subfolder}`
- Repository: `awesome-project`
- Subfolder: `api-service`
- Result: `awesome-project-api-service`

**Validation:**
- Must be unique within project
- Lowercase alphanumeric and hyphens only
- Maximum 63 characters

## Error Handling

### Common Deployment Failures

1. **Build Failures**
   - Missing Dockerfile
   - Invalid Docker context
   - Build dependency issues

2. **Runtime Failures**
   - Port binding issues
   - Missing environment variables
   - Health check failures

3. **Configuration Errors**
   - Invalid repository access
   - Incorrect volume mounts
   - Network configuration issues

### Script Error Recovery

- Provide clear error messages
- Suggest fixes for common issues
- Allow user to retry with different configuration
- Save partially completed configuration for retry

## Code Compatibility Requirements

### Environment Variable Handling in Production

**❌ This won't work in Sliplane:**
```python
from dotenv import load_dotenv
load_dotenv(".env")  # No .env file exists in deployment!
API_KEY = os.getenv("API_KEY")  # Will be None if not set
```

**✅ This will work in Sliplane:**
```python
import os
from dotenv import load_dotenv

# Load .env for local development only
if os.path.exists(".env"):
    load_dotenv(".env")

# Always provide fallbacks for production
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY environment variable is required")

# Or with defaults
PORT = int(os.getenv("PORT", "10000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

### Required Environment Variables for Sliplane

**Automatically Added by Platform:**
- `PORT` - The port your service should listen on (e.g., `10000`)

**Must Be Configured in Deployment:**
- All variables from your `.env` file
- Service-specific configuration
- External service URLs
- API keys and secrets

### Chess Agent Specific Requirements

```python
# chess_player_agent_server.py compatibility
import os
from dotenv import load_dotenv

# Load .env for development (will be skipped in production)
if os.path.exists(".env"):
    load_dotenv(".env")

# Environment variables with fallbacks
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
CHESS_MCP_SERVER_URL = os.getenv("CHESS_MCP_SERVER_URL", "http://localhost:5000/mcp")
A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "0.0.0.0")  # Must be 0.0.0.0 for containers
A2A_SERVER_PORT = int(os.getenv("PORT", os.getenv("A2A_SERVER_PORT", "10000")))

# Validation
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")
```

## Best Practices

### Security
- Always mark sensitive environment variables as secrets
- Use least-privilege GitHub access tokens
- Regularly rotate API tokens
- Keep deploy hook URLs private

### Performance
- Choose servers close to your users
- Use appropriate instance types for workload
- Configure health checks properly
- Monitor resource usage

### Maintenance
- Use descriptive service names
- Document environment variable purposes
- Keep Dockerfiles optimized
- Regular security updates

## API Mapping

### Sliplane API Endpoints Used

```
POST /projects/{projectId}/services
- Create new service with configuration

POST /projects/{projectId}/services/{serviceId}/deploy  
- Trigger deployment

GET /projects/{projectId}/services/{serviceId}
- Get service status

GET /projects/{projectId}/services/{serviceId}/logs
- Get deployment/runtime logs

GET /servers
- List available servers

GET /projects
- List available projects
```

### Script Implementation Notes

- Use read-only token for listing operations
- Require explicit permission for write operations
- Handle rate limiting (429 responses)
- Implement proper error handling and retries
- Provide progress feedback to user

---

**Last Updated**: August 22, 2025  
**Author**: Sliplane Deployment Automation  
**Version**: 1.0.0