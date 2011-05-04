#!/usr/bin/env python3

import sys, os.path
sys.path.append(os.path.dirname(__file__))

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages


setup(
    name="moody-templates",
    version="0.9",
    description="",
    author="Dave Hall",
    author_email="dave@etianen.com",
    url="http://github.com/etianen/moody-templates",
    download_url="http://github.com/downloads/etianen/moody-templates/moody-templates-0.9.tar.gz",
    packages=find_packages("src"),
    package_dir={"": "src"},
    test_suite="moody.tests",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ]
)