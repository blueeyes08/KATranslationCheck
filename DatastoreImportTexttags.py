#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
from ansicolor import black
from AutoTranslationIndexer import TextTagIndexer
from DatastoreUtils import DatastoreChunkClient

client = datastore.Client(project="watts-198422")
executor = ThreadPoolExecutor(512)
chunkClient = DatastoreChunkClient(client, executor)

def export_lang_to_db(lang, filt):
    count = 0
    indexer = TextTagIndexer(lang)
    for file in findXLIFFFiles("cache/{}".format(lang), filt=filt):
        # e.g. '1_high_priority_platform/about.donate.xliff'
        canonicalFilename = "/".join(file.split("/")[2:])
        print(black(file, bold=True))
        soup = parse_xliff_file(file)
        for entry in process_xliff_soup(soup, also_approved=True):
            indexer.add(entry.Source, entry.Translated, file.rpartition("/")[2], entry.IsApproved)
            # Stats
            count += 1
            if count % 1000 == 0:
                print("Processed {} records".format(count))
    return ttt(lang, list(indexer._convert_to_json()))

def ttt(lang, texttags):
    # Ignore empty texttag
    texttags = [texttag for texttag in texttags if texttag["english"] not in ('', '______')]
    # Delete type, which is always "texttag"
    for texttag in texttags:
        texttag["approved_in_ui"] = False
        del texttag["files"]
        del texttag["type"]
    # Generate DB ids
    dbids = [client.key('Texttag', texttag["english"], namespace=lang) for texttag in texttags]
    texttagMap = {texttag["english"]: texttag for texttag in texttags}
    # Fetch from DB
    dbvalues, missing = chunkClient.get_multi(dbids)
    #### Insert missing entries
    # Update missing entry values
    for entity in missing:
        entity.update(texttagMap[entity.key.name])
        print(entity)
    # Write to DB
    if missing:
        chunkClient.put_multi(missing)
    ### Update 
    toUpdate = []
    for dbvalue in dbvalues:
        texttag = texttagMap[dbvalue.key.name]
        # Update translation
        if not dbvalue["approved_in_ui"] and (("translated" not in dbvalue) or (texttag["translated"] != dbvalue["translated"]) or (texttag["translation_is_proofread"] != dbvalue["translation_is_proofread"])):
            dbvalue.update(texttag)
            toUpdate.append(dbvalue)
    if toUpdate:
        chunkClient.put_multi(toUpdate)
    print("Inserted {} entries, updated {} entries".format(len(missing), len(toUpdate)))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    parser.add_argument('-f', '--filter', nargs="*", action="append", help='Ignore file paths that do not contain this string, e.g. exercises or 2_high_priority. Can use multiple ones which are ANDed')
    args = parser.parse_args()

    export_lang_to_db(args.lang, args.filter)

