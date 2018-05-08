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

executor = ThreadPoolExecutor(512)

# Create & store an entity
def write_entry(obj, lang):
    key = client.key('String', obj["id"], namespace=lang)
    del obj["id"]
    entity = datastore.Entity(key)
    entity.update(obj)
    client.put(entity)

def export_lang_to_db(lang, filt):
    count = 0
    ifIndexer = IgnoreFormulaPatternIndexer(lang)
    for file in findXLIFFFiles("cache/{}".format(lang), filt=filt):
        # e.g. '1_high_priority_platform/about.donate.xliff'
        canonicalFilename = "/".join(file.split("/")[2:])
        print(black(file, bold=True))
        soup = parse_xliff_file(file)
        for entry in process_xliff_soup(soup, also_approved=True):
            obj = {
                "id": int(entry.ID),
                "source": entry.Source,
                "target": entry.Translated,
                "is_translated": entry.IsTranslated,
                "is_approved": entry.IsApproved,
                "translation_source": "Crowdin",
                "ifpattern": ifIndexer._normalize(entry.Source),
                "file": canonicalFilename
            }
            # Async write
            executor.submit(write_entry, obj, lang)
            # Stats
            count += 1
            if count % 1000 == 0:
                print("Processed {} records".format(count))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    parser.add_argument('-f', '--filter', nargs="*", action="append", help='Ignore file paths that do not contain this string, e.g. exercises or 2_high_priority. Can use multiple ones which are ANDed')
    args = parser.parse_args()

    export_lang_to_db(args.lang, args.filter)

