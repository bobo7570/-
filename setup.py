from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="app_auto_tool",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A mobile app automation testing tool based on Appium",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/app-auto-tool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "app-auto-tool=app_auto_tool.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app_auto_tool": [
            "resources/*",
            "resources/icons/*",
            "config/*",
        ],
    },
    data_files=[
        ("", ["LICENSE", "README.md", "requirements.txt"]),
    ],
) 