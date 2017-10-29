#!/usr/bin/env python3
import re as re
from collections import Counter, defaultdict
from ansicolor import red

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

class TextTagIndexer(object):
    def __init__(self):
        self.index = Counter()
        self.translated_index = {}
        self._re = re.compile(r"\\text\{\s*([^\}]+)\}")

    def add(self, engl, translated=None):
        # Find english hits and possible hits in target lang to be able to match them!
        engl_hits = self._re.findall(engl)
        # Just make sure that transl_hits has the same length as index
        transl_hits = engl if translated is None else self._re.findall(translated)
        # Find hits in english
        for engl_hit, transl_hit in zip(engl_hits, transl_hits):
            engl_hit = engl_hit.strip()
            transl_hit = transl_hit.strip()
            self.index[engl_hit] += 1
            # If untranslated, do not index translions
            if translated is not None and transl_hit:
                self.translated_index[engl_hit] = transl_hit
        #except Exception as ex:
        #    print(red("Failed to index '{}' --> {}: {}".format(engl, translated, ex) bold=True))

    def __len__(self):
        return len(self.index)

    def exportCSV(self, filename):
        with open(filename, "w") as outfile:
            for (hit, count) in self.index.most_common():
                transl = self.translated_index[hit] if hit in self.translated_index else ""
                # engl,translated(or ""),count
                outfile.write("\"{}\",\"{}\",{}\n".format(hit, transl, count))


class PatternIndexer(object):
    def __init__(self):
        self.index = Counter()
        self._re = re.compile(r"\d")

    def add(self, engl, translated):
        # Currently just remove digits
        normalized = self._re.sub("", engl)
        self.index[normalized] += 1

    def exportCSV(self, filename):
        with open(filename, "w") as outfile:
            for (hit, count) in self.index.most_common():
                if count == 1:  # Ignore non-patterns
                    continue
                outfile.write("\"{}\",{}\n".format(hit, count))

if __name__ == "__main__":
    tti = TextTagIndexer()
    source = "john counts $6\\text{balls and }4\\text{orchs and}12\\text{spears}$"
    target = "john räknar $6\\text{bollar och }4\\text{orcher och}12\\text{spjut}$"
    tti.add(source, target)
    print(tti.index)
    print(tti.translated_index)