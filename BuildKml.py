"""
Created on 29 juill. 2019

@author: david.larochelle
"""

import sys
import getopt
import os
from tkinter import filedialog
from KML import KML

if __name__ == "__main__":
    pass

# default value
min_distance = 2000
input_paths = ""
kml_file_name = ""

# If executed from command line, accept -d option to override MinDistance
try:
    opts, args = getopt.getopt(sys.argv[1:], "hd:i:o:")
except getopt.GetoptError:
    print("test.py -d MinDistance -i InputPathsCommaSeparated -o OutputFile")
    sys.exit(2)
for opt, arg in opts:
    if opt == "-h":
        print("test.py -d MinDistance -i InputPathsCommaSeparated -o OutputFile")
        sys.exit()
    elif opt in ("-d"):
        min_distance = int(arg)
    elif opt in ("-i"):
        input_paths = str(arg)
    elif opt in ("-o"):
        kml_file_name = str(arg)
print("Min Distance is " + str(min_distance) + " Meters.")


# Create KML object
my_kml = KML("Unnamed")

# Build a list of folders to scan if not provided on command line
folder_list = []
if input_paths == "":
    while True:
        foldername = filedialog.askdirectory(
            title="Choose Folders to scan for picture files. Cancel when done."
        )
        if foldername == "":
            break
        folder_list.append(foldername)
else:
    # Split InputPaths
    folder_list = input_paths.split(";")

if len(folder_list) == 0:
    # Canceled by user
    sys.exit()

# Scan all selected foders for image files with GPS info
nb_files = 0
for foldername in folder_list:
    print("Scanning files in folder " + foldername + " ...")
    nb_files += my_kml.scan_folder(folder=foldername)

print("Imported " + str(nb_files) + " files from folders.")

if nb_files == 0:
    # Canceled by user
    print("No GPS info found in folder. Aborting.")
    sys.exit()

# FilteredQty = my_kml.FilterPlacemarks(min_distance)
my_kml.min_distance_between_placemarks = min_distance

# Export KML file
if kml_file_name == "":
    kml_file_name = filedialog.asksaveasfilename(
        title="Select KML output file", filetypes={("KML files", "*.kml")}
    )
file, ext = os.path.splitext(kml_file_name)

if kml_file_name == "":
    # Canceled by user
    print("No KML file provided. Aborting.")
    sys.exit()

# enforce kml extension
if ext.lower() != ".kml":
    kml_file_name = file + ".kml"

_, my_kml.map_name = os.path.split(kml_file_name)
my_kml.min_distance_between_placemarks = min_distance
file_saved = my_kml.save_kml_file(kml_file_name)
print(kml_file_name + " exported successfully.")
