# -*- coding: utf-8 -*-
"""
Installs one binary:

    - ocrd-ocropy-segment
"""
import codecs

from setuptools import setup

setup(
    name='ocrd_ocropy',
    version='0.0.2',
    description='ocropy bindings',
    long_description=codecs.open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    author='Konstantin Baierer',
    author_email='unixprog@gmail.com, wuerzner@gmail.com',
    url='https://github.com/OCR-D/ocrd_ocropy',
    license='Apache License 2.0',
    packages=['ocrd_ocropy'],
    install_requires=[
        'ocrd >= 1.0.0a4',
        'ocrd-fork-ocropy >= 1.4.0a3',
        'click'
    ],
    package_data={
        '': ['*.json', '*.yml', '*.yaml'],
    },
    entry_points={
        'console_scripts': [
            'ocrd-ocropy-segment=ocrd_ocropy.cli:ocrd_ocropy_segment',
        ]
    },
)
