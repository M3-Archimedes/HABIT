from setuptools import setup, find_packages

setup(
    name='habit',
    version='0.1',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[
        'shapely',
        'networkx',
        'h3',
        'geopandas',
        'folium',
        'duckdb',
        'numpy',        # Pinned version as requested
        'scikit-learn',  # Pinned version as requested
        'seaborn',
        'setuptools',
        'matplotlib',
        'rtree',
    ],
    author='Giannis Spiliopoulos, Alexandros Troupiotis-Kapeliaris, Kostas Patroumpas,Nikolaos Liapis, Dimitrios Skoutas, Dimitris Zissis, Nikos Bikakis',
    description='An H3 Aggregation-Based Imputation (HABIT)that relies on H3 spatial index and graph algorithms to impute missing trajectory data.',
)