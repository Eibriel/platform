"""
Eibriel Platfor for Conversational Experiences
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='python-eibrielplatform-flask',
    version='1.0.0',
    description='Eibriel Platfor for Conversational Experiences',
    long_description=long_description,
    url='https://github.com/Eibriel/platform',
    license='GNU General Public License v3.0'
)