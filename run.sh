#!/bin/bash
git pull
# Download
./katc.py -l de update-translations -j 256
./katc.py -l pt-BR update-translations -j 256
/katc.py -l bg update-translations -j 256
./katc.py -l sv-SE update-translations -j 256
./katc.py -l ja update-translations -j 256
./katc.py -l ka update-translations -j 256
./katc.py -l hu update-translations -j 256
./katc.py -l cs update-translations -j 256

# Render
./katc.py -l de render -f 2_high
#./katc.py -l pt-BR render -f 2_high
./katc.py -l bg render -f 2_high
./katc.py -l hu render -f 2_high
./katc.py -l cs render -f 2_high
./katc.py -l sv-SE render -f 2_high
./katc.py -l ja render -f 2_high
./katc.py -l ka render -f 2_high
