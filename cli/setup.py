"""
Setup script for the Expense Tracker CLI application.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="expense-tracker-cli",
    version="1.0.0",
    author="Expense Tracker Team",
    author_email="team@expensetracker.com",
    description="Command-line interface for the Expense Tracker application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/expense-tracker/cli",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "requests>=2.28.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.0",
        "tabulate>=0.9.0",
        "toml>=0.10.0",
        "pyyaml>=6.0",
        "keyring>=24.0.0",
        "cryptography>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "expense-tracker=expense_tracker_cli.main:cli",
            "et=expense_tracker_cli.main:cli",  # Short alias
        ],
    },
    include_package_data=True,
    package_data={
        "expense_tracker_cli": ["templates/*.yaml", "config/*.toml"],
    },
)