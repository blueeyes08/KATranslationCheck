#!/usr/bin/env python3
# coding: utf-8
from Rules import *
from ImageAliases import readImageAliases
from ansicolor import red

imageAliases = readImageAliases("177zIAO37SY6xUBUyUE30kn5G_wR7oT-txY8XIN7cecU")

########################
### Initialize rules ###
########################
# Currently hardcoded for DE language
rules = [
    #Wikipedia-listed typos
    TextListRule("Wikipedia-listed typo", "cache/de-typos.txt", severity=Severity.standard),
    #Coordinate separated by comma instead of |
    IgnoreByMsgidRegexWrapper(r"CC\s+BY-NC-SA\s+\d\.\d",
        SimpleRegexRule("Decimal dot instead of comma inside number (high TPR)", r"\d+\.\d+", severity=Severity.info)),
    # Three cases of thin space missing in coordinate
    #The most simple case of using a decimal point instead
    IgnoreByMsgidRegexWrapper(r"^[^\$]+$", # No dollar in string
        SimpleRegexRule("Plain comma used instead of {,}", r"\d+,\d+", severity=Severity.info)),
    #Errors in thousands separation
    DynamicTranslationIdentityRule("Thousands separation via {,} (must be {\\,}) (experimental)", r"(\d+\{,\}\d+\{,\}\d+(\{,\}\d+)*)", negative=True, group=0, severity=Severity.warning), #Should be space. Comma without {} ignored.
    IgnoreByFilenameListWrapper(["de/4_low_priority/about.team.pot"],
            SimpleRegexRule("Occurrence of untranslated 'school'", r"(?<!Old-)(?<!Stanford )(?<!Ivy-League[- ])(?<!High[- ])(?<!Marlborough[- ])(?<!World[- ])\b[S]chool\b", severity=Severity.standard)),
    IgnoreByMsgidRegexWrapper(r"value: The value to constrain",
        SimpleRegexRule("Occurrence of untranslated value", r"(?<!%\()(?<!Property:)\b[Vv]alues?\b(?!\)s)(?!=)", severity=Severity.standard)),
    IgnoreByFilenameRegexWrapper(r"^de/1_high_priority_platform/_other_.pot$",
        SimpleRegexRule("Occurrence of untranslated low(er)", r"\b[Ll]ow(er)?\b", severity=Severity.standard)),
    SimpleRegexRule("Occurrence of untranslated (counter)clockwise", r"\b([Cc]ounter)?-?[Cc]clockwise\b", severity=Severity.standard),
    IgnoreByMsgidRegexWrapper(r"Attack of the Soft Purple Bunnies",
        SimpleRegexRule("Occurrence of untranslated purple (not as color specifier)", r"(?<!\\)\b[Pp]urple\b(?! Pi)", severity=Severity.standard)),
    IgnoreByMsgidRegexWrapper(r"Lygia\s+Pape", # red bottles = artwork
        SimpleRegexRule("Occurrence of untranslated red (not as color specifier)", r"(?<!\\)(?<!\\color\{)\b[Rr]ed\b(?! Delicious)(?! Robins)(?! Robbins)", severity=Severity.standard)),
    IgnoreByMsgidRegexWrapper(r"(Summer|Tree|Hour|Art|Lots|System|Museum|Institute|University)\s+of\s+(Drawing|Code|Script(ing)?|Life|Webpage|Databases|Problem|Fun|Higher\s+Education|Art|Technology)",
        IgnoreByMsgidRegexWrapper(r"(University\s+of\s+\w+|Nature of Code|cost of goods sold)", # Any "University of Maryland" etc
            SimpleRegexRule("Occurrence of untranslated of", r"\b[Oo]f\b(?!-)", severity=Severity.info))), #Also allow of inside links etc.
    IgnoreByMsgidRegexWrapper(r"([Gg]reen'?s.+[Tt]heorem|Green Elementary)",
        SimpleRegexRule("Occurrence of untranslated green (not as color specifier)", r"(?<!\\)(?<!Hank )\b[Gg]reen\b", severity=Severity.standard)),
    IgnoreByTcommentRegexWrapper("/measuring-and-converting-money-word-problems", # Ignore for conversion exercises 
        SimpleRegexRule("Occurrence of dollar as string", r"(?<!US-)[Dd]ollars?(?!ville)(?!-Schein)", severity=Severity.notice)), #US-Dollars? & Dollarville allowed
    IgnoreByFilenameRegexWrapper(r"^de/1_high_priority_platform", SimpleRegexRule("'Sie' instead of 'Du'", r"\bSie\b", severity=Severity.notice), invert=True),
    IgnoreByFilenameRegexWrapper(r"^de/1_high_priority_platform", SimpleRegexRule("'Ihre' instead of 'Deine'", r"\bIhre[rms]?\b", severity=Severity.notice), invert=True),
    # Recommended translations
    IgnoreByMsgidRegexWrapper(r"TRIANGLES", # Apparently a special code for something in javascript
        TranslationConstraintRule("'Triangle' not translated to 'Dreieck'", r"(?<!\\)triangles?", r"Dreiecke?", severity=Severity.info, flags=re.UNICODE | re.IGNORECASE)),
    # Others
    IgnoreByTcommentRegexWrapper(r"(us-customary-distance|metric-system-tutorial)",
        NegativeTranslationConstraintRule("'mile(s)' translated to 'Meile(n)' instead of 'Kilometer'", r"miles?", r"(?<!\")meilen?", severity=Severity.info, flags=re.UNICODE | re.IGNORECASE)),
    IgnoreByMsgstrRegexWrapper(r"Term", #Ignore false positives if term has any hits
        NegativeTranslationConstraintRule("'term' translated to 'Begriff' instead of 'Term'", r"\bterms?\b", r"\bBegriffe?\b", severity=Severity.standard, flags=re.UNICODE | re.IGNORECASE)),
    # HTML tags must not be removed. Rules disabled because they don't work.
    #TranslationConstraintRule("'&lt;table&gt;' not translated to '&lt;table&gt;'", r"<table", r"<table", severity=Severity.warning, flags=re.UNICODE),
    #TranslationConstraintRule("'&lt;/table&gt;' not translated to '&lt;/table&gt;'", r"</table", r"</table", severity=Severity.warning, flags=re.UNICODE),
    #TranslationConstraintRule("'&lt;div&gt;' not translated to '&lt;div&gt;'", r"<div", r"<div", severity=Severity.warning, flags=re.UNICODE),
    #TranslationConstraintRule("'&lt;/div&gt;' not translated to '&lt;/div&gt;'", r"</div", r"</div", severity=Severity.warning, flags=re.UNICODE),
    #TranslationConstraintRule("'&lt;span&gt;' not translated to '&lt;span&gt;'", r"<span", r"<span", severity=Severity.warning, flags=re.UNICODE),
    #TranslationConstraintRule("'&lt;/span&gt;' not translated to '&lt;/span&gt;'", r"</span", r"</span", severity=Severity.warning, flags=re.UNICODE),
    # Machine-readable stuff must be identical in the translation
    ExactCopyRule("All image URLs must match in order", r"!\[\]\s*\([^\)]+\)", severity=Severity.dangerous, aliases=imageAliases),
    ExactCopyRule("All image URLs must match in order (with translation)", r"!\[[^\]](\]\s*\([^\)]+\))", severity=Severity.info, aliases=imageAliases, group=1),
    ExactCopyRule("All numeric digits must match in order", r"(?<!powers of )(?<!\#)\d+(?!\d)(?!rd)(?!-step)(?!-digit)(?!-stellig)(?!-stellige)(?!-stelligen)(?!\. )", severity=Severity.dangerous, aliases=imageAliases), # Avoid image URLs matching
    DynamicTranslationIdentityRule("Non-identical whitespace before image (auto-translate) (experimental)", r"(\\n(\\n|\s|\*)*!\[)", group=0, severity=Severity.notice),
]

rules, rule_errors = readRulesFromGoogleDocs("1DWKXjktzuyf0Sxats88TszKlETRrbQ5o3hQARrZ9_EY", rules)

if __name__ == "__main__":
    print("Counting %d rules" % len(rules))
