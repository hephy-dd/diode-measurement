from setuptools import setup, find_packages

setup(
    name='diode-measurement',
    version='0.6.1',
    author="Bernhard Arnold",
    author_email="bernhard.arnold@oeaw.ac.at",
    url="https://github.com/hephy-dd/diode-measurement",
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'PyQt5==5.15.*',
        'PyQtChart==5.15.*',
        'PyVISA==1.11.*',
        'PyVISA-py==0.5.*',
        'pint==0.17.*'
    ],
    package_data={},
    entry_points={
        'console_scripts': [
            'diode-measurement = diode_measurement.__main__:main'
        ]
    },
    test_suite='tests',
    license='GPLv3'
)
