"""
Authentication utilities for CLI.
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from rich.console import Console
from rich.prompt import Prompt
from urllib.parse import urljoin

console = Console()


async def authenticate_user(api_url: str, email: str, password: str) -> Optional[str]:
    """Authenticate user and return auth token."""
    auth_url = urljoin(api_url, '/api/auth/login')
    
    auth_data = {
        'email': email,
        'password': password
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json=auth_data) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('access_token')
                else:
                    error_text = await response.text()
                    console.print(f"[red]Authentication failed: {error_text}[/red]")
                    return None
    except Exception as e:
        console.print(f"[red]Authentication error: {e}[/red]")
        return None


async def verify_token(api_url: str, token: str) -> bool:
    """Verify that auth token is still valid."""
    verify_url = urljoin(api_url, '/api/auth/verify')
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(verify_url, headers=headers) as response:
                return response.status == 200
    except Exception:
        return False


async def refresh_token(api_url: str, refresh_token: str) -> Optional[str]:
    """Refresh auth token using refresh token."""
    refresh_url = urljoin(api_url, '/api/auth/refresh')
    
    refresh_data = {
        'refresh_token': refresh_token
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(refresh_url, json=refresh_data) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('access_token')
                else:
                    return None
    except Exception:
        return None


async def ensure_authenticated(config: Dict[str, Any]) -> bool:
    """Ensure user is authenticated, prompt if not."""
    api_url = config.get('api_url')
    auth_token = config.get('auth_token')
    
    if not api_url:
        console.print("[red]API URL not configured. Run 'expense-cli config setup'[/red]")
        return False
    
    # Check if we have a token and if it's valid
    if auth_token:
        if await verify_token(api_url, auth_token):
            return True
        else:
            console.print("[yellow]Auth token expired or invalid[/yellow]")
    
    # Need to authenticate
    console.print("\n[bold blue]Authentication Required[/bold blue]")
    console.print("Please enter your credentials:")
    
    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    
    token = await authenticate_user(api_url, email, password)
    
    if token:
        # Save token to config
        from cli.utils.config import update_config_value
        update_config_value('auth_token', token)
        console.print("[green]✓ Authentication successful[/green]")
        return True
    else:
        console.print("[red]✗ Authentication failed[/red]")
        return False


def interactive_login(config: Dict[str, Any]) -> bool:
    """Interactive login process."""
    console.print("\n[bold blue]Login to Expense Tracker[/bold blue]")
    console.print("=" * 40)
    
    api_url = config.get('api_url')
    if not api_url:
        console.print("[red]API URL not configured. Run 'expense-cli config setup' first.[/red]")
        return False
    
    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    
    async def do_login():
        token = await authenticate_user(api_url, email, password)
        if token:
            from cli.utils.config import update_config_value
            update_config_value('auth_token', token)
            console.print("[green]✓ Login successful[/green]")
            return True
        else:
            console.print("[red]✗ Login failed[/red]")
            return False
    
    return asyncio.run(do_login())


def logout(config_path: Optional[str] = None) -> bool:
    """Logout by removing auth token."""
    from cli.utils.config import update_config_value
    
    if update_config_value('auth_token', None, config_path):
        console.print("[green]✓ Logged out successfully[/green]")
        return True
    else:
        console.print("[red]✗ Failed to logout[/red]")
        return False


async def get_user_info(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get current user information."""
    api_url = config.get('api_url')
    auth_token = config.get('auth_token')
    
    if not api_url or not auth_token:
        return None
    
    user_url = urljoin(api_url, '/api/auth/me')
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(user_url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
    except Exception:
        return None


def show_auth_status(config: Dict[str, Any]):
    """Show current authentication status."""
    console.print("\n[bold blue]Authentication Status[/bold blue]")
    console.print("=" * 40)
    
    api_url = config.get('api_url')
    auth_token = config.get('auth_token')
    
    console.print(f"API URL: {api_url or 'Not configured'}")
    
    if not auth_token:
        console.print("Status: [red]Not authenticated[/red]")
        console.print("\nRun 'expense-cli config auth' to login")
    else:
        async def check_status():
            if await verify_token(api_url, auth_token):
                console.print("Status: [green]Authenticated[/green]")
                
                user_info = await get_user_info(config)
                if user_info:
                    console.print(f"User: {user_info.get('email', 'Unknown')}")
                    console.print(f"Name: {user_info.get('name', 'Unknown')}")
            else:
                console.print("Status: [red]Token expired/invalid[/red]")
                console.print("\nRun 'expense-cli config auth' to re-authenticate")
        
        asyncio.run(check_status())
    
    console.print()