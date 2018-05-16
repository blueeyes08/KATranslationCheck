#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import re
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
from ansicolor import black
from AutoTranslationTranslator import IFPatternAutotranslator

client = datastore.Client(project="watts-198422")
executor = ThreadPoolExecutor(512)

decimal_point_regex = re.compile(r"(-?\d+\}?)\.(-?\d+|\\\\[a-z]+\{\d+)")

# Create & store an entity
def write_entry(obj, lang):
    key = client.key('String', obj["id"], namespace=lang)
    del obj["id"]
    entity = client.get(key) or datastore.Entity(key)
    entity.update(obj)
    client.put(entity)

def string_update_rules(obj):
    obj["has_decimal_point"] = obj["is_translated"] and (decimal_point_regex.search(obj["target"]) is not None)
    obj["has_decimal_point_override"] = False

def export_lang_to_db(lang, filt):
    count = 0
    ifTranslator = IFPatternAutotranslator(lang)
    for file in findXLIFFFiles("cache/{}".format(lang), filt=filt):
        # e.g. '1_high_priority_platform/about.donate.xliff'
        canonicalFilename = "/".join(file.split("/")[2:])
        section = canonicalFilename.partition("/")[0]
        print(black(file, bold=True))
        soup = parse_xliff_file(file)
        for entry in process_xliff_soup(soup, also_approved=True):
            normalized, _, _ = ifTranslator.normalize(entry.Source)
            obj = {
                "id": int(entry.ID),
                "source": entry.Source,
                "target": entry.Translated,
                "source_length": len(entry.Source),
                "is_translated": entry.IsTranslated,
                "is_approved": entry.IsApproved,
                "translation_source": "Crowdin",
                "ifpattern": normalized,
                "file": canonicalFilename,
                "fileid": entry.FileID,
                "section": section,
            }
            # Update rule flags
            string_update_rules(obj)
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

