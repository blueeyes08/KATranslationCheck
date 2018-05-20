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
coordinate_regex = re.compile(r"\$([A-Z]?\{?)\(\s*(-?\d+(([\.,]|\{,\})\d+)?|-?[a-z]|-?\\\\[a-z]+[A-Z]?\{-?\d+[.,]?\d*\})\s*[,;|]\s*(-?\d+(([\.,]|\{,\})\d+)?|-?[a-z]|-?\\\\[a-z]+[A-Z]?\{-?\d+[.,]?\d*\})\s*\)(\}?)\$")
double_comma_regex = re.compile(r"(,|\{,\}|\.)\d+(,|\{,\}|\.)")
literal_dollar_regex = re.compile(r"\\\\$")

relevant_for_live_files = ["2_high_priority_content/learn.math.early-math.articles.xliff",
    "2_high_priority_content/learn.math.early-math.exercises.xliff",
    "2_high_priority_content/learn.math.early-math.xliff",
    "2_high_priority_content/learn.math.early-math.videos.xliff",
    "2_high_priority_content/learn.math.arithmetic.articles.xliff",
    "2_high_priority_content/learn.math.arithmetic.exercises.xliff",
    "2_high_priority_content/learn.math.arithmetic.xliff",
    "2_high_priority_content/learn.math.arithmetic.videos.xliff",
    "2_high_priority_content/learn.math.pre-algebra.articles.xliff",
    "2_high_priority_content/learn.math.pre-algebra.exercises.xliff",
    "2_high_priority_content/learn.math.pre-algebra.xliff",
    "2_high_priority_content/learn.math.pre-algebra.videos.xliff",
    "1_high_priority_platform/_other_.xliff"]

# Create & store an entity
def write_entry(obj, lang):
    key = client.key('String', obj["id"], namespace=lang)
    del obj["id"]
    entity = client.get(key) or datastore.Entity(key)
    entity.update(obj)
    string_update_rules(entity)
    client.put(entity)

def string_update_rules(obj):
    #
    obj["has_decimal_point"] = obj["is_translated"] and (decimal_point_regex.search(obj["target"]) is not None)
    if "has_decimal_point_override" not in obj:
        obj["has_decimal_point_override"] = False
    #
    obj["has_enclosed_comma_outside_math"] = obj["is_translated"] and "{,}" in obj["target"] and "$" not in obj["target"]
    if "has_enclosed_comma_outside_math_override" not in obj:
        obj["has_enclosed_comma_outside_math_override"] = False
    #
    obj["has_coordinate_without_pipe"] = obj["is_translated"] and (coordinate_regex.search(obj["target"]) is not None)
    if "has_coordinate_without_pipe_override" not in obj:
        obj["has_coordinate_without_pipe_override"] = False
    #
    obj["has_double_comma"] = obj["is_translated"] and (double_comma_regex.search(obj["target"]) is not None)
    if "has_double_comma" not in obj:
        obj["has_double_comma_override"] = False
        obj["has_coordinate_without_pipe_override"] = False
    #
    obj["has_literal_dollar"] = obj["is_translated"] and (literal_dollar_regex.search(obj["target"]) is not None)
    if "has_literal_dollar" not in obj:
        obj["has_literal_dollar_override"] = False


def export_lang_to_db(lang, filt):
    count = 0
    ifTranslator = IFPatternAutotranslator(lang)
    for file in findXLIFFFiles("cache/{}".format(lang), filt=filt):
        # e.g. '1_high_priority_platform/about.donate.xliff'
        canonicalFilename = "/".join(file.split("/")[2:])
        section = canonicalFilename.partition("/")[0]
        # relevant_for_live
        relevant_for_live = False
        if canonicalFilename in relevant_for_live_files:
            relevant_for_live = True

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
                "relevant_for_live": relevant_for_live
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

