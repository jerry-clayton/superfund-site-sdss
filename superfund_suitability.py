import tkinter as tk
from tkinter import messagebox
import pandas as pd
import geopandas as gpd
import numpy as np
import copy
## Function to rescale scores to 1-100
def rescale_values(series):
    
    # Step 1: Compute min and max of the original range
    min_value = min(series)
    max_value = max(series)
    
    # Step 2: Apply the rescaling formula
    rescaled_values = [1 + (v - min_value) / (max_value - min_value) * 99 for v in series]
    
    return(rescaled_values)

class SDSS_GUI:
    def __init__(self, root, field_names):
        self.root = root
        self.root.title("NY-NJ Superfund Remediation SDSS")

        self.entries = []
        self.field_names = field_names

        for i, name in enumerate(self.field_names):
            label = tk.Label(root, text=f"{name}:")
            label.grid(row=i, column=0, padx=10, pady=5, sticky="e")

            entry = tk.Entry(root, validate="key")
            entry.grid(row=i, column=1, padx=10, pady=5)

            # Add validation
            entry['validatecommand'] = (root.register(self.validate_input), '%P')
            self.entries.append(entry)

        # Submit button
        submit_button = tk.Button(root, text="Submit", command=self.get_values)
        submit_button.grid(row=len(self.field_names), column=0, columnspan=2, pady=10)

    def validate_input(self, value):
        """Validate input to ensure it's a float or int."""
        if value == "":
            return False  # Disallow empty input
        try:
            float(value)  # Check if the input is a valid number
            return True
        except ValueError:
            return False

    def get_values(self):
        """Retrieve values from fields and pass to SDSS."""
        values = {}
        for i, entry in enumerate(self.entries):
            value = entry.get()
            if value.strip() == "":
                messagebox.showerror("Error", f"The field '{self.field_names[i]}' cannot be empty!")
                return
            values[self.field_names[i]] = float(value)
        
        self.runAHP(values)

    def runAHP(self, inputs):
        ## Units KM, convert to meters 
        NATURAL_AREAS_RADIUS = inputs.get('Natural Areas Radius (km)') * 1000
        SCHOOL_RADIUS = inputs.get('School Radius (km)') * 1000
        POP_RADIUS = inputs.get('Population Radius (km)') * 1000
        
        # weights between 0 and 1, should add to 1
        POP_WEIGHT = inputs.get('Population Weight')
        SCHOOL_WEIGHT = inputs.get('School Weight')
        NATURAL_WEIGHT = inputs.get('Natural Areas Weight')
        SEVERITY_WEIGHT = inputs.get('Severity Weight')
        
        # read input files 
        superfund_sites = gpd.read_file('input_layers/nynj_superfund_sites_with_scores_and_geoms.gpkg')
        natural_areas = gpd.read_file('input_layers/nynj_natural_areas.gpkg')
        bg_population = gpd.read_file('input_layers/block_group_population_and_geoms.gpkg')
        school_pts = gpd.read_file('input_layers/nynj_school_points.gpkg')

        #messagebox.showinfo('Progress', 'computing buffers')
        # Transform to UTM 11N for Buffers
        superfund_sites = superfund_sites.to_crs(26911)
        natural_areas = natural_areas.to_crs(26911)
        bg_population = bg_population.to_crs(26911)
        school_pts = school_pts.to_crs(26911)
        
        # Hudson River is an Outlier and needs removal
        superfund_sites = superfund_sites[superfund_sites['Site Name'] != 'Hudson River PCBs']
        
        # Worried about total natural area so dissolve polygons so no double-counting overlapping areas
        natural_areas = natural_areas.dissolve()
        
        # isolate the shape to intersect with
        natural_areas = natural_areas.iloc[0].geometry
        
        #print(NATURAL_AREAS_RADIUS)
        # Buffer the superfund sites according to the input radius
        # Then compute the intersection and save the total intersected area
        sites_nature_buffer = superfund_sites.buffer(NATURAL_AREAS_RADIUS)
        nature_intersection = sites_nature_buffer.intersection(natural_areas)
        superfund_sites['nature_int_area'] = nature_intersection.area
        
        # Now do population
        sites_pop_buffer = superfund_sites.buffer(POP_RADIUS)
        superfund_sites_pop_copy = copy.deepcopy(superfund_sites)
        superfund_sites_pop_copy['geometry'] = sites_pop_buffer
        
        # inner join to get every intersection for every block-group/superfund pair
        intersections = gpd.sjoin(superfund_sites_pop_copy, bg_population, how="inner", predicate="intersects")
        
        # compute total population at risk from each site and join back to original GDF
        intersections.POPULATION = intersections.POPULATION.astype(int)
        population_to_id = intersections.groupby('EPA_ID')['POPULATION'].sum().reset_index()
        superfund_sites = superfund_sites.merge(population_to_id, on='EPA_ID', how='left')
        
        # Now the schools
        schools_buffer = superfund_sites.buffer(SCHOOL_RADIUS)
        superfund_sites_schools_copy = copy.deepcopy(superfund_sites)
        superfund_sites_schools_copy['geometry'] = schools_buffer
        
        # Spatial join to find points within polygons then count the points in each superfund site radius and merge back to original GDF
        points_within_polygons = gpd.sjoin(school_pts, superfund_sites_schools_copy, how="inner", predicate="within")
        point_counts = points_within_polygons.groupby("EPA_ID").size().reset_index(name="school_count")
        superfund_sites = superfund_sites.merge(point_counts, on="EPA_ID", how="left").fillna(0)

        #messagebox.showinfo('Progress', 'ranking sites...')
        # Compute scores for each factor
        superfund_sites['nature_score'] = rescale_values(superfund_sites.nature_int_area)
        superfund_sites['pop_score'] = rescale_values(superfund_sites.POPULATION)
        superfund_sites['school_score'] = rescale_values(superfund_sites.school_count)
        superfund_sites['severity_score'] = rescale_values(superfund_sites['Site Score'])
        
        # Compute final score with user weights
        superfund_sites['final_score'] = np.sqrt(superfund_sites.nature_score * NATURAL_WEIGHT + superfund_sites.pop_score * POP_WEIGHT + superfund_sites.severity_score * SEVERITY_WEIGHT + superfund_sites.school_score * SCHOOL_WEIGHT)
        
        output_string = f'outputs/nat{NATURAL_AREAS_RADIUS/1000}_school{SCHOOL_RADIUS/1000}_pop{POP_RADIUS/1000}_weights_{POP_WEIGHT}_{SCHOOL_WEIGHT}_{NATURAL_WEIGHT}_{SEVERITY_WEIGHT}.gpkg'
        superfund_sites.to_file(output_string)
        messagebox.showinfo('Success', f'output saved to {output_string}')


# Define custom field names
field_names = ["Natural Areas Radius (km)", "School Radius (km)", "Population Radius (km)", "Population Weight", "School Weight", "Natural Areas Weight", "Severity Weight"]

# Create the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = SDSS_GUI(root, field_names)
    root.mainloop()