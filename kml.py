"""
Created on 29 juill. 2019

@author: david.larochelle
"""

import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom
import exifread


class Kml:
    """
    Kml Class is created to handle scanning of multiple image files in multiple folders and ultimately export a Kml file compatible
    with Google Maps import.
    For large number of placemarks, a minimum distance can be specified so close placemarks from one another will not be exported.
    """

    # Member variables
    map_name = ""
    map_description = ""
    _placemark_list = []
    _placemark_list_is_ordered = False
    min_distance_between_placemarks_in_meters = 0  # minimum distance there as to be from previous point for current placemark to be exported.

    def __init__(self, map_name: str):
        """
        Constructor
        """
        self.map_name = map_name

    def __repr__(self):
        return f"KML({self.map_name})"

    def __str__(self):
        return "This is My KML : " + self.map_name

    def scan_folder(self, folder: str):
        """
        Scans folders recursively to build a list of compatible image files,
        extract exif data and returns the number of imported files (that had gps information).
        :param folder: (string)
        :rtype: int
        """
        # Get list of files
        base_folder = Path(folder)
        file_types = ("*.jpg", "*.jpeg", "*.dng")
        file_list = []
        for file_type in file_types:
            file_list.extend(
                base_folder.glob("**/" + file_type)
            )  # # ** allows to parse forlder recursively
        
        # exclude files beginning with ._
        file_list = [f for f in file_list if not f.name.startswith("._")]

        # import os
        nb_files = 0
        index = 0
        for my_file in file_list:
            # print the index of the file being processed
            index += 1
            print("\tProcessing file: " + str(index) + "/" + str(len(file_list)), end="\r")
            try:
                tags = exifread.process_file(open(str(my_file), "rb"))
            except (IOError, OSError):# as e:
                #print(f"\tCould not read exif from file {my_file}: {e}")
                continue

            try:
                my_lat = self._convert_to_degress(tags["GPS GPSLatitude"])
                if tags["GPS GPSLatitudeRef"].values[0] != "N":
                    my_lat = -my_lat
                my_lon = self._convert_to_degress(tags["GPS GPSLongitude"])
                if tags["GPS GPSLongitudeRef"].values[0] != "E":
                    my_lon = -my_lon
                # FilePath , FileName = os.path.split(my_file)
                # BasePath, FirstFolder = os.path.split(FilePath)
                self._add_placemark(my_lat, my_lon, str(my_file), folder)
                nb_files += 1

            except (KeyError, AttributeError, IndexError):# as e:
                #print(f"\tCould not extract GPS info from file {my_file}: {e}")
                continue

        #print(str(nb_files) + "/" + str(len(file_list)) + " files have coordinates in folder " + folder)
        return nb_files

    def _add_placemark(
        self, latitude: float, longitude: float, name: str = "", folder: str = ""
    ):
        self._placemark_list.append(
            {
                "Latitude": latitude,
                "Longitude": longitude,
                "Name": name,
                "Folder": folder,
            }
        )

    def _get_kml_string(self):
        # create the file structure
        root = ET.Element("kml")
        root.set("xmlns", "http://www.opengis.net/kml/2.2")
        document = ET.SubElement(root, "Document")
        name = ET.SubElement(document, "name")
        name.text = self.map_name
        description = ET.SubElement(document, "description")
        description.text = self.map_description

        # Sort List prior to export
        self._reorder_placemarks()

        # Create first folder element
        folder = ET.SubElement(document, "Folder")
        folder_name = ET.SubElement(folder, "name")
        folder_name.text = self._placemark_list[0]["Folder"]

        nb_files_to_export = 0
        for my_coord in self._placemark_list:
            if my_coord["Folder"] != folder_name.text:
                # Create new folder if different
                folder = ET.SubElement(document, "Folder")
                folder_name = ET.SubElement(folder, "name")
                folder_name.text = my_coord["Folder"]

            if my_coord["Export"]:
                my_placemark = ET.SubElement(folder, "Placemark")
                if my_coord["Name"] != "":
                    file_path, file_name = os.path.split(my_coord["Name"])
                    my_name = ET.SubElement(my_placemark, "name")
                    my_name.text = file_name
                    my_desc = ET.SubElement(my_placemark, "description")
                    my_desc.text = file_path

                my_point = ET.SubElement(my_placemark, "Point")
                my_coordinate = ET.SubElement(my_point, "coordinates")
                my_coordinate.text = (
                    str(my_coord["Longitude"]) + "," + str(my_coord["Latitude"])
                )
                nb_files_to_export += 1

        print(str(nb_files_to_export) + " placemarks exported to KML.")

        # create a new XML file with the results
        xml_string = ET.tostring(root, encoding="unicode")
        try:
            xml_string = minidom.parseString(xml_string).toprettyxml()
        except (ValueError, TypeError) as e:
            print(f"Problems converting to Pretty XML (minidom): {e}")
        return xml_string

    def save_kml_file(self, path: str):
        """
        Saves the KML data to a file.
        :param path: The file path where the KML will be saved
        :return: True if successful, False otherwise
        """
        kml_string = self._get_kml_string()
        try:
            with open(path, "w", encoding="utf-8") as my_file:
                my_file.write(kml_string)
        except (IOError, OSError) as e:
            print(f"\tCould not save KML file: {e}")
            return False

        return True

    def _reorder_placemarks(self):
        """
        Sorts list based on Folder and latitude
        """
        # Sort List in order to calculate distance between points.
        self._placemark_list = sorted(
            self._placemark_list, key=lambda i: (i["Folder"], i["Latitude"])
        )
        self._filter_placemarks()  # recalculate placemarks to be exported

    def _filter_placemarks(self):
        """
        Functions that will sort Placemark list and tag each placemark to be exported based on the MinDistance parameter.
        pMinDistance : distance in meters
        """

        print(
            "\tMin Distance Between Placemarks set to "
            + str(self.min_distance_between_placemarks_in_meters)
            + " meters."
        )

        kept_coords = []

        export_count = 0
        for my_coord in self._placemark_list:
            my_coord["Export"] = True
            for kept_coord in kept_coords:
                if (
                    self._distance_between_placemarks(
                        my_coord["Latitude"],
                        my_coord["Longitude"],
                        kept_coord["Latitude"],
                        kept_coord["Longitude"],
                    )
                    < self.min_distance_between_placemarks_in_meters
                ):
                    my_coord["Export"] = False
                    break

            if my_coord["Export"] is True:
                export_count += 1
                kept_coords.append(my_coord)

        print(
            "\t"
            + str(export_count)
            + " placemarks marked to export out of "
            + str(len(self._placemark_list))
        )
        return export_count

    def _convert_to_degress(self, ratio) -> float:
        """
        Helper function to convert the GPS coordinates stored in the EXIF to degress in float format
        :param value:
        :type value: exifread.utils.Ratio
        :rtype: float
        """
        d = float(ratio.values[0].num) / float(ratio.values[0].den)
        m = float(ratio.values[1].num) / float(ratio.values[1].den)
        s = float(ratio.values[2].num) / float(ratio.values[2].den)

        return d + (m / 60.0) + (s / 3600.0)

    def _distance_between_placemarks(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ):
        radius = 6378.137  # // Radius of earth in KM
        d_lat = lat2 * math.pi / 180 - lat1 * math.pi / 180
        d_lon = lon2 * math.pi / 180 - lon1 * math.pi / 180
        a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + math.cos(
            lat1 * math.pi / 180
        ) * math.cos(lat2 * math.pi / 180) * math.sin(d_lon / 2) * math.sin(d_lon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = radius * c
        return d * 1000  # // meters
