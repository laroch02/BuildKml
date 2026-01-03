rem Set current directory to the batchfile directory.
cd /d %~dp0
pyinstaller build_kml.py --onefile -n build_kml
pause