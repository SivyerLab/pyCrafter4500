from distutils.core import setup

setup(
    name = 'pycrafter4500',
    packages = ['pycrafter4500'], # this must be the same as the name above
    version = '0.4',
    description = 'A python interface to communicate over USB with the TI Lightcrafter 4500',
    author = 'Alexander Tomlinson',
    author_email = 'tomlinsa@ohsu.eud',
    url = 'https://github.com/SivyerLab/pyCrafter4500',
    download_url = 'https://github.com/SivyerLab/pyCrafter4500/archive/0.4.tar.gz',
    keywords = 'lightcrafter 4500 dlpc 350 projector texas',
    install_requires=[
        'pyusb'
    ],
    license='MIT',
)