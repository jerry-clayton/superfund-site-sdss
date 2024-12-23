### NY-NJ Superfund Suitability SDSS Usage Guide

1. Create a new directory for the tool
2. Unzip the archive and ensure that superfund_suitability.py is one directory level above two folders: input_layers and outputs
3. Ensure input_layers has 4 gpkgs inside
4. Create a new conda environment for the tool, and install the following packages:

   a. tkinter
   
   b. pandas
   
   c. geopandas
   
   d. numpy 
6. run the tool with `python superfund_suitability.py`


### Running the tool

Values must be input for each of the seven fields. Only integers and floats area accepted. The three radii are input in kilometers, while the four weights are input as decimal fractions. The four weights should sum to 1. Leading 0s must be included for the four weights: type '0.1' instead of '.1'. 0 is an acceptable value in all fields, but will of course result in the corresponding factor not being included in the calculation. 

The output of the tool is a geopackage, which will be saved in 'outputs', with a file name that includes all seven weights. The quickest way to view the results is by reading the geopackage in a jupyter notebook with geopandas, and using the `.explore()` method of the GeoDataFrame and passing the `'final_score'` column as a parameter, like this: 

`import geopandas as gpd`

`scene1 = gpd.read_file('outputs/nat5_school2_pop3_weights_0.3_0.2_0.1_0.4.gpkg')`

`scene1.explore(column='final_score')`
