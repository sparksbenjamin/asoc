"""
ASoc - AI Socket Protocol
Setup script for pip installation
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="asoc-protocol",
    version="0.1.0",
    author="ASoc Contributors",
    author_email="",
    description="Ultra-compact, peer-to-peer, tensor-native networking for AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/asoc-protocol",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=[
        # No dependencies! Pure Python.
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
        "benchmark": [
            "numpy>=1.20",
        ],
    },
    entry_points={
        "console_scripts": [
            "asoc-test=test_setup:main",
            "asoc-benchmark=benchmark_ready:main",
        ],
    },
)
