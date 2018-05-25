#!/bin/bash
if [ $# -ne 2 ]; then
    echo "Usage: pretranslate.sh <lang code> <filter string e.g. arithmetic>"
    exit 1
fi
for i in $(cat filenames.txt  | grep $2) ; do ./DatastorePretranslate.py $1 -f $i ; done 
