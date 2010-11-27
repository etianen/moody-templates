#!/usr/bin/env python3

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages


setup(
    name="Moody Templates",
    version="1.0",
    description="",
    author="Dave Hall",
    author_email="dave@etianen.com",
    url="http://github.com/etianen/django-reversion",
    download_url="http://github.com/downloads/etianen/django-reversion/django-reversion-1.3.2.tar.gz",
    zip_safe=False,
    packages=find_packages("src"),
    package_dir={"": "src"},
    test_suite="moody.tests",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ]
)