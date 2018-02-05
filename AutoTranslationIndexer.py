#!/usr/bin/env python3
import cffi_re2 as re
import time
from collections import Counter, defaultdict
from ansicolor import red
from toolz.dicttoolz import valmap
from AutoTranslationTranslator import RuleAutotranslator
import os
import json
from bs4 import BeautifulSoup
from UpdateAllFiles import getTranslationFilemapCache
from AutoTranslateCommon import *

class CompositeIndexer(object):
    """
    Utility that calls add() once for every child object.
    So you dont need to change indexers all over the place.

    Args are filtered for None
    """
    def __init__(self, *args):
        self.children = list(filter(lambda arg: arg is not None, args))

    def add(self, *args, **kwargs):
        for child in self.children:
            child.add(*args, **kwargs)

    def preindex(self, *args, **kwargs):
        for child in self.children:
            child.preindex(*args, **kwargs)

    def clean_preindex(self, *args, **kwargs):
        for child in self.children:
            child.clean_preindex(*args, **kwargs)


class TextTagIndexer(object):
    def __init__(self, lang):
        self.lang = lang
        self.index = Counter() # TOTAL count for each text tag
        self.untranslated_index = Counter()
        self.approved_index = defaultdict(Counter) # norm engl => translation => count ONLY for proofread versions
        self.translated_index = defaultdict(Counter) # norm engl => translation => count
        self.filename_index = defaultdict(Counter) # norm_engl => {filename: count}
        self._re = get_text_content_regex()

    def add(self, engl, translated=None, filename=None, approved=False):
        # Find english hits and possible hits in target lang to be able to match them!
        engl_hits = self._re.finditer(engl)
        # Just make sure that transl_hits has the same length as index
        transl_hits = None if translated is None else self._re.finditer(translated)
        # Find hits in english
        if translated is not None: # Translated, do not count but index
            for engl_hit, transl_hit in zip(engl_hits, transl_hits):
                # Extract corresponding hits
                engl_hit = engl_hit.group(2).strip()
                transl_hit = transl_hit.group(2).strip()
                # Check for trivial number-only tags
                if is_numeric_only(engl_hit):
                    continue # Trivial, don't index
                # Count
                self.index[engl_hit] += 1
                # If untranslated, do not index translions
                if transl_hit:
                    if approved:
                        self.approved_index[engl_hit][transl_hit] += 1
                    else:
                        self.translated_index[engl_hit][transl_hit] += 1
        else: # Not translated, just index to collect stats
            for engl_hit in engl_hits:
                engl_hit = engl_hit.group(2).strip()
                if is_numeric_only(engl_hit):
                    continue # Trivial, don't index
                self.index[engl_hit] += 1
                self.untranslated_index[engl_hit] += 1
                # Count occurrences in files
                self.filename_index[engl_hit][filename] += 1
        #except Exception as ex:
        #    print(red("Failed to index '{}' --> {}: {}".format(engl, translated, ex) bold=True))

    def __len__(self):
        return len(self.index)

    def _convert_to_json(self, ignore_alltranslated=False, only_proofread_patterns=False):
        texttags = []
        # Sort by most untranslated
        for (hit, count) in self.untranslated_index.most_common():
            total_count = self.index[hit]
            untransl_count = self.untranslated_index[hit]
            if untransl_count == 0 and ignore_alltranslated:
                continue
            # Get the most common translation for that tag
            pattern_from_proofread = False
            transl = ""
            if len(self.approved_index[hit]) > 0:
                transl = self.approved_index[hit].most_common(1)[0][0]
                pattern_from_proofread = True
            elif len(self.translated_index[hit]) > 0:
                transl = self.translated_index[hit].most_common(1)[0][0]

            if only_proofread_patterns and not pattern_from_proofread:
                continue

            texttags.append({"english": hit,
                "translated": transl, "count": total_count,
                "untranslated_count": untransl_count,
                "files": self.filename_index[hit],
                "type": "texttag",
                "translation_is_proofread": pattern_from_proofread})
        print("Found {} text tags".format(len(texttags)))
        return texttags

    def preindex(self, *args, **kwargs):
        pass

    def clean_preindex(self, *args, **kwargs):
        pass

    def exportJSON(self, ignore_alltranslated=False, only_proofread_patterns=False):
        texttags = self._convert_to_json(ignore_alltranslated, only_proofread_patterns=only_proofread_patterns)
        # Export main patterns file
        with open(transmap_filename(self.lang, "texttags"), "w") as outfile:
            json.dump(texttags, outfile, indent=4, sort_keys=True)

        # export file of untranslated patterns
        with open(transmap_filename(self.lang, "texttags.untranslated"), "w") as outfile:
            json.dump(list(filter(lambda p: not p["translated"], texttags)),
                outfile, indent=4, sort_keys=True)

    def exportXLIFF(self, ignore_alltranslated=False, only_proofread_patterns=False):
        texttags = self._convert_to_json(ignore_alltranslated, only_proofread_patterns=only_proofread_patterns)
        soup = pattern_list_to_xliff(texttags)
        with open(transmap_filename(self.lang, "texttags", "xliff"), "w") as outfile:
            outfile.write(str(soup))

    def exportXLSX(self, ignore_alltranslated=False, only_proofread_patterns=False):
        texttags = self._convert_to_json(ignore_alltranslated, only_proofread_patterns=only_proofread_patterns)
        filename = transmap_filename(self.lang, "texttags", "xlsx")
        to_xlsx(texttags, filename)

class IgnoreFormulaPatternIndexer(object):
    """
    Indexes patterns with only the text as key, replacing all formulas with §formula§
    """
    def __init__(self, lang, ignore_translation_state=True):
        self.lang = lang
        self.autotrans = RuleAutotranslator()
        # Preindex filter
        # Used to avoid indexing patterns with one instance
        self.preindex_ctr = Counter() # norm engl hash => count
        self.preindex_min_count = 2 # minimum instances to be considered a pattern
        self.preindex_set = set() # Compiled from preindex_ctr in clean_preindex()
        self.ignore_translation_state = ignore_translation_state
        self.index = Counter() # norm engl => count
        self.untranslated_index = Counter() # norm engl => count
        self.approved_index = defaultdict(Counter) # norm engl => translation => count ONLY for proofread versions
        self.translated_index = defaultdict(Counter) # norm engl => translation => count
        self.filename_index = defaultdict(Counter) # norm_engl => {filename: count}
        self._formula_re = re.compile(r"\$[^\$]+\$")
        self._end_invariant_re = get_end_invariant_regex()
        self._start_invariant_re = get_start_invariant_regex()
        #self._end_re
        self._img_re = get_image_regex()
        self._text = get_text_content_regex()
        self._transURLs = {} # Translation URL examples
        # NOTE: Need to run indexer TWO TIMES to get accurate results
        # as the text tags first need to be updated to get an accurate IF index
        self.texttags = read_texttag_index(lang)
        # Ignore specific whitelisted texts which are not translated

    def _normalize(self, engl):
        #t0 = time.time()
        normalized_engl = self._formula_re.sub("§formula§", engl)
        #t1 = time.time()
        normalized_engl = self._img_re.sub("§image§", normalized_engl)
        #t2 = time.time()
        normalized_engl = self._end_invariant_re.sub("", normalized_engl[::-1])[::-1]
        #t3 = time.time()
        normalized_engl = self._start_invariant_re.sub("", normalized_engl)
        #t4 = time.time()
        #print((t1 - t0), (t2 - t1), (t3 - t2), (t4 - t3))
        return normalized_engl

    def preindex(self, engl, translated=None, filename=None, approved=False):
        """
        Index
        Kind of similar to a bloom filter, but not strictly probabilistic
        (only regarding hash collision)
        and also mainta ins an exact count of strings by
        """
        #t0 = time.time()
        normalized_engl = self._normalize(engl)
        #t1 = time.time()
        h = hash_string(normalized_engl)
        #t2 = time.time()
        self.preindex_ctr[h] += 1
        #t3 = time.time()
        # Stats
        #print((t1-t0), (t2-t1), (t3-t2))
        #print(normalized_engl)

    def clean_preindex(self):
        """
        Remove patterns with too few instances from the preindex, 
        compiling:

        - preindex_ctr with a minimum number of hits
        - preindex_set: A set of hashes, which is fast to check for "x in set"
        """
        todelete = []
        # Find hits to delete
        for (hit, count) in self.preindex_ctr.most_common():
            if count < self.preindex_min_count:
                todelete.append(hit)
            else: # Will keep - add to fast set
                self.preindex_set.add(hit)
        # Log
        print("Cleaning preindex: Removing {} of {} entries - {} left".format(
            len(todelete), len(self.preindex_ctr), len(self.preindex_set)))
        # Delete all
        for todel in todelete:
            del self.preindex_ctr[todel]
        

    def add(self, engl, translated=None, filename=None, approved=False):
        normalized_engl = self._normalize(engl)
        # Check if present in preindex. If not, its not worth investigating this string any more
        h = hash_string(normalized_engl)
        if h not in self.preindex_set:
            return None
        # Count also if translated
        self.index[normalized_engl] += 1
        # Add example link
        # print(filename)
        #"{}#q={}".format(self.translationURLs[filename], to_crowdin_search_string(entry))
        # Track translation for majority selection later
        if translated is not None: # translated
            normalized_trans = self._normalize(translated)
            # Add to index
            if approved:
                self.approved_index[normalized_engl][normalized_trans] += 1
            else:
                self.translated_index[normalized_engl][normalized_trans] += 1
            # If options is set, index translated just like untranslated
            if self.ignore_translation_state and not approved:
                self.untranslated_index[normalized_engl] += 1
                self.filename_index[normalized_engl][filename] += 1
        else: # untranslated
            self.untranslated_index[normalized_engl] += 1
            self.filename_index[normalized_engl][filename] += 1

    def _convert_to_json(self, ignore_alltranslated=False, only_proofread_patterns=False):
        ifpatterns = []
        # Sort by most untranslated
        for (hit, count) in self.untranslated_index.most_common():
            total_count = self.index[hit]
            untransl_count = self.untranslated_index[hit]
            if untransl_count == 0 and ignore_alltranslated:
                continue
            # Get the most common pattern. Try proofread pattern first
            pattern_from_proofread = False
            transl = ""
            if len(self.approved_index[hit]) > 0:
                transl = self.approved_index[hit].most_common(1)[0][0]
                pattern_from_proofread = True
            elif len(self.translated_index[hit]) > 0:
                transl = self.translated_index[hit].most_common(1)[0][0]

            if only_proofread_patterns and not pattern_from_proofread:
                continue
            
            if total_count >= self.preindex_min_count:  # Ignore non-patterns
                ifpatterns.append({"english": hit,
                    "translated": transl, "count": total_count,
                    "untranslated_count": untransl_count,
                    "files": self.filename_index[hit],
                    "type": "ifpattern",
                    "translation_is_proofread": pattern_from_proofread})
        print("Found {} IF patterns".format(len(ifpatterns)))
        return ifpatterns


    def exportJSON(self, ignore_alltranslated=False, only_proofread_patterns=False):
        ifpatterns = self._convert_to_json(ignore_alltranslated, only_proofread_patterns=only_proofread_patterns)
        # Export main patterns file
        with open(transmap_filename(self.lang, "ifpatterns"), "w") as outfile:
            json.dump(ifpatterns, outfile, indent=4, sort_keys=True)

        # export file of untranslated patterns
        with open(transmap_filename(self.lang, "ifpatterns.untranslated"), "w") as outfile:
            json.dump(list(filter(lambda p: not p["translated"], ifpatterns)),
                outfile, indent=4, sort_keys=True)

    def exportXLIFF(self, ignore_alltranslated=False, only_proofread_patterns=False):
        ifpatterns = self._convert_to_json(ignore_alltranslated, only_proofread_patterns=only_proofread_patterns)
        soup = pattern_list_to_xliff(ifpatterns)
        with open(transmap_filename(self.lang, "ifpatterns", "xliff"), "w") as outfile:
            outfile.write(str(soup))

    def exportXLSX(self, ignore_alltranslated=False, only_proofread_patterns=False):
        iftags = self._convert_to_json(ignore_alltranslated, only_proofread_patterns=only_proofread_patterns)
        filename = transmap_filename(self.lang, "ifpatterns", "xlsx")
        to_xlsx(iftags, filename)


class GenericPatternIndexer(object):
    """
    Indexes arbitrary patters with unknown form by replacing ndoes
    """
    def __init__(self):
        self.index = Counter()
        self.translated_index = {}
        self.autotranslator = RuleAutotranslator()
        self._re = re.compile(r"\d")

    def add(self, engl, translated=None, filename=None, approved=False):
        # If the autotranslator can translate it, ignore it
        if self.autotranslator.translate(engl) is not None:
            return
        # Currently just remove digits
        normalized = self._re.sub("<num>", engl)
        # Add to index
        self.index[normalized] += 1
        # Add translated version to index
        if translated:
            self.translated_index[normalized] = self._re.sub("<num>", translated)

    def exportCSV(self, filename):
        with open(filename, "w") as outfile:
            for (hit, count) in self.index.most_common():
                transl = self.translated_index[hit] if hit in self.translated_index else ""
                outfile.write("\"{}\",\"{}\",{}\n".format(hit,transl,count))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('str', nargs=1, help='the string')
    args = parser.parse_args()

    idxer = IgnoreFormulaPatternIndexer("de")
    print(idxer._normalize(args.str[0]))
