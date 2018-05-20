#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import sys
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from ansicolor import black
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer

pattern_exclude_from_indexes = ('pattern', 'approved', 'translated', 'untranslated')

def index_pattern(client, lang, pattern, onlyRelevantForLive=False):
    key = client.key('Pattern', pattern, namespace=lang)
    patternInfo = datastore.Entity(key, exclude_from_indexes=pattern_exclude_from_indexes)
    print("Indexing '{}'".format(pattern))
    patternInfo.update({
        "pattern": pattern,
        "pattern_length": len(pattern),
        # Lists of String IDs
        "approved": [],
        "translated": [],
        "untranslated": [],
        "relevant_for_live": onlyRelevantForLive
    })
    # Find all strings 
    query = client.query(kind='String', namespace=lang)
    if onlyRelevantForLive:
        query.add_filter('relevant_for_live', '=', True)
    query.add_filter('normalized', '=', pattern)
    query.projection = []
    query_iter = query.fetch()
    # ... and add them to the list
    for result in query_iter:
        if result["is_approved"]:
            patternInfo["approved"].append(result.key.id)
        elif result["is_translated"]:
            patternInfo["translated"].append(result.key.id)
        else:
            patternInfo["untranslated"].append(result.key.id)
    # Complete stats
    patternInfo["num_approved"] = len(patternInfo["approved"])
    patternInfo["num_translated"] = len(patternInfo["translated"])
    patternInfo["num_untranslated"] = len(patternInfo["untranslated"])
    patternInfo["num_total"] = patternInfo["num_approved"] + patternInfo["num_translated"] + patternInfo["num_untranslated"]
    patternInfo["num_unapproved"] = patternInfo["num_translated"] + patternInfo["num_untranslated"]
    # Write to DB
    client.put(patternInfo)

def index(client, executor, lang):
    query = client.query(kind='String', namespace=lang)
    query.distinct_on = ['normalized']
    query.projection = ['normalized']
    query_iter = query.fetch()
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        # Index with and without relevant_for_live
        futures.append(executor.submit(index_pattern, client, lang, result["normalized"], True))
        futures.append(executor.submit(index_pattern, client, lang, result["normalized"], False))
    # Wait for futures to finish
    for future in concurrent.futures.as_completed(futures):
        pass
    print("Total {} patterns".format(count))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    args = parser.parse_args()


    client = datastore.Client(project="watts-198422")
    executor = ThreadPoolExecutor(512)

    index(client, executor, args.lang)

