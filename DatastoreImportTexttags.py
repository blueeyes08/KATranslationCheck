#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
from ansicolor import black
from AutoTranslationIndexer import TextTagIndexer

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
    indexer = TextTagIndexer(lang)
    for file in findXLIFFFiles("cache/{}".format(lang), filt=filt):
        # e.g. '1_high_priority_platform/about.donate.xliff'
        canonicalFilename = "/".join(file.split("/")[2:])
        print(black(file, bold=True))
        soup = parse_xliff_file(file)
        for entry in process_xliff_soup(soup, also_approved=True):
            indexer.add(entry.Source, entry.Translated, file, entry.IsApproved)
            # Stats
            count += 1
            if count % 1000 == 0:
                print("Processed {} records".format(count))
    return ttt(lang, list(indexer._convert_to_json()))

def ttt(lang, texttags):
    # Delete type, which is always "texttag"
    for texttag in texttags:
        del texttag["type"]
    # Generate DB ids
    dbids = [client.key('Texttag', texttag["english"], namespace=lang) for texttag in texttags]
    texttagMap = {texttag["english"]: texttag for texttag in texttags}
    # Fetch from DB
    missing = []
    dbvalues = client.get_multi(dbids, missing=missing)
    #### Insert missing entries
    # Update missing entry values
    for entity in missing:
        entity.update()
    # Write to DB
    if missing:
        client.put_multi(missing)
    ### Update 
    toUpdate = []
    for dbvalue in dbvalues:
        updated = False
        texttag = texttagMap[dbvalue.key.name]
        # Update translation
        if (texttag["translated"] != dbvalue["translated"]) or (texttag["translation_is_proofread"] != dbvalue["translation_is_proofread"]):
            dbvalue.update(texttag)
            toUpdate.append(dbvalue)
    if toUpdate:
        client.put_multi(toUpdate)
    print("Inserted {} entries, updated {} entries".format(len(missing), len(toUpdate)))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    parser.add_argument('-f', '--filter', nargs="*", action="append", help='Ignore file paths that do not contain this string, e.g. exercises or 2_high_priority. Can use multiple ones which are ANDed')
    args = parser.parse_args()

    export_lang_to_db(args.lang, args.filter)

