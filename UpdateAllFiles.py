#!/usr/bin/env python3
"""
Update files by individually exporting from Crowdin.

This script assumes that a full file tree is already present (e.g. in the "de" directory).
Non-present files will NOT be updated.
"""
import requests
import json
import re
import os
import os.path
from multiprocessing import Pool
from bs4 import BeautifulSoup
from ansicolor import red, black, blue, green

translationFilemapCacheFilename = "translation-filemap.cache.json"

def loadUsernamePassword():
    """ """
    with open("crowdin-credentials.json") as infile:
        return json.load(infile)

# Globally load credentials
crowdingCredentials = loadUsernamePassword()

# Perform login
def getCrowdinSession():
    s = requests.Session()
    username = crowdingCredentials["username"]
    password = crowdingCredentials["password"]
    loginData = {"password": password, "submitted": 1, "redirect": "/profile", "email_as_login": "", "login": username}
    response = s.post("http://crowdin.khanacademy.org/login", data=loginData, stream=False)
    return s

def downloadTranslationFilemap(lang="de"):
    """
    Create a filename -> info map for a given Crowdin.
    The info contains all crowdin info plus the "id" property,
    containing the numeric file ID on Crowdin.
    """
    # Extract filemap
    response = requests.get("http://crowdin.khanacademy.org/project/khanacademy/%s" % lang)
    soup = BeautifulSoup(response.text)
    scripttext = soup.find_all("script")[3].text
    jsonStr = scripttext.partition("PROJECT_FILES = ")[2]
    jsonStr = jsonStr.rpartition(", DOWNLOAD_PERMISSIONS")[0].replace("\\/", "/")
    projectFiles = json.loads(jsonStr)
    # Filter only POT. Create filename -> object map with "id" property set
    idRegex = re.compile("/khanacademy/(\d+)/enus-de")
    return {
        v["name"]: dict(v.items() | [("id", int(idRegex.match(v["editor_url"]).group(1)))])
        for k, v in projectFiles.items()
        if v["name"].endswith(".pot")}

def performPOTDownload(argtuple):
    """
    Explicitly uncurried function that downloads a single Crowdin file
    to a filesystem file. fileid, filepath
    """
    # Extract argument tuple
    fileid, filepath = argtuple
    urlPrefix = "http://crowdin.khanacademy.org/project/khanacademy/de/%s/" % str(fileid)
    # Initialize session
    s = getCrowdinSession()
    # Trigger export
    exportResponse = s.get(urlPrefix + "export", headers={"Accept": "application/json"})
    #print(exportResponse.text)
    if exportResponse.json()["success"] != True:
        raise Exception("Crowdin export failed: " + response.text)
    # Trigger download
    # Store in file
    with open(filepath, "wb") as outfile:
        response = s.get(urlPrefix + "download", stream=True)

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
    print(black("Updating translation filemap", bold=True))
    with open(translationFilemapCacheFilename, "w") as outfile:
        translation_filemap = downloadTranslationFilemap(lang)
        json.dump(translation_filemap, outfile)
        return translation_filemap

def getTranslationFilemapCache(forceUpdate=False):
    # Enforce update if file does not exist
    if not os.path.isfile(translationFilemapCacheFilename) or forceUpdate:
        updateTranslationFilemapCache()
    # Read filename cache
    with open(translationFilemapCacheFilename) as infile:
        return json.load(infile)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--language', default="de", help='The language directory to use/extract')
    parser.add_argument('-j', '--num-processes', default=1, type=int, help='Number of processes to use for parallel download')
    args = parser.parse_args()

    # Create directory
    if not os.path.isdir(args.language):
        os.mkdir(args.language)

    # Get map that contains (besides other stuff)
    #  the crowdin ID for a given file
    translationFilemap = getTranslationFilemapCache()



    # Collect valid downloadable files for parallel processing
    fileinfos = []
    for filename, fileinfo in translationFilemap.items():
        filepath = os.path.join(args.language, filename)
        fileid = fileinfo["id"]
        fileinfos.append((fileid, filepath))
    # Perform parallel download
    if args.num_processes > 1:
        pool = Pool(args.num_processes)
        pool.map(performPOTDownload, fileinfos)
    else:
        for t in fileinfos:
            performPOTDownload(t)
