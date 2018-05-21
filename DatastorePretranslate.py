#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import traceback
import sys
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from ansicolor import black
from AutoTranslationTranslator import FullAutoTranslator
from AutoTranslationIndexer import IgnoreFormulaPatternIndexer

pattern_exclude_from_indexes = ('pattern', 'approved', 'translated', 'untranslated')

def pretranslate_string(client, lang, string):
    try:
        engl = string['source']
        translator = FullAutoTranslator(lang)
        transl = translator.translate(engl)
        if transl is not None:
            string["target"] = transl
            string["translation_source"] = "BEAST"
            client.put(string)
    except Exception as ex:
        traceback.print_exc()

def pretranslate(client, executor, lang):
    query = client.query(kind='String', namespace=lang)
    query.add_filter('translation_source', '=', 'Crowdin')
    query.add_filter('is_translated', '=', False)
    query_iter = query.fetch()
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        # Index with and without relevant_for_live
        futures.append(executor.submit(pretranslate_string, client, lang, result))
        if count % 1000 == 0:
            print("Pretranslated {} strings".format(count))
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

    pretranslate(client, executor, args.lang)
    #index_pattern(client, "de", "§formula§", False)

