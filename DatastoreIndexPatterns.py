#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import traceback
import sys
import json
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from ansicolor import black
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer

pattern_exclude_from_indexes = ('pattern', 'approved', 'translated', 'untranslated')

total_string_count = 0

def read_groups():
    with open("groups.json") as infile:
        return json.load(infile)

def read_groups_set():
    groups = read_groups()
    for group in groups:
        group["files"] = set(group["files"])
    return groups

def index_pattern(client, lang, pattern, groups, onlyRelevantForLive=False):
    global total_string_count
    try:
        prefix = "live" if onlyRelevantForLive else "all"
        key = client.key('Pattern', "{}#{}".format(prefix, pattern), namespace=lang)
        patternInfo = datastore.Entity(key, exclude_from_indexes=pattern_exclude_from_indexes)
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
        query.projection = ['is_approved', 'is_translated', 'file']
        unapproved_files = set()
        all_files = set()
        # ... and add them to the list
        for result in query.fetch():
            if result["is_approved"]:
                patternInfo["approved"].append(result.key.id)
            elif result["is_translated"]:
                unapproved_files.add(result["file"])
                patternInfo["translated"].append(result.key.id)
            else:
                unapproved_files.add(result["file"])
                patternInfo["untranslated"].append(result.key.id)
            all_files.add(result["file"])
        # Compute groups
        pattern_groups = set()
        for group in groups:
            if len(group["files"] & unapproved_files) > 0:
                pattern_groups.add(group["name"])
        patternInfo["groups"] = sorted(list(pattern_groups))
        # Complete stats
        patternInfo["num_approved"] = len(patternInfo["approved"])
        patternInfo["num_translated"] = len(patternInfo["translated"])
        patternInfo["num_untranslated"] = len(patternInfo["untranslated"])
        patternInfo["num_total"] = patternInfo["num_approved"] + patternInfo["num_translated"] + patternInfo["num_untranslated"]
        patternInfo["num_unapproved"] = patternInfo["num_translated"] + patternInfo["num_untranslated"]
        # Limit entity size
        patternInfo["untranslated"] = patternInfo["untranslated"][:500]
        patternInfo["translated"] = patternInfo["translated"][:500]
        patternInfo["approved"] = patternInfo["approved"][:500]
        # File lists
        patternInfo["all_files"] = sorted(list(all_files))
        patternInfo["unapproved_files"] = sorted(list(unapproved_files))
        # Write to DB
        if patternInfo["num_total"] >= 2:
            # Stats
            if not onlyRelevantForLive:
                total_string_count += patternInfo["num_total"]
            # Write
            print("Indexing '{}' (relevant_for_live={})".format(pattern, onlyRelevantForLive))
            client.put(patternInfo)
        else: # No strings
            client.delete(key)
    except Exception as ex:
        traceback.print_exc()

def index(client, executor, lang, groups):
    query = client.query(kind='String', namespace=lang)
    query.distinct_on = ['normalized']
    query.projection = ['normalized']
    query_iter = query.fetch()
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        # Index with and without relevant_for_live
        futures.append(executor.submit(index_pattern, client, lang, result["normalized"], groups, True))
        futures.append(executor.submit(index_pattern, client, lang, result["normalized"], groups, False))
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
    executor = ThreadPoolExecutor(1024)

    groups = read_groups_set()

    index(client, executor, args.lang, groups)
    #index_pattern(client, "de", "§formula§", False)
    print("Total pattern strings: {}".format(total_string_count))

