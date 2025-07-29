"""
Setup script for the Expense Tracker CLI.
"""
from setuptools import setup, find_packages

setup(
    name="expense-tracker-cli",
    version="1.0.0",
    description="Command-line interface for the Expense Tracker application",
    author="Expense Tracker Team",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "aiohttp>=3.8.0",
        "toml>=0.10.0",
        "asyncio",
    ],
    entry_points={
        "console_scripts": [
            "expense-cli=cli.main:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)