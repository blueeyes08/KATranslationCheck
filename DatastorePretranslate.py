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

def pretranslate_string(client, lang, string, retries_left=3):
    try:
        engl = string['source']
        translator = FullAutoTranslator(lang)
        transl = translator.translate(engl)
        if transl is not None:
            string["target"] = transl
            string["translation_source"] = "BEAST"
            client.put(string)
        else:
            if retries_left > 0:
                return pretranslate_string(client, lang, string, retries_left-1)
    except Exception as ex:
        traceback.print_exc()

def pretranslate(client, executor, lang, file, overwrite=False):
    query = client.query(kind='String', namespace=lang)
    query.add_filter('translation_source', '=', 'Crowdin')
    query.add_filter('is_translated', '=', False)
    if file:
        query.add_filter('file', '=', file)
    query_iter = query.fetch()
    count = 0
    futures = []
    for result in query_iter:
        count += 1
        # Skip already translated strings
        if (result["translation_source"] == "BEAST" and not overwrite):
            return
        # Index with and without relevant_for_live
        futures.append(executor.submit(pretranslate_string, client, lang, result))
        #pretranslate_string(client, lang, result)
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
    parser.add_argument('-f','--file', help='File code to filter for')
    parser.add_argument('-o','--overwrite', action='store_true', help='Overwrite old pretranslations')
    parser.add_argument('-j','--threads', default=3, type=int, help='Number of threads. Reduce on rate error')
    args = parser.parse_args()

    client = datastore.Client(project="watts-198422")
    executor = ThreadPoolExecutor(args.threads)

    pretranslate(client, executor, args.lang, args.file, overwrite=args.overwrite)
    #index_pattern(client, "de", "§formula§", False)

