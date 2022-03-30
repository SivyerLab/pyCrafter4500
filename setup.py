from setuptools import setup
from pathlib import Path

README = Path('README.md').read_text()

setup(
    name='pycrafter4500',
    version='0.7',
    packages=['pycrafter4500'],
    install_requires=['pyusb'],

    # pypi metadata
    author='Alexander Tomlinson',
    author_email='tomlinsa@ohsu.edu',
    description='A python interface to communicate over USB with the TI Lightcrafter 4500',
    long_description=README,
    long_description_content_type="text/markdown",
    keywords='lightcrafter 4500 dlpc 350 projector texas',
    url='https://pycrafter4500.readthedocs.io/en/latest/',
    project_urls={
        "Source Code": 'https://github.com/SivyerLab/pyCrafter4500',
    },
    license='GPL',
)
