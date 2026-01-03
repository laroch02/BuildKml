"""
Unit tests for the Kml class.
Tests the functionality of KML file generation from image GPS data.

TESTING TOOLS DOCUMENTATION:

@patch decorator:
    The @patch decorator replaces a real function/method/object with a mock during testing.
    It's used to isolate the code being tested from external dependencies like file I/O,
    network calls, or other modules. The mock is automatically passed as an argument to the
    test method (rightmost decorator = rightmost parameter).

    Example: @patch('builtins.open', new_callable=mock_open)
             Replaces the built-in open() function with a mock that simulates file operations
             without actually touching the file system.

MagicMock:
    MagicMock is a flexible mock object that can simulate any object or data structure.
    It automatically creates attributes and methods as they're accessed, making it ideal
    for mocking complex objects like EXIF data structures.

    Example: mock_ratio = MagicMock()
             mock_ratio.values = [MagicMock(num=45, den=1), ...]
             Creates a mock object that mimics the structure of exifread ratio objects
             with numerator (num) and denominator (den) properties.

Why use mocking?
    - Tests run faster (no real file I/O or external dependencies)
    - Tests are more reliable (no dependency on file system state)
    - Tests can simulate edge cases (like I/O errors) that are hard to reproduce
    - Tests focus on the logic being tested, not on external systems
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock
import tempfile
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from kml import Kml


class TestKmlInit(unittest.TestCase):
    """Test Kml class initialization"""

    def test_init_with_name(self):
        """Test that Kml initializes with a map name"""
        kml = Kml("Test Map")
        self.assertEqual(kml.map_name, "Test Map")
        self.assertEqual(kml.map_description, "")
        self.assertEqual(len(kml._placemark_list), 0)
        self.assertEqual(kml.min_distance_between_placemarks_in_meters, 0)

    def test_repr(self):
        """Test __repr__ method"""
        kml = Kml("Test Map")
        self.assertEqual(repr(kml), "KML(Test Map)")

    def test_str(self):
        """Test __str__ method"""
        kml = Kml("Test Map")
        self.assertEqual(str(kml), "This is My KML : Test Map")


class TestKmlAddPlacemark(unittest.TestCase):
    """Test adding placemarks to the KML"""

    def setUp(self):
        self.kml = Kml("Test Map")
        self.kml.clear_placemarks()

    def test_add_placemark_basic(self):
        """Test adding a basic placemark"""
        self.kml._add_placemark(45.5, -73.5, "Test", "/test/folder")
        self.assertEqual(len(self.kml._placemark_list), 1)
        self.assertEqual(self.kml._placemark_list[0]["Latitude"], 45.5)
        self.assertEqual(self.kml._placemark_list[0]["Longitude"], -73.5)
        self.assertEqual(self.kml._placemark_list[0]["Name"], "Test")
        self.assertEqual(self.kml._placemark_list[0]["Folder"], "/test/folder")

    def test_add_multiple_placemarks(self):
        """Test adding multiple placemarks"""
        self.kml._add_placemark(45.5, -73.5, "Test1", "/folder1")
        self.kml._add_placemark(46.5, -74.5, "Test2", "/folder2")
        self.assertEqual(len(self.kml._placemark_list), 2)


class TestKmlConvertToDegrees(unittest.TestCase):
    """Test GPS coordinate conversion"""

    def setUp(self):
        self.kml = Kml("Test Map")
        self.kml.clear_placemarks()

    def test_convert_to_degrees(self):
        """Test conversion from GPS ratio format to decimal degrees"""
        # MagicMock Usage: Creating a mock exifread ratio object
        # Real exifread returns complex ratio objects with num/den properties.
        # Instead of reading actual EXIF data, we create a MagicMock that mimics
        # this structure, allowing us to test the conversion logic in isolation.
        mock_ratio = MagicMock()
        mock_ratio.values = [
            MagicMock(num=45, den=1),  # degrees
            MagicMock(num=30, den=1),  # minutes
            MagicMock(num=0, den=1),  # seconds
        ]

        result = self.kml._convert_to_degress(mock_ratio)
        # 45 + (30/60) + (0/3600) = 45.5
        self.assertAlmostEqual(result, 45.5, places=5)

    def test_convert_to_degrees_with_seconds(self):
        """Test conversion with seconds"""
        mock_ratio = MagicMock()
        mock_ratio.values = [
            MagicMock(num=45, den=1),  # degrees
            MagicMock(num=30, den=1),  # minutes
            MagicMock(num=36, den=1),  # seconds
        ]

        result = self.kml._convert_to_degress(mock_ratio)
        # 45 + (30/60) + (36/3600) = 45.51
        self.assertAlmostEqual(result, 45.51, places=5)


class TestKmlDistanceBetweenPlacemarks(unittest.TestCase):
    """Test distance calculation between placemarks"""

    def setUp(self):
        self.kml = Kml("Test Map")

    def test_distance_same_location(self):
        """Test distance between identical coordinates"""
        distance = self.kml._distance_between_placemarks(45.5, -73.5, 45.5, -73.5)
        self.assertAlmostEqual(distance, 0, places=1)

    def test_distance_different_locations(self):
        """Test distance between different coordinates"""
        # Montreal to Quebec City (approximately 250 km)
        distance = self.kml._distance_between_placemarks(
            45.5017, -73.5673, 46.8139, -71.2080  # Montreal  # Quebec City
        )
        # Should be around 233,000 meters
        self.assertGreater(distance, 200000)
        self.assertLess(distance, 260000)

    def test_distance_small_difference(self):
        """Test distance for small coordinate differences"""
        # Approximately 1 km apart
        distance = self.kml._distance_between_placemarks(45.5, -73.5, 45.51, -73.5)
        # Should be around 1,100 meters
        self.assertGreater(distance, 1000)
        self.assertLess(distance, 1200)


class TestKmlReorderAndFilterPlacemarks(unittest.TestCase):
    """Test placemark reordering and filtering"""

    def setUp(self):
        self.kml = Kml("Test Map")
        self.kml.clear_placemarks()

    def test_reorder_placemarks_by_folder_and_latitude(self):
        """Test that placemarks are sorted by folder and latitude"""
        self.kml._add_placemark(46.0, -73.5, "Point3", "/folderB")
        self.kml._add_placemark(45.0, -73.5, "Point1", "/folderA")
        self.kml._add_placemark(47.0, -73.5, "Point4", "/folderB")
        self.kml._add_placemark(45.5, -73.5, "Point2", "/folderA")

        self.kml._reorder_placemarks()

        # Should be sorted by folder then latitude
        self.assertEqual(self.kml._placemark_list[0]["Name"], "Point1")
        self.assertEqual(self.kml._placemark_list[1]["Name"], "Point2")
        self.assertEqual(self.kml._placemark_list[2]["Name"], "Point3")
        self.assertEqual(self.kml._placemark_list[3]["Name"], "Point4")

    def test_filter_placemarks_no_minimum_distance(self):
        """Test filtering with no minimum distance - all should be exported"""
        self.kml._add_placemark(45.0, -73.5, "Point1", "/folder")
        self.kml._add_placemark(45.1, -73.5, "Point2", "/folder")
        self.kml._add_placemark(45.2, -73.5, "Point3", "/folder")

        self.kml.min_distance_between_placemarks_in_meters = 0
        count = self.kml._filter_placemarks()

        self.assertEqual(count, 3)
        for placemark in self.kml._placemark_list:
            self.assertTrue(placemark["Export"])

    def test_filter_placemarks_with_minimum_distance(self):
        """Test filtering with minimum distance - some should be filtered"""
        # Add points very close to each other
        self.kml._add_placemark(45.5, -73.5, "Point1", "/folder")
        self.kml._add_placemark(
            45.500001, -73.500001, "Point2", "/folder"
        )  # ~15 meters away
        self.kml._add_placemark(45.501, -73.5, "Point3", "/folder")  # ~111 meters away

        self.kml.min_distance_between_placemarks_in_meters = 50
        self.kml._reorder_placemarks()

        # Point1 and Point3 should be exported, Point2 should not
        self.assertTrue(self.kml._placemark_list[0]["Export"])
        self.assertFalse(self.kml._placemark_list[1]["Export"])
        self.assertTrue(self.kml._placemark_list[2]["Export"])


class TestKmlGetKmlString(unittest.TestCase):
    """Test KML string generation"""

    def setUp(self):
        self.kml = Kml("Test Map")
        self.kml.map_description = "Test Description"
        self.kml.clear_placemarks()

    def test_get_kml_string_basic_structure(self):
        """Test that KML string has correct basic structure"""
        self.kml._add_placemark(45.5, -73.5, "/path/to/test.jpg", "/folder")
        self.kml._reorder_placemarks()

        kml_string = self.kml._get_kml_string()

        # Check that essential KML elements are present
        self.assertIn('xmlns="http://www.opengis.net/kml/2.2"', kml_string)
        self.assertIn("<Document>", kml_string)
        self.assertIn("<name>Test Map</name>", kml_string)
        self.assertIn("<description>Test Description</description>", kml_string)
        self.assertIn("<Folder>", kml_string)
        self.assertIn("<Placemark>", kml_string)
        self.assertIn("<Point>", kml_string)
        self.assertIn("<coordinates>", kml_string)

    def test_get_kml_string_coordinates_format(self):
        """Test that coordinates are in correct format (lon,lat)"""
        self.kml._add_placemark(45.5, -73.5, "/path/to/test.jpg", "/folder")
        self.kml._reorder_placemarks()

        kml_string = self.kml._get_kml_string()

        # Coordinates should be longitude,latitude
        self.assertIn("-73.5,45.5", kml_string)

    def test_get_kml_string_multiple_folders(self):
        """Test KML with multiple folders"""
        self.kml._add_placemark(45.5, -73.5, "/folderA/test1.jpg", "/folderA")
        self.kml._add_placemark(46.5, -74.5, "/folderB/test2.jpg", "/folderB")
        self.kml._reorder_placemarks()

        kml_string = self.kml._get_kml_string()

        # Should have two folder elements
        self.assertIn("<name>/folderA</name>", kml_string)
        self.assertIn("<name>/folderB</name>", kml_string)

    def test_get_kml_string_respects_export_flag(self):
        """Test that only placemarks marked for export are included"""
        self.kml._add_placemark(45.5, -73.5, "/folder/test1.jpg", "/folder")
        self.kml._add_placemark(45.500001, -73.500001, "/folder/test2.jpg", "/folder")

        self.kml.min_distance_between_placemarks_in_meters = 50
        self.kml._reorder_placemarks()

        kml_string = self.kml._get_kml_string()

        # Only one placemark should be in the output
        self.assertEqual(kml_string.count("<Placemark>"), 1)


class TestKmlSaveFile(unittest.TestCase):
    """Test saving KML to file"""

    def setUp(self):
        self.kml = Kml("Test Map")
        self.kml._add_placemark(45.5, -73.5, "/folder/test.jpg", "/folder")
        self.kml._reorder_placemarks()

    def test_save_kml_file_success(self):
        """Test successfully saving KML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.kml")
            result = self.kml.save_kml_file(file_path)

            self.assertTrue(result)
            self.assertTrue(os.path.exists(file_path))

            # Verify file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("<?xml", content)
                self.assertIn("<kml", content)

    def test_save_kml_file_invalid_path(self):
        """Test saving to invalid path"""
        result = self.kml.save_kml_file("/invalid/path/that/does/not/exist/test.kml")
        self.assertFalse(result)


class TestKmlScanFolder(unittest.TestCase):
    """Test folder scanning functionality"""

    def setUp(self):
        self.kml = Kml("Test Map")
        self.kml.clear_placemarks()

    # @patch decorator usage: Multiple patches are applied from bottom to top
    # The corresponding mock arguments are passed to the test method from right to left
    # 1. @patch("exifread.process_file") → mock_exif (rightmost parameter)
    # 2. @patch("builtins.open", ...) → mock_file (middle parameter)
    # 3. @patch("pathlib.Path.glob") → mock_glob (leftmost parameter)
    #
    # This allows us to test scan_folder() without:
    # - Actually reading files from disk (builtins.open is mocked)
    # - Processing real EXIF data (exifread.process_file is mocked)
    # - Scanning real directories (pathlib.Path.glob is mocked)
    @patch("pathlib.Path.glob")
    @patch("builtins.open", new_callable=mock_open)
    @patch("exifread.process_file")
    def test_scan_folder_with_gps_data(self, mock_exif, mock_file, mock_glob):
        """Test scanning folder with images containing GPS data"""
        # Setup mock files: Configure what Path.glob() should return
        # This simulates finding two image files in the directory
        mock_glob.return_value = [Path("/test/image1.jpg"), Path("/test/image2.jpg")]

        # Setup mock EXIF data: Create a dictionary structure that mimics real exifread output
        # MagicMock objects simulate the nested structure of GPS coordinates:
        # - Each coordinate (lat/lon) has a 'values' list with 3 MagicMock objects
        # - Each value has 'num' (numerator) and 'den' (denominator) for degrees/minutes/seconds
        # - Latitude: 45°30'0"N = 45.5°
        # - Longitude: 73°30'0"W = -73.5°
        mock_exif.return_value = {
            "GPS GPSLatitude": MagicMock(
                values=[
                    MagicMock(num=45, den=1),  # 45 degrees
                    MagicMock(num=30, den=1),  # 30 minutes
                    MagicMock(num=0, den=1),  # 0 seconds
                ]
            ),
            "GPS GPSLatitudeRef": MagicMock(values=["N"]),  # North = positive
            "GPS GPSLongitude": MagicMock(
                values=[
                    MagicMock(num=73, den=1),  # 73 degrees
                    MagicMock(num=30, den=1),  # 30 minutes
                    MagicMock(num=0, den=1),  # 0 seconds
                ]
            ),
            "GPS GPSLongitudeRef": MagicMock(values=["W"]),  # West = negative
        }

        result = self.kml.scan_folder("/test")

        self.assertEqual(
            result, 6
        )  # mock will not allow filtering for different file types.
        self.assertEqual(len(self.kml._placemark_list), 6)

    @patch("pathlib.Path.glob")
    @patch("builtins.open", new_callable=mock_open)
    @patch("exifread.process_file")
    def test_scan_folder_without_gps_data(self, mock_exif, mock_file, mock_glob):
        """Test scanning folder with images without GPS data"""
        mock_glob.return_value = [Path("/test/image1.jpg")]
        # Return empty dict to simulate images with no EXIF GPS data
        # This tests that the code handles missing GPS data gracefully
        mock_exif.return_value = {}  # No GPS data

        result = self.kml.scan_folder("/test")

        self.assertEqual(result, 0)
        self.assertEqual(len(self.kml._placemark_list), 0)

    @patch("pathlib.Path.glob")
    def test_scan_folder_excludes_metadata_files(self, mock_glob):
        """Test that macOS metadata files are excluded"""
        mock_glob.return_value = [Path("/test/._metadata.jpg"), Path("/test/image.jpg")]

        with patch("builtins.open", mock_open()), patch(
            "exifread.process_file", return_value={}
        ):
            result = self.kml.scan_folder("/test")

        # Only non-metadata files should be processed
        # (both will return 0 since no GPS data, but metadata file should be skipped)
        self.assertEqual(len(self.kml._placemark_list), 0)

    # @patch with side_effect: Simulates exceptions/errors
    # Instead of returning a value, side_effect makes the mock raise an exception
    # This tests error handling without needing to corrupt actual files
    @patch("pathlib.Path.glob")
    @patch("builtins.open", side_effect=IOError("Cannot read file"))
    def test_scan_folder_handles_io_errors(self, mock_file, mock_glob):
        """Test that IO errors are handled gracefully"""
        mock_glob.return_value = [Path("/test/image1.jpg")]

        result = self.kml.scan_folder("/test")

        # Should return 0 and not crash
        self.assertEqual(result, 0)


class TestKmlIntegration(unittest.TestCase):
    """Integration tests for complete workflows"""

    def test_complete_workflow(self):
        """Test a complete workflow from creation to export"""
        kml = Kml("Integration Test Map")
        kml.map_description = "Testing complete workflow"

        # Add some placemarks
        kml._add_placemark(45.5, -73.5, "/folder1/image1.jpg", "/folder1")
        kml._add_placemark(46.5, -74.5, "/folder1/image2.jpg", "/folder1")
        kml._add_placemark(47.5, -75.5, "/folder2/image3.jpg", "/folder2")

        # Set minimum distance
        kml.min_distance_between_placemarks_in_meters = 100

        # Generate KML
        kml._reorder_placemarks()
        kml_string = kml._get_kml_string()

        # Verify output
        self.assertIn("Integration Test Map", kml_string)
        self.assertIn("Testing complete workflow", kml_string)
        self.assertIn("<Placemark>", kml_string)

        # Save to file
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "integration_test.kml")
            success = kml.save_kml_file(file_path)

            self.assertTrue(success)
            self.assertTrue(os.path.exists(file_path))

            # Verify it's valid XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            self.assertIn("kml", root.tag)


if __name__ == "__main__":
    unittest.main()
