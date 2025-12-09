# HABIT: H3 Aggregation-based Imputation Framework for Vessel Trajectories


HABIT Framework  provides a valuable means to impute the missing trajectory segments by extracting, analyzing, and indexing such patterns over historical AIS data.
HABIT provides  an efficient, data-driven and scalable approach for gap imputation relying on spatial aggregates of AIS positional reports computed over H3 hexagon cells. 
## Installation 

Pre-requisites:
```
! pip install shapely networkx h3 geopandas folium duckdb numpy==1.26.4 scikit-learn==1.6.1 seaborn setuptools matplotlib rtree ipykernel
! cd ../habit; pip install -e .
```
If you are running this through a notebook, you might need to restart kernel to load changes.

*Please find a working example in the notebooks folder* 

## Framework

HABIT is a data-driven and scalable approach for gap imputation in maritime trajectories relayed by vessels through the [Automatic Identification System (AIS)](https://www.imo.org/en/ourwork/safety/pages/ais.aspx). It relies on spatial aggregates of positional reports computed over [H3 hexagon cells](https://h3geo.org). It is built on top of open-source tools such as [DuckDB](https://duckdb.org) and [NetworkX](https://networkx.org/) and is comprised of four main phases:

- _Data preprocessing & trip segmentation_: Erroneous data is filtered out and raw positional reports are cleaned, analyzed and organized by trip.

- _Graph generation_: Position embeddings are computed using the spatial H3 index. The transitions between cells are first organized into  an edge list and then assembled into a graph.

- _Trajectory imputation_: A shortest-path algorithm is used to identify the points of the missing trajectory segments, leveraging graph statistics. Additionally, a data-driven method is applied to more accurately project between H3 cells and coordinates.

- _Trajectory simplification_:A smoothing process is applied to the imputed trajectory to generate a realistic and navigable path.



## License

The contents of these repository are licensed under [GNU General Public License v3.0](https://github.com/M3-Archimedes/AIS-trajectory-annotation/blob/main/LICENSE).


