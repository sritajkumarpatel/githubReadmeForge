from setuptools import setup, find_packages

setup(
    name="githubReadmeForge",
    version="0.1.0",
    description="Multi-agent CLI & Web tool that analyzes codebases and forges professional README.md files using AI.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="githubReadmeForge Contributors",
    url="https://github.com/your-username/githubReadmeForge",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "rich>=13.0.0",
        "requests>=2.28.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "gemini": ["google-generativeai>=0.3.0"],
        "openai": ["openai>=1.0.0"],
        "claude": ["anthropic>=0.18.0"],
        "all": [
            "google-generativeai>=0.3.0",
            "openai>=1.0.0",
            "anthropic>=0.18.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "readme-forge=readme_forge.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
