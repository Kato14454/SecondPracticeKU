@echo off
set PYTHONPATH=%~dp0src
python -m unittest discover -s tests -v