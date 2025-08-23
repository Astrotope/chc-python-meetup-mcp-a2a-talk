#!/usr/bin/env python3
"""
Sliplane Deployment Automation Script

Automates the deployment of services to Sliplane.io from GitHub repositories.
Supports server selection, project management, and service configuration.
"""
import os
import sys
import json
import time
import argparse
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv


class ServiceStatus(Enum):
    """Service status enumeration"""
    PENDING = "pending"
    LIVE = "live"
    FAILED = "failed"
    SUSPENDED = "suspended"


class ServerStatus(Enum):
    """Server status enumeration"""
    BOOTING = "booting"
    RUNNING = "running"
    ERROR = "error"
    RESCALING = "rescaling"
    DELETING = "deleting"


@dataclass
class Server:
    """Server information"""
    id: str
    name: str
    status: str
    instance_type: str
    location: str
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None


@dataclass
class Project:
    """Project information"""
    id: str
    name: str


@dataclass
class Service:
    """Service information"""
    id: str
    name: str
    status: str
    project_id: str
    server_id: str
    created_at: str


class SliplaneAPIError(Exception):
    """Custom exception for Sliplane API errors"""
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class SliplaneClient:
    """
    Sliplane API client with dual token support (RO/RW)
    """
    
    def __init__(self, ro_token: str, rw_token: str, organization_id: str, skip_prompts: bool = False, base_url: str = "https://ctrl.sliplane.io/v0"):
        """
        Initialize Sliplane client with read-only and read-write tokens
        
        Args:
            ro_token: Read-only API token for list operations
            rw_token: Read-write API token for create/update operations
            organization_id: Organization ID for API requests
            skip_prompts: Skip permission prompts for write operations
            base_url: Base URL for Sliplane API
        """
        self.ro_token = ro_token
        self.rw_token = rw_token
        self.organization_id = organization_id
        self.base_url = base_url
        self.skip_prompts = skip_prompts
        
        # Configure requests sessions with retries (one for each token type)
        self.ro_session = self._create_session(ro_token)
        self.rw_session = self._create_session(rw_token)
    
    def _create_session(self, token: str) -> requests.Session:
        """Create configured requests session"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'Authorization': f'Bearer {token}',
            'X-Organization-ID': self.organization_id,
            'Content-Type': 'application/json',
            'User-Agent': 'SliplaneDeployBot/2.0'
        })
        return session
    
    def _is_write_operation(self, method: str, endpoint: str) -> bool:
        """Check if operation requires write permissions"""
        write_methods = ['POST', 'PATCH', 'PUT', 'DELETE']
        return method.upper() in write_methods
    
    def _request_write_permission(self, operation: str) -> bool:
        """Ask user for explicit permission to perform write operation"""
        print(f"\n⚠️  WRITE OPERATION REQUESTED")
        print(f"🔒 Operation: {operation}")
        
        # Provide detailed explanation based on the operation
        if "POST /projects/" in operation and "/services" in operation and "/deploy" not in operation:
            print("📝 About to CREATE A NEW SERVICE:")
            print("   • Creates a new containerized service on your selected server")
            print("   • Configures the service with your GitHub repository")
            print("   • Sets up environment variables and networking")
            print("   • Service will be created but NOT YET deployed")
            print("   • This operation is REVERSIBLE (you can delete the service)")
        elif "POST /projects/" in operation and "/deploy" in operation:
            print("📝 About to DEPLOY THE SERVICE:")
            print("   • Triggers a build from your GitHub repository")
            print("   • Deploys the built container to your server")
            print("   • Service will become LIVE and accessible")
            print("   • This will consume server resources and bandwidth")
        elif "POST /projects" in operation:
            print("📝 About to CREATE A NEW PROJECT:")
            print("   • Creates a new project container for organizing services")
            print("   • This is just an organizational structure")
            print("   • No server resources consumed")
        else:
            print("📝 This will use your READ-WRITE token and may modify your Sliplane resources.")
        
        print("\n🔐 This operation requires your READ-WRITE API token.")
        
        while True:
            try:
                response = input("Do you want to proceed? (yes/no): ").strip().lower()
                if response in ['yes', 'y']:
                    return True
                elif response in ['no', 'n']:
                    print("❌ Operation cancelled by user")
                    return False
                else:
                    print("Please answer 'yes' or 'no'")
            except KeyboardInterrupt:
                print("\n❌ Operation cancelled by user")
                return False
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make authenticated API request with appropriate token
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            JSON response data
            
        Raises:
            SliplaneAPIError: If API request fails
        """
        url = f"{self.base_url}{endpoint}"
        is_write_op = self._is_write_operation(method, endpoint)
        
        # Choose appropriate session based on operation type
        if is_write_op:
            # Get permission for write operations (unless skipped)
            operation_desc = f"{method.upper()} {endpoint}"
            if not self.skip_prompts:
                if not self._request_write_permission(operation_desc):
                    raise SliplaneAPIError("Operation cancelled by user")
            session = self.rw_session
            print(f"🔓 Using READ-WRITE token for: {operation_desc}")
        else:
            session = self.ro_session
            # print(f"🔍 Using READ-ONLY token for: {method.upper()} {endpoint}")
        
        try:
            response = session.request(method, url, **kwargs)
            
            # Handle different response codes
            if response.status_code == 204:  # No content
                return {}
            elif response.status_code == 429:  # Rate limited
                raise SliplaneAPIError(
                    "Rate limit exceeded. Please wait before retrying.",
                    status_code=response.status_code
                )
            elif not response.ok:
                try:
                    error_data = response.json()
                    message = error_data.get('message', f'HTTP {response.status_code}')
                except:
                    message = f'HTTP {response.status_code}: {response.text}'
                
                raise SliplaneAPIError(
                    message,
                    status_code=response.status_code,
                    response_data=error_data if 'error_data' in locals() else {}
                )
            
            return response.json() if response.content else {}
            
        except requests.RequestException as e:
            raise SliplaneAPIError(f"Request failed: {str(e)}")
    
    def list_servers(self) -> List[Server]:
        """
        List all available servers
        
        Returns:
            List of Server objects
        """
        response = self._make_request('GET', '/servers')
        return [
            Server(
                id=server['id'],
                name=server['name'],
                status=server['status'],
                instance_type=server['instanceType'],
                location=server['location'],
                ipv4=server.get('ipv4'),
                ipv6=server.get('ipv6')
            )
            for server in response
        ]
    
    def list_projects(self) -> List[Project]:
        """
        List all projects
        
        Returns:
            List of Project objects
        """
        response = self._make_request('GET', '/projects')
        return [
            Project(id=project['id'], name=project['name'])
            for project in response
        ]
    
    def create_project(self, name: str) -> Project:
        """
        Create a new project
        
        Args:
            name: Project name
            
        Returns:
            Created Project object
        """
        data = {'name': name}
        response = self._make_request('POST', '/projects', json=data)
        return Project(id=response['id'], name=response['name'])
    
    def create_service(
        self,
        project_id: str,
        server_id: str,
        name: str,
        github_url: str,
        branch: str = "main",
        dockerfile_path: str = "Dockerfile",
        docker_context: str = ".",
        auto_deploy: bool = True,
        public: bool = True,
        protocol: str = "http",
        health_check: str = "/",
        env_vars: Optional[List[Dict[str, Any]]] = None,
        cmd_override: Optional[str] = None
    ) -> Service:
        """
        Create a new service from GitHub repository
        
        Args:
            project_id: Target project ID
            server_id: Target server ID  
            name: Service name
            github_url: GitHub repository URL
            branch: Git branch to deploy (default: main)
            dockerfile_path: Path to Dockerfile (default: Dockerfile)
            docker_context: Docker build context (default: .)
            auto_deploy: Enable auto-deploy on git push (default: True)
            public: Make service publicly accessible (default: True)
            protocol: Network protocol (default: http)
            health_check: Health check endpoint (default: /)
            env_vars: Environment variables list
            cmd_override: Override Docker CMD instruction
            
        Returns:
            Created Service object
        """
        data = {
            'name': name,
            'serverId': server_id,
            'deployment': {
                'url': github_url,
                'branch': branch,
                'dockerfilePath': dockerfile_path,
                'dockerContext': docker_context,
                'autoDeploy': auto_deploy
            },
            'network': {
                'public': public,
                'protocol': protocol if public else None
            },
            'healthcheck': health_check
        }
        
        # Add optional fields
        if env_vars:
            data['env'] = env_vars
        if cmd_override:
            data['cmd'] = cmd_override
        
        response = self._make_request('POST', f'/projects/{project_id}/services', json=data)
        return Service(
            id=response['id'],
            name=response['name'],
            status=response['status'],
            project_id=response['projectId'],
            server_id=response['serverId'],
            created_at=response['createdAt']
        )
    
    def deploy_service(self, project_id: str, service_id: str) -> Dict[str, Any]:
        """
        Trigger service deployment
        
        Args:
            project_id: Project ID
            service_id: Service ID
            
        Returns:
            Deployment response data
        """
        return self._make_request('POST', f'/projects/{project_id}/services/{service_id}/deploy')
    
    def get_service_status(self, project_id: str, service_id: str) -> Service:
        """
        Get current service status
        
        Args:
            project_id: Project ID
            service_id: Service ID
            
        Returns:
            Service object with current status
        """
        response = self._make_request('GET', f'/projects/{project_id}/services/{service_id}')
        return Service(
            id=response['id'],
            name=response['name'],
            status=response['status'],
            project_id=response['projectId'],
            server_id=response['serverId'],
            created_at=response['createdAt']
        )
    
    def get_service_logs(self, project_id: str, service_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get service logs
        
        Args:
            project_id: Project ID
            service_id: Service ID
            limit: Maximum number of log entries
            
        Returns:
            List of log entries
        """
        params = {'limit': limit} if limit else {}
        return self._make_request('GET', f'/projects/{project_id}/services/{service_id}/logs', params=params)


class EnvironmentProcessor:
    """
    Processes environment variables for Sliplane deployment
    """
    
    def __init__(self):
        # Load .env file if it exists
        if os.path.exists(".env"):
            load_dotenv(".env")
    
    def _is_secret_var(self, key: str, value: str) -> bool:
        """Detect if an environment variable should be marked as secret"""
        secret_keywords = [
            'key', 'token', 'secret', 'password', 'auth', 'credential',
            'private', 'cert', 'signature', 'hash'
        ]
        
        # Check key name for secret indicators
        key_lower = key.lower()
        for keyword in secret_keywords:
            if keyword in key_lower:
                return True
        
        # Check if value looks like a secret (long alphanumeric string)
        if len(value) > 20 and any(c.isalnum() for c in value):
            return True
            
        return False
    
    def _transform_url_for_container(self, url: str) -> str:
        """Transform localhost URLs to container-friendly URLs"""
        if not url.startswith(('http://', 'https://')):
            return url
            
        # Transform localhost to service names
        transformations = {
            'http://localhost:5000/mcp': 'http://chess-mcp-server:5000/mcp',
            'http://127.0.0.1:5000/mcp': 'http://chess-mcp-server:5000/mcp',
            'http://localhost:': 'http://host.docker.internal:',
            'http://127.0.0.1:': 'http://host.docker.internal:',
        }
        
        for old, new in transformations.items():
            if url.startswith(old):
                return url.replace(old, new)
        
        return url
    
    def extract_env_vars(self, service_port: int = 10000) -> List[Dict[str, Any]]:
        """Extract environment variables from .env file only"""
        env_vars = []
        
        # Read .env file directly instead of from environment
        env_file_vars = {}
        if os.path.exists(".env"):
            with open(".env", 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Skip Sliplane API tokens (handled separately)
                        if not key.startswith('SLIPLANE_'):
                            env_file_vars[key] = value
        
        # Process variables from .env file
        for key, value in env_file_vars.items():
            # Skip empty values
            if not value.strip():
                continue
            
            # Transform URLs for container environment
            if 'URL' in key or 'HOST' in key:
                value = self._transform_url_for_container(value)
            
            # Determine if secret
            is_secret = self._is_secret_var(key, value)
            
            env_vars.append({
                'key': key,
                'value': value,
                'secret': is_secret
            })
        
        # Add PORT variable automatically if not present
        port_exists = any(var['key'] == 'PORT' for var in env_vars)
        if not port_exists:
            env_vars.append({
                'key': 'PORT',
                'value': str(service_port),
                'secret': False
            })
        
        # Sort by key name for consistent display
        return sorted(env_vars, key=lambda x: x['key'])
    
    def display_env_vars(self, env_vars: List[Dict[str, Any]]) -> None:
        """Display environment variables in a formatted way"""
        print(f"\n📦 Environment Variables ({len(env_vars)}):")
        print("-" * 50)
        
        for var in env_vars:
            key = var['key']
            value = var['value']
            is_secret = var['secret']
            
            if is_secret:
                # Mask secret values
                if len(value) > 8:
                    masked_value = f"{value[:4]}...{value[-4:]}"
                else:
                    masked_value = "*" * len(value)
                print(f"🔒 {key}: {masked_value} (secret)")
            else:
                print(f"📋 {key}: {value}")
        print()
    
    def extract_github_config(self) -> Dict[str, str]:
        """Extract GitHub repository configuration from .env file"""
        config = {}
        
        # Read .env file directly
        if os.path.exists(".env"):
            with open(".env", 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Extract GitHub-related config
                        if key in ['GITHUB_REPOSITORY_URL', 'GITHUB_BRANCH', 'DOCKERFILE_PATH', 'DOCKER_CONTEXT']:
                            config[key.lower()] = value
        
        # Set defaults for missing values
        config.setdefault('github_repository_url', '')
        config.setdefault('github_branch', 'main')
        config.setdefault('dockerfile_path', 'Dockerfile')
        config.setdefault('docker_context', '.')
        
        return config
    
    def confirm_env_vars(self, env_vars: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Confirm environment variables with user
        
        Returns:
            Tuple of (proceed, modified_env_vars)
        """
        self.display_env_vars(env_vars)
        
        while True:
            try:
                response = input("Use these environment variables? (yes/no/edit): ").strip().lower()
                
                if response in ['yes', 'y']:
                    return True, env_vars
                elif response in ['no', 'n']:
                    return False, env_vars
                elif response in ['edit', 'e']:
                    return self._edit_env_vars(env_vars)
                else:
                    print("Please answer 'yes', 'no', or 'edit'")
                    
            except KeyboardInterrupt:
                print("\n❌ Cancelled by user")
                return False, env_vars
    
    def _edit_env_vars(self, env_vars: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
        """Interactive environment variable editing"""
        print(f"\n✏️  Edit Environment Variables")
        print("Commands: 'skip <key>' to remove, 'secret <key>' to toggle secret, 'done' to finish")
        print("-" * 60)
        
        modified_vars = env_vars.copy()
        
        while True:
            try:
                # Show current variables
                self.display_env_vars(modified_vars)
                
                command = input("Edit command (or 'done'): ").strip()
                
                if command.lower() == 'done':
                    return True, modified_vars
                elif command.lower().startswith('skip '):
                    key_to_remove = command[5:].strip()
                    modified_vars = [var for var in modified_vars if var['key'] != key_to_remove]
                    print(f"✓ Removed {key_to_remove}")
                elif command.lower().startswith('secret '):
                    key_to_toggle = command[7:].strip()
                    for var in modified_vars:
                        if var['key'] == key_to_toggle:
                            var['secret'] = not var['secret']
                            status = "secret" if var['secret'] else "plain"
                            print(f"✓ {key_to_toggle} marked as {status}")
                            break
                    else:
                        print(f"❌ Variable {key_to_toggle} not found")
                else:
                    print("Invalid command. Use: skip <key>, secret <key>, or done")
                    
            except KeyboardInterrupt:
                print("\n❌ Edit cancelled")
                return False, env_vars


class SliplaneDeployer:
    """
    High-level deployment automation class
    """
    
    def __init__(self, client: SliplaneClient):
        self.client = client
    
    def interactive_server_selection(self) -> Server:
        """
        Interactive server selection from available servers
        
        Returns:
            Selected Server object
        """
        print("🔍 Fetching available servers...")
        servers = self.client.list_servers()
        
        if not servers:
            raise SliplaneAPIError("No servers available in organization")
        
        # Filter to running servers only
        running_servers = [s for s in servers if s.status == ServerStatus.RUNNING.value]
        
        if not running_servers:
            raise SliplaneAPIError("No running servers available")
        
        print(f"\n📋 Available Servers ({len(running_servers)} running):")
        print("-" * 60)
        for i, server in enumerate(running_servers, 1):
            print(f"{i:2d}. {server.name}")
            print(f"     ID: {server.id}")
            print(f"     Type: {server.instance_type}")
            print(f"     Location: {server.location}")
            print(f"     IP: {server.ipv4 or 'N/A'}")
            print()
        
        while True:
            try:
                choice = input(f"Select server (1-{len(running_servers)}): ").strip()
                index = int(choice) - 1
                if 0 <= index < len(running_servers):
                    selected = running_servers[index]
                    print(f"✅ Selected: {selected.name} ({selected.id})")
                    return selected
                else:
                    print(f"❌ Please enter a number between 1 and {len(running_servers)}")
            except ValueError:
                print("❌ Please enter a valid number")
            except KeyboardInterrupt:
                print("\n❌ Cancelled by user")
                sys.exit(1)
    
    def get_or_create_project(self, project_name: Optional[str] = None) -> Project:
        """
        Get existing project or create new one
        
        Args:
            project_name: Project name (if None, will prompt user)
            
        Returns:
            Project object
        """
        projects = self.client.list_projects()
        
        if not project_name:
            if projects:
                print(f"\n📁 Existing Projects ({len(projects)}):")
                print("-" * 40)
                for i, project in enumerate(projects, 1):
                    print(f"{i:2d}. {project.name} ({project.id})")
                print(f"{len(projects) + 1:2d}. Create new project")
                print()
                
                while True:
                    try:
                        choice = input(f"Select project (1-{len(projects) + 1}): ").strip()
                        index = int(choice) - 1
                        if 0 <= index < len(projects):
                            selected = projects[index]
                            print(f"✅ Using existing project: {selected.name}")
                            return selected
                        elif index == len(projects):
                            break
                        else:
                            print(f"❌ Please enter a number between 1 and {len(projects) + 1}")
                    except ValueError:
                        print("❌ Please enter a valid number")
                    except KeyboardInterrupt:
                        print("\n❌ Cancelled by user")
                        sys.exit(1)
            
            project_name = input("Enter new project name: ").strip()
            if not project_name:
                raise SliplaneAPIError("Project name cannot be empty")
        
        # Check if project already exists
        existing = next((p for p in projects if p.name == project_name), None)
        if existing:
            print(f"✅ Using existing project: {existing.name}")
            return existing
        
        print(f"🔨 Creating new project: {project_name}")
        return self.client.create_project(project_name)
    
    def deploy_from_github(
        self,
        github_url: str,
        service_name: Optional[str] = None,
        server: Optional[Server] = None,
        project: Optional[Project] = None,
        env_vars: Optional[List[Dict[str, Any]]] = None,
        **service_config
    ) -> Service:
        """
        Deploy service from GitHub repository with automatic environment processing
        
        Args:
            github_url: GitHub repository URL
            service_name: Service name (defaults to repo name)
            server: Target server (if None, will prompt user)
            project: Target project (if None, will prompt user)
            env_vars: Pre-processed environment variables
            **service_config: Additional service configuration
            
        Returns:
            Created Service object
        """
        # Extract service name from GitHub URL if not provided
        if not service_name:
            service_name = github_url.rstrip('/').split('/')[-1]
            if service_name.endswith('.git'):
                service_name = service_name[:-4]
        
        # Select server if not provided
        if not server:
            server = self.interactive_server_selection()
        
        # Get or create project if not provided  
        if not project:
            project = self.get_or_create_project()
        
        # Process environment variables if not provided
        if env_vars is None:
            env_processor = EnvironmentProcessor()
            service_port = service_config.get('port', 10000)
            env_vars = env_processor.extract_env_vars(service_port)
            
            # Confirm environment variables with user
            proceed, env_vars = env_processor.confirm_env_vars(env_vars)
            if not proceed:
                raise SliplaneAPIError("Deployment cancelled - environment variables not confirmed")
        
        print(f"\n🚀 Deploying {service_name} from {github_url}")
        print(f"📍 Server: {server.name} ({server.id})")
        print(f"📁 Project: {project.name} ({project.id})")
        print(f"📦 Environment variables: {len(env_vars)} configured")
        
        # Add environment variables to service config
        if env_vars:
            service_config['env_vars'] = env_vars
        
        # Create service
        service = self.client.create_service(
            project_id=project.id,
            server_id=server.id,
            name=service_name,
            github_url=github_url,
            **service_config
        )
        
        print(f"✅ Service created: {service.name} ({service.id})")
        return service
    
    def monitor_deployment(self, project_id: str, service_id: str, timeout: int = 300) -> bool:
        """
        Monitor deployment progress
        
        Args:
            project_id: Project ID
            service_id: Service ID
            timeout: Timeout in seconds
            
        Returns:
            True if deployment successful, False otherwise
        """
        print(f"\n⏳ Monitoring deployment...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                service = self.client.get_service_status(project_id, service_id)
                status = service.status
                
                if status == ServiceStatus.LIVE.value:
                    print(f"🎉 Deployment successful! Service is {status}")
                    return True
                elif status == ServiceStatus.FAILED.value:
                    print(f"❌ Deployment failed! Service status: {status}")
                    # Get logs for debugging
                    try:
                        logs = self.client.get_service_logs(project_id, service_id, limit=10)
                        if logs:
                            print("\n📋 Recent logs:")
                            for log in logs[-5:]:  # Show last 5 logs
                                print(f"  {log['createdAt']}: {log['message']}")
                    except Exception as e:
                        print(f"Could not fetch logs: {e}")
                    return False
                else:
                    print(f"⏳ Status: {status}... (waiting)")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"⚠️  Error checking status: {e}")
                time.sleep(5)
        
        print(f"⏰ Deployment timeout after {timeout} seconds")
        return False


def main():
    """Main CLI interface"""
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Interactive Sliplane.io Deployment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 Interactive Deployment Examples:

  # Deploy with guided prompts (recommended)
  python sliplane_deploy.py https://github.com/user/repo
  
  # Deploy with pre-configured options
  python sliplane_deploy.py https://github.com/user/google_chess_player_agent \\
    --service-name chess-agent \\
    --project "AI Agents" \\
    --env GOOGLE_API_KEY=your_key:secret
  
  # List-only operations (uses read-only token)
  python sliplane_deploy.py --list-servers
  python sliplane_deploy.py --list-projects

🔐 Security Features:
  - Separate read-only and read-write API tokens
  - Explicit permission prompts for all write operations
  - Environment variables loaded from .env file
        """
    )
    
    # Positional argument or list operations
    parser.add_argument('github_url', nargs='?', help='GitHub repository URL')
    
    # List-only operations (read-only)
    parser.add_argument('--list-servers', action='store_true', help='List available servers (read-only)')
    parser.add_argument('--list-projects', action='store_true', help='List existing projects (read-only)')
    
    # Deployment configuration
    parser.add_argument('--service-name', help='Service name (defaults to repo name)')
    parser.add_argument('--project', help='Project name')
    parser.add_argument('--branch', default='main', help='Git branch (default: main)')
    parser.add_argument('--dockerfile', default='Dockerfile', help='Dockerfile path (default: Dockerfile)')
    parser.add_argument('--context', default='.', help='Docker build context (default: .)')
    parser.add_argument('--health-check', default='/', help='Health check endpoint (default: /)')
    parser.add_argument('--private', action='store_true', help='Make service private (not publicly accessible)')
    parser.add_argument('--protocol', default='http', choices=['http', 'tcp', 'udp'], help='Network protocol (default: http)')
    parser.add_argument('--no-auto-deploy', action='store_true', help='Disable auto-deploy on git push')
    parser.add_argument('--cmd', help='Override Docker CMD instruction')
    parser.add_argument('--env', action='append', help='Additional environment variable (KEY=value or KEY=value:secret) - .env auto-loaded')
    parser.add_argument('--skip-env-confirm', action='store_true', help='Skip environment variable confirmation prompt')
    parser.add_argument('--timeout', type=int, default=300, help='Deployment timeout in seconds (default: 300)')
    parser.add_argument('--skip-permission-prompts', action='store_true', help='Skip write permission prompts (use with caution)')
    
    args = parser.parse_args()
    
    # Get API credentials from environment
    ro_token = os.getenv('SLIPLANE_API_TOKEN_RO')
    rw_token = os.getenv('SLIPLANE_API_TOKEN_RW') 
    org_id = os.getenv('SLIPLANE_ORG_ID')
    
    # Validate required credentials
    if not org_id:
        print("❌ Error: Organization ID required. Set SLIPLANE_ORG_ID in .env file")
        print("   Get this from Sliplane Dashboard -> Team Settings -> API")
        sys.exit(1)
    
    # Check if we need write operations
    is_list_only = args.list_servers or args.list_projects
    
    if not ro_token:
        print("❌ Error: Read-only API token required. Set SLIPLANE_API_TOKEN_RO in .env file")
        print("   Create a read-only token in Sliplane Dashboard -> Team Settings -> API")
        sys.exit(1)
    
    if not is_list_only and not rw_token:
        print("❌ Error: Read-write API token required for deployment operations.")
        print("   Set SLIPLANE_API_TOKEN_RW in .env file")
        print("   Create a read-write token in Sliplane Dashboard -> Team Settings -> API")
        sys.exit(1)
    
    # For list-only operations, we can use empty RW token
    if is_list_only:
        rw_token = rw_token or ""
    
    # Process environment variables
    env_processor = EnvironmentProcessor()
    
    # Extract from .env and environment
    service_port = 10000  # Default port, could be made configurable
    env_vars = env_processor.extract_env_vars(service_port)
    
    # Add any additional environment variables from command line
    if args.env:
        for env_str in args.env:
            try:
                if '=' not in env_str:
                    raise ValueError("Environment variable must be in format KEY=value")
                
                key, value_part = env_str.split('=', 1)
                if ':secret' in value_part:
                    value = value_part.replace(':secret', '')
                    secret = True
                else:
                    value = value_part
                    secret = False
                
                # Override existing or add new
                existing_var = next((var for var in env_vars if var['key'] == key.strip()), None)
                if existing_var:
                    existing_var['value'] = value.strip()
                    existing_var['secret'] = secret
                    print(f"🔄 Overriding {key.strip()} from command line")
                else:
                    env_vars.append({
                        'key': key.strip(),
                        'value': value.strip(),
                        'secret': secret
                    })
                    print(f"➕ Adding {key.strip()} from command line")
                    
            except ValueError as e:
                print(f"❌ Error parsing environment variable '{env_str}': {e}")
                sys.exit(1)
    
    # Confirm environment variables unless skipped
    if not args.skip_env_confirm:
        proceed, env_vars = env_processor.confirm_env_vars(env_vars)
        if not proceed:
            print("❌ Deployment cancelled - environment variables not confirmed")
            sys.exit(1)
    
    try:
        # Initialize client with dual tokens
        client = SliplaneClient(ro_token, rw_token, org_id, skip_prompts=args.skip_permission_prompts)
        
        # Handle list-only operations
        if args.list_servers:
            print("🖥️  Listing Available Servers")
            print("=" * 40)
            servers = client.list_servers()
            if not servers:
                print("No servers found in organization")
            else:
                for server in servers:
                    status_icon = "🟢" if server.status == "running" else "🟡" if server.status == "booting" else "🔴"
                    print(f"{status_icon} {server.name} ({server.id})")
                    print(f"   Type: {server.instance_type} | Location: {server.location} | Status: {server.status}")
                    if server.ipv4:
                        print(f"   IPv4: {server.ipv4}")
                    print()
            return
        
        if args.list_projects:
            print("📁 Listing Projects")
            print("=" * 30)
            projects = client.list_projects()
            if not projects:
                print("No projects found in organization")
            else:
                for project in projects:
                    print(f"📂 {project.name} ({project.id})")
            return
        
        # Get GitHub configuration from .env file or command line
        github_config = env_processor.extract_github_config()
        github_url = args.github_url or github_config.get('github_repository_url', '')
        
        # Validate GitHub URL for deployment operations
        if not github_url:
            print("❌ Error: GitHub repository URL required for deployment")
            print("   Provide via command line: python sliplane_deploy.py <github_url>")
            print("   Or add GITHUB_REPOSITORY_URL to .env file")
            print("   Use --list-servers or --list-projects for read-only operations")
            sys.exit(1)
        
        print(f"🔗 Repository: {github_url}")
        if not args.github_url:
            print("   (Loaded from .env file)")
        
        # Initialize deployer for deployment operations
        deployer = SliplaneDeployer(client)
        
        print("🚀 Interactive Sliplane Deployment")
        print("=" * 50)
        print("🔐 Security: Using separate read-only and read-write tokens")
        if args.skip_permission_prompts:
            print("⚡ Permission prompts DISABLED - write operations will proceed automatically")
        else:
            print("⚠️  You will be prompted before any write operations")
        print()
        
        # Prepare service configuration using .env file defaults when available
        service_config = {
            'branch': args.branch if args.branch != 'main' else github_config.get('github_branch', 'main'),
            'dockerfile_path': args.dockerfile if args.dockerfile != 'Dockerfile' else github_config.get('dockerfile_path', 'Dockerfile'),
            'docker_context': args.context if args.context != '.' else github_config.get('docker_context', '.'),
            'auto_deploy': not args.no_auto_deploy,
            'public': not args.private,
            'protocol': args.protocol,
            'health_check': args.health_check,
        }
        
        # Display configuration being used
        print(f"⚙️  Branch: {service_config['branch']}")
        print(f"🐳 Dockerfile: {service_config['dockerfile_path']}")
        print(f"📁 Context: {service_config['docker_context']}")
        if service_config['dockerfile_path'] != 'Dockerfile' or service_config['docker_context'] != '.':
            print("   (Using .env file configuration)")
        
        if args.cmd:
            service_config['cmd_override'] = args.cmd
        
        # Deploy service with processed environment variables
        project = deployer.get_or_create_project(args.project) if args.project else None
        service = deployer.deploy_from_github(
            github_url=github_url,  # Use github_url from .env or command line
            service_name=args.service_name,
            project=project,
            env_vars=env_vars,  # Pass processed environment variables
            **service_config
        )
        
        # Monitor deployment
        success = deployer.monitor_deployment(
            service.project_id,
            service.id,
            timeout=args.timeout
        )
        
        if success:
            print(f"\n🎉 Deployment completed successfully!")
            print(f"📍 Service ID: {service.id}")
            print(f"🌐 Access your service through the Sliplane dashboard")
            sys.exit(0)
        else:
            print(f"\n❌ Deployment failed or timed out")
            sys.exit(1)
            
    except SliplaneAPIError as e:
        print(f"❌ API Error: {e.message}")
        if e.status_code:
            print(f"   HTTP Status: {e.status_code}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()