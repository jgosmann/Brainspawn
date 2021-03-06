#!/bin/bash
SOURCE_FOLDER="../brainspawn"
RST_FILES="source"

PYTHONPATH=$PYTHONPATH:$(readlink -m ../brainspawn)
echo "PYTHONPATH => $PYTHONPATH"
echo

echo ">>> Cleaning old .rst files"
echo
rm -v "${RST_FILES}/modules.rst" "${RST_FILES}/brainspawn."* 

# Search source folder for new files. Creates basic .rst file for them that
# come with auto-doc. -e to generate an rst per python file vs. 1 per folder
echo
echo ">>> Creating .rst files"
echo
sphinx-apidoc -e -o ${RST_FILES} ${SOURCE_FOLDER} || exit 1

echo
echo ">>> Creating html files"
echo
make html || exit 1

echo
echo ">>> Complete: open \"build/html/index.html\""
