# -*- coding: utf-8 -*-
"""
Installs one binary:

    - ocrd-ocropy-gpageseg
"""
import codecs

from setuptools import setup

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
    packages=['ocrd_ocropy'],
    install_requires=open('requirements.txt').read().split('\n'),
    package_data={
        '': ['*.json', '*.yml', '*.yaml'],
    },
    entry_points={
        'console_scripts': [
            'ocrd-ocropy-segment=ocrd_ocropy.cli:ocrd_ocropy_segment',
        ]
    },
)
