from setuptools import setup

setup(
    name='fgdb2postgis',
    version=__import__('fgdb2postgis').get_current_version(),
    description="""ESRI file geodatabase to PostGIS converter""",
    long_description=open('README.rst').read(),
    author='George Ioannou',
    author_email='gmioannou@cartologic.com',
    url='https://github.com/cartologic/fgdb2postgis',
    packages=['fgdb2postgis'],
    package_data={'fgdb2postgis': ['sql_files/*.sql']},
    include_package_data=True,
    install_requires=[
		'numpy>=1.18.1',
		'psycopg2>=2.8.5',
        'ruamel.yaml>=0.16.10',
        'awesome-slugify>=1.6.5'
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
