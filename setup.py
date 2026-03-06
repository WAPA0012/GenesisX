"""Setup script for Genesis X."""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#") and not line.startswith("-r")
        ]

# Read dev requirements
dev_requirements_file = Path(__file__).parent / "requirements-dev.txt"
dev_requirements = []
if dev_requirements_file.exists():
    with open(dev_requirements_file) as f:
        # Extract only dev-specific packages (exclude -r requirements.txt)
        dev_requirements = [
            line.strip()
            for line in f
            if line.strip()
            and not line.startswith("#")
            and not line.startswith("-r")
        ]

setup(
    name="genesis-x",
    version="1.0.1",
    description="Genesis X: A Value-Driven Cognitive Architecture with Dynamic Organ Differentiation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Genesis X Project",
    author_email="genesisx@example.com",
    url="https://github.com/genesisx/genesisx",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples", "artifacts", "logs"]),
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
    },
    entry_points={
        "console_scripts": [
            "genesisx=run:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    keywords="cognitive-architecture, agi, value-alignment, digital-life, autonomous-agent",
    project_urls={
        "Documentation": "https://genesisx.readthedocs.io",
        "Source": "https://github.com/genesisx/genesisx",
        "Tracker": "https://github.com/genesisx/genesisx/issues",
    },
    include_package_data=True,
    zip_safe=False,
)
