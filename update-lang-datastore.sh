#!/bin/sh
./katc.py -l $1 update-translations -j128 && ./DatastoreImportStrings.py $1 && ./DatastoreIndexPatterns.py $1
