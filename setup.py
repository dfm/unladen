#!/usr/bin/env python

from pathlib import Path

from setuptools import find_packages, setup

NAME = "unladen"
PACKAGES = find_packages(where="src")
CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
]
INSTALL_REQUIRES = ["click", "toml", "packaging"]
EXTRA_REQUIRE = {
    "docs": ["sphinx>=1.7.5", "myst-nb"],
    "test": ["pytest"],
    "lint": ["mypy", "pre-commit"],
}


def get_long_description() -> str:
    return (Path(__file__).parent / "README.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    setup(
        name=NAME,
        use_scm_version={
            "write_to": "src/unladen/unladen_version.py",
            "write_to_template": 'version = "{version}"\n',
        },
        author="Dan Foreman-Mackey",
        author_email="foreman.mackey@gmail.com",
        url="https://github.com/dfm/unladen",
        license="MIT",
        description="Language agnostic documentation versions",
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        packages=PACKAGES,
        package_dir={"": "src"},
        package_data={"unladen": ["py.typed"]},
        include_package_data=True,
        python_requires=">=3.7",
        install_requires=INSTALL_REQUIRES,
        extras_require=EXTRA_REQUIRE,
        classifiers=CLASSIFIERS,
        zip_safe=False,
        entry_points={"console_scripts": ["unladen=unladen:main"]},
    )
