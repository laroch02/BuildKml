'''
Created on 29 juill. 2019

@author: david.larochelle
'''

import sys
import getopt
import os
from tkinter import filedialog
from KML import KML
if __name__ == '__main__':
    pass

# default value
MinDistance = 2000
InputPaths = ""
KMLFileName = ""

# If executed from command line, accept -d option to override MinDistance
try:
    opts, args = getopt.getopt(sys.argv[1:], "hd:i:o:")
except getopt.GetoptError:
    print('test.py -d MinDistance -i InputPathsCommaSeparated -o OutputFile')
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print('test.py -d MinDistance -i InputPathsCommaSeparated -o OutputFile')
        sys.exit()
    elif opt in ("-d"):
        MinDistance = int(arg)
    elif opt in ("-i"):
        InputPaths = str(arg)
    elif opt in ("-o"):
        KMLFileName = str(arg)
print ('Min Distance is ' + str(MinDistance) + " Meters.")


# Create KML object
MyKML = KML("Unnamed")

# Build a list of folders to scan if not provided on command line
FolderList = []
if (InputPaths == ""):
    while True:
        Foldername = filedialog.askdirectory(title="Choose Folders to scan for picture files. Cancel when done.")
        if (Foldername == ""):
            break
        FolderList.append(Foldername)
else:
    # Split InputPaths
    FolderList = InputPaths.split(";")
    
if (len(FolderList) == 0):
    # Canceled by user
    sys.exit()

# Scan all selected foders for image files with GPS info
NbFiles = 0
for Foldername in FolderList:
    print ("Scanning files in folder " + Foldername + " ...")
    NbFiles += MyKML.ScanFolder(Folder=Foldername)

print ("Imported " + str(NbFiles) + " files from folders.")

if (NbFiles == 0):
    # Canceled by user
    print("No GPS info found in folder. Aborting.")
    sys.exit()
    
# FilteredQty = MyKML.FilterPlacemarks(MinDistance)
MyKML.MinDistanceBetweenPlacemarks = MinDistance

# Export KML file
if (KMLFileName == ""):
    KMLFileName = filedialog.asksaveasfilename(title="Select KML output file", filetypes={("KML files", "*.kml")})
file, ext = os.path.splitext(KMLFileName)

if (KMLFileName == ""):
    # Canceled by user
    print("No KML file provided. Aborting.")
    sys.exit()
    
# enforce kml extension
if (ext.lower() != ".kml"):
    KMLFileName = file + ".kml"

_ , MyKML.MapName = os.path.split(KMLFileName)
MyKML.MinDistanceBetweenPlacemark = MinDistance
FileSaved = MyKML.SaveKMLFile(KMLFileName)
print(KMLFileName + " exported successfully.")
