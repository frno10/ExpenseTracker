"""
Budget management commands.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, Text