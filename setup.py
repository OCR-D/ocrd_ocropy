# -*- coding: utf-8 -*-
"""
Installs one binary:

    - ocrd-ocropy-gpageseg
"""
import codecs

from setuptools import setup, find_packages

with codecs.open('README.rst', encoding='utf-8') as f:
    README = f.read()

setup(
    name='ocrd_ocropy',
    version='0.0.1',
    description='ocropy bindings',
    long_description=README,
    author='Konstantin Baierer',
    author_email='unixprog@gmail.com, wuerzner@gmail.com',
    url='https://github.com/OCR-D/ocrd_ocropy',
    license='Apache License 2.0',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'ocrd >= 0.2.2',
        'ocrd-fork-ocropy >= v1.3.3.post2',
        'click',
    ],
    package_data={
        '': ['*.json', '*.yml', '*.yaml'],
    },
    entry_points={
        'console_scripts': [
            'ocrd-ocropy-gpageseg=ocrd_ocropy.cli:ocrd_ocropy_gpageseg',
        ]
    },
)
