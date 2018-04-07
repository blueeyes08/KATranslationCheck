#!/usr/bin/env python3
from AutoTranslationIndexer import *
from AutoTranslationTranslator import *
import os.path
import os
import sys
import traceback
from AutoTranslatePostproc import *
from tqdm import tqdm
from ansicolor import black, blue, green
from UpdateAllFiles import *
from XLIFFUpload import *
import concurrent.futures
from toolz.functoolz import identity
import gc
import bs4

def findXLIFFFiles(directory, filt=[], lang="de"):
    """
    Get a list of PO files (.po / .pot) which are present in the directory.

    filter is a nested list from argparse which defined
    """
    transFilemap = getTranslationFilemapCache(lang)
    if os.path.isfile(directory): #Single file>=
        poFilenames = [directory]
    else:
        xliffFiles = {} # name => crowdin file id
        #Recursively iterate directory, ignore everythin except *.po
        for (curdir, _, files) in os.walk(directory):
            # Ignore non-XLIFF files
            for f in filter(lambda f: f.endswith(".xliff"), files):
                #Add to list of files to process
                filename = os.path.join(curdir, f)
                basename = os.path.basename(filename)
                # Filter based on custom filter
                filtered = False # true => ignore this file
                # Ignore files not in filter, if any
                for subfilt1 in (filt or []):
                    for subfilt2 in subfilt1: # argparse creates nested list
                        if subfilt2 not in filename and subfilt2 not in filename.replace(".xliff", ".pot"):
                            filtered = True
                if not filtered: # passed filter
                    key = basename.replace(".xliff", ".pot")
                    # For some reason sometimes mapping does not work correctly
                    if key in transFilemap:
                        xliffFiles[filename] = transFilemap[key]["id"]
                    else:
                        print(red("Can't find {} in filemap - ignoring file".format(key), bold=True))
    return xliffFiles

def parse_xliff_file(filename):
    with open(filename) as infile:
        return BeautifulSoup(infile, "lxml-xml")

def export_xliff_file(soup, filename):
    with open(filename, "w") as outfile:
        outfile.write(str(soup))

def process_xliff_soup(filename, soup, autotranslator, indexer, autotranslate=True, preindex=False, overwrite=False, postproc=identity):
    """
    Remove both untranslated and notes from the given soup.
    For the untranslated elements, in
    """
    overall_count = 0
    untranslated_count = 0
    translated_count = 0
    autotranslated_count = 0
    # Iterate over all translatable strings
    body = soup.xliff.file.body

    # Resulting elements
    results = []

    indexFN = indexer.preindex if preindex else indexer.add

    for trans_unit in body.children: #body.find_all("trans-unit"):
        # Ignore strings
        if not isinstance(trans_unit, bs4.element.Tag):
            continue

        # Ignore other tags
        if trans_unit.name != "trans-unit":
            print("Encountered wrong tag: {}".format(trans_unit.name))
            continue

        overall_count += 1
        source = trans_unit.source
        target = trans_unit.target
        # Broken XLIFF?
        if target is None:
            print(trans_unit.prettify())
            continue
        note = trans_unit.note
        is_untranslated = ("state" in target.attrs and target["state"] == "needs-translation")
        is_approved = ("approved" in trans_unit.attrs and trans_unit["approved"] == "yes")

        can_overwrite = not is_untranslated and not is_approved
        will_overwrite = overwrite and can_overwrite

        engl = source.text
        translated = target.text
        # Index tags in the indexer (e.g. to extract text tags)
        # This is done even if they are translated
        # NOTE: This does index or preindex (chosen outside of the loop)
        indexFN(engl, None if is_untranslated else translated, filename=filename, approved=is_approved)

        # For indexing run, ignore autotranslator altogether
        if not autotranslate and not will_overwrite:
            trans_unit.decompose()
            continue

        # Remove entire tag if translated (or suggested)
        if not is_untranslated and not will_overwrite:
            trans_unit.decompose()
            translated_count += 1
            continue  # Dont try to autotranslate etc

        untranslated_count += 1
        # Remove HUGE note text to save space
        if note:
            note.decompose()
        # Remove empty text inside the <trans-unit> element to save space
        for c in trans_unit.contents:
            c.extract()

        # Now we can try to autotranslate
        try:
            autotrans = postproc(autotranslator.translate(engl))
        except:
            print(black("Autotranslate fail for string '{}'".format(engl), bold=True))
            traceback.print_exception(*sys.exc_info())
            autotrans = None

        if autotrans is None:  # Could not translate
            # Remove from output file to conserve space
            trans_unit.decompose()
        else:  # Could autotranslate
            # Store autotranslation in XML
            target["state"] = "translated"
            target.string = autotrans
            autotranslated_count += 1
            # Add to result list
            results.append(trans_unit.extract())

    # Remove empty text content of the body to conserve spce
    body.contents = results

    # Print stats
    if autotranslate:
        if untranslated_count != 0:  # Don't print "0 of 0 strings"
            print(black("Autotranslated {} of {} untranslated strings ({} total) in {}".format(
                autotranslated_count, untranslated_count, overall_count, os.path.basename(filename))))
    else:
        print(black("{} {} strings in {}".format(
            "Preindexed" if preindex else "Indexed",
            overall_count, os.path.basename(filename))))


    return autotranslated_count

def readAndProcessXLIFF(lang, filename, fileid, indexer, autotranslator, upload=False, approve=False, autotranslate=True, preindex=False, overwrite=False, fullauto_account=False, postproc=identity):
    soup = parse_xliff_file(filename)
    autotranslated_count = process_xliff_soup(filename, soup, autotranslator, indexer, autotranslate=autotranslate, preindex=preindex, overwrite=overwrite, postproc=postproc)
    # If we are not autotranslating, stop here, no need to export
    if not autotranslate:
        return 0
    # Export XLIFF
    outdir = "output-{}".format(lang)
    outfilename = filename.replace("cache/{}".format(lang), outdir)
    # Create directories & export
    if autotranslated_count > 0:
        os.makedirs(os.path.dirname(outfilename), exist_ok=True)
        #print(black("Exporting to {}".format(outfilename), bold=True))
        export_xliff_file(soup, outfilename)
    # Upload if enabled
    if upload and autotranslated_count > 0:
        basename = os.path.basename(filename)
        print(blue("Uploading {} (approve={})...".format(basename, approve)))
        upload_file(outfilename, fileid, auto_approve=approve, lang=lang, fullauto_account=fullauto_account, duplicates=overwrite)
        print(green("Uploaded {}".format(basename)))
    return autotranslated_count


def readAndProcessXLIFFRunner(*args, **kwargs):
    result = 0
    try:
        result = readAndProcessXLIFF(*args, **kwargs)
    except:
        traceback.print_exception(*sys.exc_info())
    gc.collect()
    return result

def run(executor, xliffs, *args, **kwargs):

    # Run XLIFF parser in parallel
    futures = [
        executor.submit(readAndProcessXLIFFRunner, *args, filename=filepath, fileid=fileid, **kwargs)
        for filepath, fileid in xliffs.items()
    ]
    # stats
    kwargs = {
        'total': len(futures),
        'unit': 'it',
        'unit_scale': True,
        'leave': True
    }
    autotranslated_count = 0
    for future in tqdm(concurrent.futures.as_completed(futures), **kwargs):
        autotranslated_count += future.result()

    return autotranslated_count

def autotranslate_xliffs(args):
    # Plausibility checks
    if args.full_auto and args.approve:
        print(red("Must not use --approve together with --full-auto, too dangerous!", bold=True))
        sys.exit(1)


    os.makedirs("output-{}".format(args.language), exist_ok=True)

    ignore_alltranslated = args.index_ignore_translated

    # Initialize pattern indexers
    text_tag_indexer = TextTagIndexer(args.language) if args.index else None
    pattern_indexer = None #GenericPatternIndexer() if args.index else None
    ignore_formula_pattern_idxer = IgnoreFormulaPatternIndexer(args.language) if args.index else None
    indexer = CompositeIndexer(text_tag_indexer, pattern_indexer, ignore_formula_pattern_idxer)

    # Initialize autotranslators
    if not args.index: # Autotranslate if not indexing
        rule_autotranslator = RuleAutotranslator() if not args.patterns else None
        full_autotranslator = FullAutoTranslator(args.language, args.limit) if args.full_auto else None
        ifpattern_autotranslator = IFPatternAutotranslator(args.language, args.limit) if args.patterns else None
        name_autotranslator = NameAutotranslator(args.language) if args.name_autotranslate else None
        autotranslator = CompositeAutoTranslator(rule_autotranslator,
            full_autotranslator, name_autotranslator, ifpattern_autotranslator)
    else: # Index, not autotranslate
        autotranslator = CompositeAutoTranslator()

    postproc = identity
    if args.comma:
        postproc = decimal_comma_replace

    # Process in parallel
    # Cant use process pool as indexers currently cant be merged
    executor = concurrent.futures.ThreadPoolExecutor(args.num_processes)

    xliffs = findXLIFFFiles("cache/{}".format(args.language), filt=args.filter, lang=args.language)

    if args.index:
        # Two pass: First preindex then
        # See IgnoreFormulaPatternIndex for reason
        # 1st pass
        run(executor, xliffs, lang=args.language, indexer=indexer, autotranslator=autotranslator, upload=args.upload, approve=args.approve, autotranslate=False, preindex=True, overwrite=args.overwrite, fullauto_account=args.full_auto, postproc=postproc)
        print("------------------------------")
        print("Preindex finished. Indexing run")
        print("------------------------------\n")
        indexer.clean_preindex()
        print()
        run(executor, xliffs, lang=args.language, indexer=indexer, autotranslator=autotranslator, upload=args.upload, approve=args.approve, autotranslate=False, preindex=False, overwrite=args.overwrite, fullauto_account=args.full_auto, postproc=postproc)
    else: # translation run. Simple single pas
        autotranslated_count = run(executor, xliffs,
            lang=args.language, indexer=indexer, autotranslator=autotranslator, upload=args.upload, approve=args.approve, autotranslate=True, overwrite=args.overwrite, fullauto_account=args.full_auto)
        print("\nAuto-translated {} strings !\n".format(autotranslated_count))

    # Export indexed
    if args.index:
        print("Exporting indices...")
        text_tag_indexer.exportJSON(ignore_alltranslated, only_proofread_patterns=args.only_approved)
        text_tag_indexer.exportXLIFF(ignore_alltranslated, only_proofread_patterns=args.only_approved)
        text_tag_indexer.exportXLSX(ignore_alltranslated, only_proofread_patterns=args.only_approved)
        ignore_formula_pattern_idxer.exportJSON(ignore_alltranslated, only_proofread_patterns=args.only_approved)
        ignore_formula_pattern_idxer.exportXLSX(ignore_alltranslated, only_proofread_patterns=args.only_approved)
        ignore_formula_pattern_idxer.exportXLIFF(ignore_alltranslated, only_proofread_patterns=args.only_approved)
        #pattern_indexer.exportCSV(os.path.join("output-" + args.language, "patterns.csv"))
    if "ifpattern_autotranslator" in locals() and ifpattern_autotranslator is not None:
        print("Could not translate {} strings due to missing text tags".format(
            ifpattern_autotranslator.textTagMissingCounter))
        ifpattern_autotranslator.export_missing_tags("transmap/{}-missing-tags.json".format(args.language))
    if args.update_index_source:
        update_crowdin_index_files(args.language)

    if args.update_index:
        pass
