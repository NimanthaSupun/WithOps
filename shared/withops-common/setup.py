"""
WithOps Common - Shared library for WithOps microservices
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="withops-common",
    version="0.1.0",
    author="WithOps Team",
    description="Shared library for WithOps microservices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.1",
        "pydantic>=2.5.0",
        "httpx>=0.25.0",
        "redis>=5.0.1",
        "python-jose[cryptography]>=3.3.0",
        "tenacity>=8.2.3",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
)
