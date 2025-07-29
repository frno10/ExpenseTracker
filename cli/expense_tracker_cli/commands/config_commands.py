"""
Configuration management commands.
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import keyring
import yaml
import toml

from ..config import get_config_template
from ..utils.exceptions import ConfigurationError


@click.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command()
@click.pass_context
def setup(ctx):
    """Interactive configuration setup."""
    console = ctx.obj["console"]
    config_manager = ctx.obj["config_manager"]
    
    console.print("[bold blue]Expense Tracker CLI Configuration Setup[/bold blue]")
    console.print()
    
    # API Configuration
    console.print("[bold]API Configuration[/bold]")
    base_url = Prompt.ask(
        "API Base URL",
        default="http://localhost:8000"
    )
    timeout = Prompt.ask(
        "Request timeout (seconds)",
        default="30"
    )
    verify_ssl = Confirm.ask(
        "Verify SSL certificates?",
        default=True
    )
    
    # Authentication
    console.print("\n[bold]Authentication[/bold]")
    auth_method = Prompt.ask(
        "Authentication method",
        choices=["api_key", "basic"],
        default="api_key"
    )
    
    if auth_method == "api_key":
        api_key = Prompt.ask(
            "API Key (will be stored securely)",
            password=True
        )
        if api_key:
            keyring.set_password("expense-tracker-cli", "api_key", api_key)
            console.print("[green]API key stored securely[/green]")
    
    elif auth_method == "basic":
        username = Prompt.ask("Username")
        password = Prompt.ask("Password", password=True)
        if username and password:
            keyring.set_password("expense-tracker-cli", username, password)
            console.print("[green]Credentials stored securely[/green]")
    
    # Display preferences
    console.print("\n[bold]Display Preferences[/bold]")
    currency = Prompt.ask("Currency", default="USD")
    table_style = Prompt.ask(
        "Table style",
        choices=["grid", "simple", "fancy_grid", "plain"],
        default="grid"
    )
    
    # Export preferences
    console.print("\n[bold]Export Preferences[/bold]")
    default_format = Prompt.ask(
        "Default export format",
        choices=["csv", "pdf", "json"],
        default="csv"
    )
    output_directory = Prompt.ask(
        "Output directory",
        default="~/Downloads"
    )
    
    # Save configuration
    try:
        config_manager.set_config_value("api.base_url", base_url)
        config_manager.set_config_value("api.timeout", int(timeout))
        config_manager.set_config_value("api.verify_ssl", verify_ssl)
        config_manager.set_config_value("auth.method", auth_method)
        if auth_method == "basic":
            config_manager.set_config_value("auth.username", username)
        config_manager.set_config_value("display.currency", currency)
        config_manager.set_config_value("display.table_style", table_style)
        config_manager.set_config_value("export.default_format", default_format)
        config_manager.set_config_value("export.output_directory", output_directory)
        
        console.print("\n[green]✓ Configuration saved successfully![/green]")
        
        # Test connection
        if Confirm.ask("\nTest API connection?", default=True):
            from ..api.client import APIClient
            try:
                client = APIClient(config_manager.load_config())
                health = client.get_health()
                console.print("[green]✓ API connection successful![/green]")
            except Exception as e:
                console.print(f"[red]✗ API connection failed: {e}[/red]")
        
    except Exception as e:
        raise ConfigurationError(f"Failed to save configuration: {e}")


@config.command()
@click.pass_context
def show(ctx):
    """Show current configuration."""
    console = ctx.obj["console"]
    config_manager = ctx.obj["config_manager"]
    
    try:
        config_data = config_manager.show_config()
        
        table = Table(title="Current Configuration")
        table.add_column("Section", style="cyan")
        table.add_column("Key", style="magenta")
        table.add_column("Value", style="green")
        
        def add_config_rows(data, section=""):
            for key, value in data.items():
                if isinstance(value, dict):
                    add_config_rows(value, f"{section}.{key}" if section else key)
                else:
                    table.add_row(section, key, str(value))
        
        add_config_rows(config_data)
        console.print(table)
        
    except Exception as e:
        raise ConfigurationError(f"Failed to show configuration: {e}")


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key: str, value: str):
    """Set a configuration value."""
    console = ctx.obj["console"]
    config_manager = ctx.obj["config_manager"]
    
    try:
        # Try to convert value to appropriate type
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        elif "." in value and value.replace(".", "").isdigit():
            value = float(value)
        
        config_manager.set_config_value(key, value)
        console.print(f"[green]✓ Set {key} = {value}[/green]")
        
    except Exception as e:
        raise ConfigurationError(f"Failed to set configuration: {e}")


@config.command()
@click.argument("key")
@click.pass_context
def get(ctx, key: str):
    """Get a configuration value."""
    console = ctx.obj["console"]
    config_manager = ctx.obj["config_manager"]
    
    try:
        value = config_manager.get_config_value(key)
        console.print(f"{key} = {value}")
        
    except KeyError:
        console.print(f"[red]Configuration key '{key}' not found[/red]")
    except Exception as e:
        raise ConfigurationError(f"Failed to get configuration: {e}")


@config.command()
@click.option("--force", is_flag=True, help="Force reset without confirmation")
@click.pass_context
def reset(ctx, force: bool):
    """Reset configuration to defaults."""
    console = ctx.obj["console"]
    config_manager = ctx.obj["config_manager"]
    
    if not force and not Confirm.ask("Reset configuration to defaults?"):
        console.print("Configuration reset cancelled.")
        return
    
    try:
        config_manager.reset_config()
        console.print("[green]✓ Configuration reset to defaults[/green]")
        
    except Exception as e:
        raise ConfigurationError(f"Failed to reset configuration: {e}")


@config.command()
@click.pass_context
def validate(ctx):
    """Validate current configuration."""
    console = ctx.obj["console"]
    config_manager = ctx.obj["config_manager"]
    
    if config_manager.validate_config():
        console.print("[green]✓ Configuration is valid[/green]")
    else:
        console.print("[red]✗ Configuration validation failed[/red]")


@config.command()
@click.pass_context
def template(ctx):
    """Show configuration file template."""
    console = ctx.obj["console"]
    console.print(get_config_template())