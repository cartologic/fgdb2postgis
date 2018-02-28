from pip.req import parse_requirements
from setuptools import setup

setup(
    name='fgdb2postgis',
    version='0.2.9',
    description="""ESRI file geodatabase to PostGIS converter""",
    long_description=open('README.rst').read(),
    author='George Ioannou',
    author_email='gmioannou@cartologic.com',
    url='https://github.com/cartologic/fgdb2postgis',
    packages=['fgdb2postgis'],
    package_data={'fgdb2postgis': ['sql_files/*.sql']},
    include_package_data=True,
    install_requires=[
		'numpy>=1.12.0',
		'psycopg2>=2.6.2',
        'ruamel.yaml>=0.15.35',
		'archook==1.1.0',
    ],
    license="GNU",
    keywords='fgdb2postgis',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: GIS',
        'Operating System :: Microsoft :: Windows'
    ],
    entry_points={
        'console_scripts': ['fgdb2postgis = fgdb2postgis.__main__:main']
    },
)
