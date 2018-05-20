#!/usr/bin/env python3
"""
Update files by individually exporting from Crowdin.

This script assumes that a full file tree is already present (e.g. in the "de" directory).
Non-present files will NOT be updated.
"""
import requests
import simplejson as json
import simplejson
import gc
import os
import errno
import os.path
import datetime
import functools
from ansicolor import black, green, blue
from retry import retry
from multiprocessing import Pool
from Languages import getCachedLanguageMap, findAvailableLanguages

languageIDs = getCachedLanguageMap()

def translationFilemapCacheFilename(lang="de"):
    return os.path.join("cache", "translation-filemap-{0}.json".format(lang))

def loadUsernamePassword():
    """Load the crowdin credentials from the config JSON file"""
    try:
        with open("crowdin-credentials.json") as infile:
            data = json.load(infile)
            return data["username"], data["password"]
    except FileNotFoundError:
        print(red("Could not find crowdin-credentials.json. Please create that file from crowdin-credentials-template.json!", bold=True))


# Globally load credentials

# Perform login
def getCrowdinSession(credentials=None, domain="https://crowdin.com", fullauto_account=False):
    s = requests.Session()
    if credentials is None:
        credentials = loadUsernamePassword()
    username, password = credentials
    if fullauto_account:
        username = "Babelfish2"
    s.cookies["csrf_token"] = "79ywqnyhig"
    s.headers["X-Csrf-Token"] = "79ywqnyhig"
    s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36"
    response = s.get("{}/login".format(domain))
    loginData = {"password": password, "redirect": "/profile", "login": username}
    headers = {"Referer": "https://crowdin.com/login", "Accept": "application/json"}
    response = s.post("{}/login/submit".format(domain), data=loginData, headers=headers, stream=False)
    # CSRF cookie is randomly generated in javascript. We can just use a fixed token here.
    #print(response.__dict__)
    #print(s.__dict__)

    response = s.get("https://crowdin.com/profile")
    return s

@retry(tries=8)
def downloadTranslationFilemap(lang="de"):
    """
    Create a filename -> info map for a given Crowdin.
    The info contains all crowdin info plus the "id" property,
    containing the numeric file ID on Crowdin and the "path" property
    containing the path inside the language directory.
    """
    langid = getCachedLanguageMap()[lang]
    # Extract filemap
    response = requests.get("https://crowdin.com/project/khanacademy/de/get_files_tree?language_id={}".format(langid))
    filesTree = response.json()["files_tree"]
    # Build map for the directory structure
    directoryMap = {
        v["id"]: v["name"] + "/"
        for k, v in filesTree.items()
        if v["node_type"] == "0"} # 0 -> directory
    directoryMap["0"] = ""
    # Filter only POT. Create filename -> object map with "id" property set
    dct = {
        v["name"]: dict(v.items() | [("id", int(v["id"])), ("path", directoryMap[v["parent_id"]] + v["name"])])
        for k, v in filesTree.items()
        if v["name"].endswith(".pot")}
    # Parse glossary
    #dct.update({
    #    "glossary.pot": dict([("id", int(v["id"])), ("path", "glossary.pot")])
    #    for k, v in projectFiles.items()
    #    if v["type"] == "glossary"})
    return dct


@retry(tries=8, delay=5.0)
def performPOTDownload(lang, argtuple, project="khanacademy"):
    # Extract argument tuple
    fileid, filepath = argtuple
    exportTranslationFile(lang, fileid, filepath, asXLIFF=False, project=project)

@retry(tries=8, delay=5.0)
def performXLIFFDownload(lang, argtuple, project="khanacademy"):
    # Extract argument tuple
    fileid, filepath = argtuple
    exportTranslationFile(lang, fileid, filepath, asXLIFF=True, project=project)

def exportTranslationFile(lang, fileid, filepath, asXLIFF=True, project="khanacademy"):
    """
    Explicitly uncurried function that downloads a single Crowdin file
    to a filesystem file. fileid, filepath
    """
    urlPrefix = "https://crowdin.com/project/{}/{}/{}/export".format(project, lang, fileid)
    # Initialize session
    s = getCrowdinSession()
    # Trigger export
    params = {"as_xliff": "1"} if asXLIFF else {}
    exportResponse = s.get(urlPrefix, headers={"Accept": "application/json"}, params=params)
    try:
        exportJSON = exportResponse.json()
        if exportResponse.json()["success"] != True:
            raise Exception("Crowdin export failed: " + exportResponse.text)
    except simplejson.scanner.JSONDecodeError:
        #print(exportResponse.text)
        return
    # Trigger download
    # Store in file
    with open(filepath, "w+b") as outfile:
        response = s.get(exportJSON["url"], stream=True)

        if not response.ok:
            raise Exception("Download error")

        for block in response.iter_content(1024):
            outfile.write(block)
    print(green("Downloaded %s" % filepath))

def findExistingPOFiles(lang="de", directory="de"):
    """Find PO files which already exist in the language directory"""
    for (curdir, _, files) in os.walk(directory):
        for f in files:
            #Ignore non-PO files
            if not f.endswith(".po"): continue
            #Add to list of files to process
            yield os.path.join(curdir, f)

def updateTranslationFilemapCache(lang="de"):
    """Re-download the translation filemap cache"""
    print(black("Updating translation filemap for {0}".format(lang), bold=True))
    filename = translationFilemapCacheFilename(lang)
    with open(filename, "w") as outfile:
        translation_filemap = downloadTranslationFilemap(lang)
        json.dump(translation_filemap, outfile)
    return translation_filemap

def getTranslationFilemapCache(lang="de",  forceUpdate=False):
    # Enforce update if file does not exist
    filename = translationFilemapCacheFilename(lang)
    if not os.path.isfile(filename) or forceUpdate:
        updateTranslationFilemapCache(lang)
    # Read filename cache
    with open(filename) as infile:
        return json.load(infile)

def updateTranslations(args):
    if args.all_languages:
        for language in findAvailableLanguages():
            print(green("Downloading language {}".format(language), bold=True))
            args.language = language
            updateTranslation(args)
            # Cleanup objects (especially the pool) left from last language
            gc.collect()
    else: # Single language
        updateTranslation(args)

def updateTranslation(args):
    # Get map that contains (besides other stuff)
    #  the crowdin ID for a given file
    translationFilemap = getTranslationFilemapCache(args.language, args.force_filemap_update)

    # Collect valid downloadable files for parallel processing
    fileinfos = []
    for filename, fileinfo in translationFilemap.items():
        if "draft" in filename:
            continue
        filepath = os.path.join("cache", args.language, fileinfo["path"])
        # Handle XLIFF filenames
        if not args.po:
            filepath = filepath.replace(".pot", ".xliff")
        # Create dir if not exists
        try:
            os.makedirs(os.path.dirname(filepath))
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                pass
            else:
                raise
        fileid = fileinfo["id"]
        # Apply filter
        filtered = False
        for subfilt1 in (args.filter or []):
            for subfilt2 in subfilt1: # argparse creates nested list
                if subfilt2 not in filepath and subfilt2 not in filepath.replace(".xliff", ".pot"):
                    filtered = True
        if filtered:
            continue
        # Add to list
        fileinfos.append((fileid, filepath))
    # Curry the function with the language
    performDownload = functools.partial(performPOTDownload if args.po else performXLIFFDownload, args.language)
    # Perform parallel download
    if args.num_processes > 1:
        pool = Pool(args.num_processes)
        pool.map(performDownload, fileinfos)
    else:
        for t in fileinfos:
            # Perform download
            performDownload(t)
    #Set download timestamp
    timestamp = datetime.datetime.now().strftime("%y-%m-%d %H:%M:%S")
    with open("lastdownload.txt", "w") as outfile:
        outfile.write(timestamp)

def downloadCrowdinById(session, crid, lang="de"):
    if lang in languageIDs:
        langId = languageIDs[lang]
    else:  # Fallback -- wont really work
        print(red("Error: Language unknown: {0}".format(lang), bold=True))
        langId = 11  #de
    url = "https://crowdin.com/translation/phrase?id={0}&project_id=10880&target_language_id={1}".format(crid, langId)
    response = session.get(url)
    try:
        jsondata = response.json()["data"]
        msgid = jsondata["translation"]["text"]
        msgstr = jsondata["top_suggestion"]
        comment = jsondata["translation"]["context"]
        filename = jsondata["translation"]["file_path"][1:]
    except:
        errstr = "[Retrieval error while fetching {0}]".format(url)
        return errstr, errstr, errstr, None
    return msgid, msgstr, comment, filename

if __name__ == "__main__":
    # Create new session
    s = getCrowdinSession(domain="https://crowdin.com")
    #print(s.__dict__)
    print(downloadCrowdinById(s, "41065"))
    # Load phrase

def get_translation_urls(lang, xliff=True):
    """
    Get a map from filename to "where to translate on Crowdin" URL
    """
    translationFilemapCache = getTranslationFilemapCache(lang)
    return {
        v["path"].replace(".pot", ".xliff" if xliff else ".pot"):
            "https://crowdin.com/translate/khanacademy/{}/enus-{}".format(
                v["id"], lang.partition("-")[0])
        for v in translationFilemapCache.values()
    }
