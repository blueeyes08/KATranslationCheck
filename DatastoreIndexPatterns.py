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

def index_pattern(client, lang, pattern, section="2_high_priority_content"):
    key = client.key('Pattern', pattern, namespace=lang)
    patternInfo = datastore.Entity(key)
    print("Indexing '{}'".format(pattern))
    patternInfo.update({
        "pattern": pattern,
        "section": section,
        # Lists of String IDs
        "approved": [],
        "translated": [],
        "untranslated": []
    })
    # Find all strings 
    query = client.query(kind='String', namespace=lang)
    query.add_filter('section', '=', section)
    query.add_filter('ifpattern', '=', pattern)
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

def index(client, executor, lang, section):
    query = client.query(kind='String', namespace=lang)
    query.add_filter('section', '=', section)
    query.distinct_on = ['ifpattern']
    query.projection = ['ifpattern']
    query_iter = query.fetch()
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        futures.append(executor.submit(index_pattern, client, lang, result["ifpattern"], section))
    # Wait for futures to finish
    for future in concurrent.futures.as_completed(futures):
        pass
    print("Total {} patterns".format(count))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    parser.add_argument('-s', '--section', default="2_high_priority_content", help='The section to index for')
    args = parser.parse_args()


    client = datastore.Client(project="watts-198422")
    executor = ThreadPoolExecutor(512)

    index(client, executor, args.lang, args.section)

