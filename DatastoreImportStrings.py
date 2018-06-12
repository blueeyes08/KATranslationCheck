#!/usr/bin/env python3
from google.cloud import datastore
from collections import namedtuple
import time
import traceback
import re
import nltk
import concurrent.futures
from deepdiff import DeepDiff
from nltk import ngrams
from XLIFFToXLSX import process_xliff_soup
from XLIFFReader import findXLIFFFiles, parse_xliff_file
from concurrent.futures import ThreadPoolExecutor
from ansicolor import black, green
from toolz.dicttoolz import merge
from AutoTranslationTranslator import IFPatternAutotranslator
from nltk.corpus import stopwords
from DatastoreIndexPatterns import read_groups_set

nltk.download("punkt")
nltk.download("stopwords")

ignored = 0
updated = 0

def compute_ngrams(words, max_size=5):
    # Compute ngrams
    result = []
    for sz in range(1, max_size+1):
        result += [" ".join(ngram) for ngram in ngrams(words, sz)]
    return list(set(result))

generic_stopwords = ["https", "nbsp"]

string_exclude_from_indexes = ('source', 'target', 'fileid')

client = datastore.Client(project="watts-198422")
executor = ThreadPoolExecutor(1024)

decimal_point_regex = re.compile(r"(-?\d+\}?)\.(-?\d+|\\\\[a-z]+\{\d+)")
coordinate_regex = re.compile(r"\$([A-Z]?\{?)\(\s*(-?\d+(([\.,]|\{,\})\d+)?|-?[a-z]|-?\\\\[a-z]+[A-Z]?\{-?\d+[.,]?\d*\})\s*[,;|]\s*(-?\d+(([\.,]|\{,\})\d+)?|-?[a-z]|-?\\\\[a-z]+[A-Z]?\{-?\d+[.,]?\d*\})\s*\)(\}?)\$")
double_comma_regex = re.compile(r"(,|\{,\}|\.)\d+(,|\{,\}|\.)")
literal_dollar_regex = re.compile(r"\\\$(?=\s*\S)")
space_around_url_regex = re.compile(r"(!\[\]\s+\(|!\s+\[\]\(|!\s+\[\]\s+\()")
possible_thousands_separator_re = re.compile(r"(\d+)(\{,\}|,)(\d{3})")

def has_possible_thousands_separator(source, target):
    for rgx in possible_thousands_separator_re.findall(source):
        return ("{},{}".format(rgx[0], rgx[2]) in target or "{}{{,}}{}".format(rgx[0], rgx[2]) in target)

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
def write_entry(obj, lang, groups):
    global ignored
    global updated
    try:
        key = client.key('String', obj["id"], namespace=lang)
        del obj["id"]
        entity = client.get(key) or datastore.Entity(key, exclude_from_indexes=string_exclude_from_indexes)
        orig_entity = dict(entity)
        # Update translations
        if obj["is_translated"] or obj["is_approved"]:
            # Update everything
            entity["source"] = obj["source"]
            entity["target"] = obj["target"]
            entity["translation_source"] = obj["translation_source"]
            entity["is_translated"] = obj["is_translated"]
            entity["is_approved"] = obj["is_approved"]
        elif entity.get("translation_source", "") == "BEAST": # Pretranslated
            # only update if string changed
            # unsure if this can happen with the same string ID
            if entity["source"] != obj["source"]:
                entity["source"] = obj["source"]
                entity["target"] = obj["target"]
                entity["translation_source"] = obj["translation_source"]
        else:
            # Not pretranslated, but not translated
            # Update "just in case it changed"
            entity["source"] = obj["source"]
            entity["target"] = obj["target"]
            entity["translation_source"] = obj["translation_source"]
        # Update keys that were previously not present
        entity.update(merge(obj, entity))
        string_update_rules(lang, entity, groups)
        # Did we change anything relevant?
        if len(DeepDiff(orig_entity, dict(entity))) > 0:
            client.put(entity)
            updated += 1
            return True
        else:
            ignored += 1
            return False
    except Exception as ex:
        traceback.print_exc()
        return False

genericIFTranslator = IFPatternAutotranslator("de")

def string_update_rules(lang, obj, groups):
    #
    obj["has_decimal_point"] = obj["is_translated"] and obj["target"].count("$") >= 2 and (decimal_point_regex.search(obj["target"]) is not None)
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
    if "has_double_comma_override" not in obj:
        obj["has_double_comma_override"] = False
    #
    obj["has_literal_dollar"] = obj["is_translated"] and (literal_dollar_regex.search(obj["target"]) is not None)
    if "has_literal_dollar_override" not in obj:
        obj["has_literal_dollar_override"] = False
    #
    obj["has_space_around_url"] = obj["is_translated"] and (space_around_url_regex.search(obj["target"]) is not None)
    if "has_space_around_url_override" not in obj:
        obj["has_space_around_url_override"] = False
    #
    obj["has_possible_thousands_separator"] = obj["is_translated"] and has_possible_thousands_separator(obj["source"], obj["target"])
    if "has_possible_thousands_separator_override" not in obj:
        obj["has_possible_thousands_separator_override"] = False
    ###
    ### Update pattern
    ###
    normalized, _, _ = genericIFTranslator.normalize(obj["source"])
    obj["normalized"] = normalized[:1200] # Limit length due to datastore limitation
    # Delete old fields
    if "words" in obj:
        del obj["words"]
    if "words_cs" in obj:
        del obj["words_cs"]
    ###
    ### Update keywords
    ###   words: CI words
    ###   words_cs: CS words
    ###   words_ngrams: CS words
    ###   words_cs_ngrams: CS words
    ###
    if obj["is_translated"]:
        raw_words = nltk.word_tokenize(obj["target"])
        raw_alpha_words = list(filter(lambda s: (s and s.isalpha()), raw_words))
        # Compute ngrams (including stopwords)
        obj["words_ngrams"] = compute_ngrams([w.lower() for w in raw_alpha_words])
        obj["words_ngrams_cs"] = compute_ngrams(raw_alpha_words)
    ### Update groups
    string_groups = set()
    for group in groups:
        if obj["file"] in group["files"]:
            string_groups.add(group["name"])
    obj["groups"] = sorted(list(string_groups))


def export_lang_to_db(lang, filt):
    count = 0
    groups = read_groups_set()
    futures = []
    for file in findXLIFFFiles("cache/{}".format(lang), filt=filt):
        # e.g. '1_high_priority_platform/about.donate.xliff'
        canonicalFilename = "/".join(file.split("/")[2:])
        section = canonicalFilename.partition("/")[0]
        # Dont index drafts
        if "learn.draft.xliff" in canonicalFilename:
            print(green("Skipping {}".format(canonicalFilename), bold=True))
        # relevant_for_live
        relevant_for_live = False
        if canonicalFilename in relevant_for_live_files:
            relevant_for_live = True

        print(black(file, bold=True))
        soup = parse_xliff_file(file)
        for entry in process_xliff_soup(soup, also_approved=True):
            obj = {
                "id": int(entry.ID),
                "source": entry.Source,
                "target": entry.Translated,
                "source_length": len(entry.Source),
                "is_translated": entry.IsTranslated,
                "is_approved": entry.IsApproved,
                "translation_source": "Crowdin",
                "file": canonicalFilename,
                "fileid": entry.FileID,
                "relevant_for_live": relevant_for_live
            }
            # Async write
            futures.append(executor.submit(write_entry, obj, lang, groups))
            # Stats
            count += 1
            if count % 1000 == 0:
                print("Processed {} records".format(count))
    for future in concurrent.futures.as_completed(futures):
        pass
    print("Updated {} strings, ignored {} strings".format(updated, ignored))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', help='The crowdin lang code')
    parser.add_argument('-f', '--filter', nargs="*", action="append", help='Ignore file paths that do not contain this string, e.g. exercises or 2_high_priority. Can use multiple ones which are ANDed')
    args = parser.parse_args()

    export_lang_to_db(args.lang, args.filter)

