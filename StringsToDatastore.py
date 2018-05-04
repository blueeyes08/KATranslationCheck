#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
from ansicolor import black
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer

client = datastore.Client(project="watts-198422")

executor = ThreadPoolExecutor(128)

# Create & store an entity
def write_entry(obj):
    key = client.key('String', "{}-{}".format(obj["lang"], obj["id"]))
    entity = datastore.Entity(key)
    entity.update(obj)
    client.put(entity)

def export_lang_to_db(lang):
    count = 0
    ifIndexer = IgnoreFormulaPatternIndexer(lang)
    for file in findXLIFFFiles("cache/{}".format(lang)):
        print(black(file, bold=True))
        soup = parse_xliff_file(file)
        for entry in process_xliff_soup(soup):
            obj = {
                "id": entry.ID,
                "source": entry.Source,
                "target": entry.Translated,
                "is_translated": entry.IsTranslated,
                "is_approved": entry.IsApproved,
                "lang": lang,
                "translation_source": "Crowdin",
                "ifpattern": ifIndexer._normalize(entry.Source),
                "file": ""
            }
            # Async write
            executor.submit(write_entry, obj)
            # Stats
            count += 1
            if count % 1000 == 0:
                print("Processed {} records".format(count))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    args = parser.parse_args()

    export_lang_to_db(args.lang)

