from setuptools import setup, find_packages

setup(
    name="minitel-lite-client",
    version="1.0.0",
    description="MiniTel-Lite Emergency Protocol Client for NORAD JOSHUA Override Mission",
    author="Agent LIGHTMAN",
    author_email="lightman@norad.mil",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "pytest-asyncio>=0.21.0",
        "rich>=13.5.0",
        "textual>=0.38.0",
        "cryptography>=41.0.0",
    ],
    entry_points={
        "console_scripts": [
            "minitel-client=src.minitel.client:main",
            "minitel-replay=src.tui.replay:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
