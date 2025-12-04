# HABIT: H3 Aggregation-based Imputation Framework for Vessel Trajectories


HABIT Framework  provides a valuable means to impute the missing trajectory segments by extracting, analyzing, and indexing such patterns over historical AIS data.
HABIT provides  an efficient, data-driven and scalable approach for gap imputation relying on spatial aggregates of AIS positional reports computed over H3 hexagon cells. 

## Framework

HABIT is a data-driven and scalable approach for gap imputation in maritime trajectories relayed by vessels through the [Automatic Identification System (AIS)](https://www.imo.org/en/ourwork/safety/pages/ais.aspx). It relies on spatial aggregates of positional reports computed over [H3 hexagon cells](https://h3geo.org). It is built on top of open-source tools such as [DuckDB](https://duckdb.org) and [NetworkX](https://networkx.org/) and is comprised of four main phases:

- _Data preprocessing & trip segmentation_: Erroneous data is filtered out and raw positional reports are cleaned, analyzed and organized by trip.

- _Graph generation_: Position embeddings are computed using the spatial H3 index. The transitions between cells are first organized into  an edge list and then assembled into a graph.

- _Trajectory imputation_: A shortest-path algorithm is used to identify the points of the missing trajectory segments, leveraging graph statistics. Additionally, a data-driven method is applied to more accurately project between H3 cells and coordinates.

- _Trajectory simplification_:A smoothing process is applied to the imputed trajectory to generate a realistic and navigable path.


## Data preprocessing & trip segmentation

In the initial phase, we segment the entire trajectory of each vessel into separate _trips_ and perform a data cleaning process. In order for the trips to be identified, the AIS raw data is analyzed by considering several factors such as time, location, speed changes, and heading, thanks to our [AIS vessel trajectory annotation](https://github.com/M3-Archimedes/AIS-trajectory-annotation). By examining how the motion pattern (speed, heading) of a given vessel changes across time, this method can incrementally annotate selected positions that signify several types of mobility events (stops, gaps, turning points, slow motion, and speed change). 

In our approach, we consider as a _trip_ the subsequence of AIS locations between two successive stops or gaps:

- A _stop_ indicates that the vessel remains stationary, i.e., its speed is <0.5 knots over a period of time. The starting location of such a stop (most typically in a port, but sometimes also at sea) marks the end of the current trip. Conversely, the last location in a stop signifies that the vessel has just departed on a new trip.

- A _communication gap_ occurs when no AIS location has been received recently, e.g., in the past 30 minutes. If such a gap occurs, the current trip is abruptly ended and a new trip will be assigned once communication with the vessel is resumed. 

Assuming that original AIS data are stored in a CSV file (available in path ```RAW_AIS_FILE```) and the respective annotations are also in a CSV file (in path ```ANNOTATED_AIS_FILE```), our [trip segmentation module](src/trip_segmentation.py) can be invoked as follows in order to produce a pandas DataFrame with the identified trips: 

```
df_all_trips = dataset2trips(RAW_AIS_FILE, ANNOTATED_AIS_FILE, MIN_GAP_SIZE=3600)
```

where ```MIN_GAP_SIZE``` specifies the maximum allowed time interval (in seconds) with no positional report; if no signal is relayed for a period longer than this threshold (e.g., ```3600``` seconds, i.e., one hour in this example), a new trip will be assigned once communication with the vessel is resumed.

The assigned trip identifiers are concatenations of three components: the vessel's unique Maritime Mobile Service Identity (```MMSI```), the timestamp marking the start of the trip (UNIX epoch in seconds), and the the timestamp marking the end of the trip (also as UNIX epoch in seconds). For instance, identifier ```211178260_1706603252_1706624731``` concerns the trip of a vessel with MMSI ```211178260```, which started at 08:27:32 GMT on 30 January 2024 (epoch: ```1706603252```) and ended at 14:25:31 GMT the same day (epoch: ```1706624731```).


## Graph generation

TBC


## Trajectory imputation

TBC


## Trajectory simplification

TBC


## License

The contents of these repository are licensed under [GNU General Public License v3.0](https://github.com/M3-Archimedes/AIS-trajectory-annotation/blob/main/LICENSE).


