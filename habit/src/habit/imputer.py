import duckdb
import networkx as nx

import h3.api.numpy_int as h3
from shapely import geometry
from scipy.spatial import cKDTree

class HabitImputer:
    """
        Habit Imputer loads a dataset calculates aggregates on h3 cells using duckdb and then user calls the fill_gap function to 
    """
       

    def __init__(self,resolution=9,max_gap=25,schema={"id":"MMSI","lon":"LON","lat":"LAT","t":"TIMESTAMP","sog":"SPEED","cog":"COURSE","trip":"TRIP"},excluded=[]):

        self.resolution = resolution
        self.max_gap = max_gap
        self.path= None
        self.query = None
        self.btree= None
        self.G = None
        self.excluded = excluded
        self.id = schema["id"]
        self.lat= schema["lat"]
        self.lon = schema["lon"]
        self.t = schema["t"]
        self.sog = schema["sog"]
        self.cog = schema["cog"]
        self.trip = schema.get("trip",self.id)
        
    def prepare_query(self):
        """Prepates the final query """

        where_clause = "" if len(self.excluded) == 0 else  f'where {self.id} not in ( {",".join(self.excluded)} )'
        
        query=f"""
                with
                    cte as (
                        select *, h3_latlng_to_cell({self.lat},{self.lon},{self.resolution}::INT) as h3 from read_csv('{self.path}'::STRING){where_clause} order by {self.t},{self.id} ASC),
                    tt as (
                        select *,lag(h3) over (partition by {self.id} order by {self.t}) lag_h3 from cte)
                    select 
                        CAST(lag_h3 AS BIGINT) lag_h3, 
                        CAST(h3 AS BIGINT) h3,  
                        count() messages, 
                        approx_count_distinct({self.id}) vessels, 
                        approx_quantile({self.sog},0.5) sog, 
                        approx_quantile({self.cog},0.5) cog, 
                        approx_count_distinct({self.trip}) transitions,
                        approx_quantile({self.lat},0.5) mlat, 
                        approx_quantile({self.lon},0.5) mlon,
                        h3_grid_distance(lag_h3,h3) distance,
                        'LINESTRING ('||list_aggregate(list_reverse(h3_cell_to_latlng(lag_h3)), 'string_agg', ' ') ||', '|| list_aggregate(list_reverse( h3_cell_to_latlng(h3)),'string_agg',' ') ||')' wkt
                    from tt 
                        where 
                        lag_h3 is not null 
                        and h3 is not null 
                        and {self.cog} is not null
                    group by 
                        lag_h3,h3
                """.replace("\n", " ").strip()
        return(query)
    
    def data_load(self,path):
        """
            Load data and into duckdb, calculate statistics and transform them into a graph. it calculates a btree for fast nn search during imputation
        """
        self.path = path
        self.query=self.prepare_query()
        self.G = nx.Graph()

        duckdb.sql("INSTALL h3 FROM community;LOAD h3;SET memory_limit = '60GB';")
        df=duckdb.sql(self.query).df()
            
        nodes = set(df.h3.astype('int64').to_list()+ df.lag_h3.astype('int64').to_list())
        edges =  df[df.distance < self.max_gap][["lag_h3","h3","transitions","cog"]].astype('int64').values

        for n in nodes: 
            p1=h3.cell_to_latlng(n)[::-1]

            filtered = df[df.h3.astype('int64') == n]
            
            if len(filtered) > 0:
                mlon = filtered["mlon"].iloc[0]
                mlat = filtered["mlat"].iloc[0]
            else:
                mlon = p1[0]
                mlat = p1[1]
                
                
            self.G.add_node(n,location=p1,mlon=mlon,mlat=mlat)

        for (u,v,weight,cog) in edges:
            self.G.add_edge(u,v,weight=(100.0-min(weight,100.0))/100.0,cog=cog)
            # self.G.add_edge(u,v,weight=weight,cog=cog)

        pos = [self.G.nodes[n]['location'] for n in self.G.nodes()]
        self.btree=cKDTree(pos)

    def get_edge_list(self):
        """
            Returns the edge list of the graph
        """
        return [(u,v,data['weight'],data['cog']) for u,v,data in self.G.edges(data=True)]

    def cells_to_linestring(self,cells):
        """
            Transforms a list of h3 cells into a linestring using its centroids
        """
        points=[h3.cell_to_latlng(p)[::-1] for p in list(cells)]
        if len(cells)<2: #if one point no linestring can be generated
            points.append(points[0])
        
        return geometry.LineString(points)

    def cells_to_linestring_weighted(self,cells):
        """
            Transforms a list of h3 cells into a linestring using its centroids
        """

        points = []

        for c in list(cells):
            points.append([self.G.nodes[c]['mlon'],self.G.nodes[c]['mlat']])


        if len(cells)<2: #if one point no linestring can be generated
            points.append(points[0])
        
        return geometry.LineString(points)

    def get_cell_path(self,origin_lon,origin_lat,destination_lon,destination_lat):
        """
            Given a the graph, has been loaded , use  and origin and destination location to find the nearest starting and end
        """
       
        RES = h3.get_resolution(list(self.G.nodes())[0])

        origin = h3.latlng_to_cell(origin_lat,origin_lon,RES)
        nn_origin =origin
        if origin not in self.G.nodes():
            dist,ix = self.btree.query(h3.cell_to_latlng(origin)[::-1],1)
            nn_origin = list(self.G.nodes())[ix]



        destination = h3.latlng_to_cell(destination_lat,destination_lon,RES)
        nn_destination = destination
        if destination not in self.G.nodes():
            dist,ix = self.btree.query(h3.cell_to_latlng(origin)[::-1],1)
            nn_destination = list(self.G.nodes())[ix]

        cells = nx.astar_path(self.G,nn_origin,nn_destination)

        if nn_origin!=origin:
            cells=cells+[origin]
      
        if nn_destination!=destination:
            cells= cells+[destination]

        return(cells)
        

    def fill_gap(self,origin_lon,origin_lat,destination_lon,destination_lat):
        """
            Given a the graph, has been loaded , use  and origin and destination location to find the nearest starting and end
        """
       
        cells = self.get_cell_path(origin_lon,origin_lat,destination_lon,destination_lat)

        linestring = self.cells_to_linestring(cells)
        return (linestring)

    def fill_gap_weighted(self,origin_lon,origin_lat,destination_lon,destination_lat):
        """
            Given a the graph, has been loaded , use  and origin and destination location to find the nearest starting and end
        """
       
        cells = self.get_cell_path(origin_lon,origin_lat,destination_lon,destination_lat)

        linestring = self.cells_to_linestring_weighted(cells)
        return (linestring)