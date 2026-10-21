# -*- coding: utf-8 -*-
from setuptools import setup, find_namespace_packages
import os
from pyscada import thread as pyscada_app


CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Environment :: Web Environment",
    "Environment :: Console",
    "Framework :: Django",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "Operating System :: POSIX",
    "Programming Language :: Python",
    "Topic :: Scientific/Engineering :: Visualization",
]
setup(
    author=pyscada_app.__author__,
    author_email=pyscada_app.__email__,
    name="pyscada-" + pyscada_app.__app_name__.lower(),
    version=pyscada_app.__version__,
    description=pyscada_app.__description__,
    long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    long_description_content_type="text/markdown",
    url="https://github.com/LucasVvn/pyscada-thread",
    license="AGPLv3",
    platforms=["OS Independent"],
    classifiers=CLASSIFIERS,
    install_requires=[
        "pyscada>=0.8.0",
        "aiocoap>=0.4.7",
    ],
    packages=find_namespace_packages(exclude=["project", "project.*", "tests", "tests.*", "examples", "examples.*"]),
    include_package_data=True,
    zip_safe=False,
)
