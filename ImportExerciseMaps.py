#!/usr/bin/env python3
import requests
import re
import json
import traceback
import os
import itertools
from tqdm import tqdm
import concurrent.futures
from toolz.dicttoolz import valmap
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(32)

def fetch_exercise_info(lang, exercise):
    url = "https://www.khanacademy.org/api/internal/translations/exercise_strings/{}?lang={}".format(exercise, lang)
    response = requests.get(url)
    exerciseInfo = response.json()
    # Assemble string lists
    aidToStrings = defaultdict(list)
    stringidRe = re.compile("crwdns(\d+):")
    for ti in exerciseInfo["translationItems"]:
        stringid = int(stringidRe.match(ti["jiptString"]).group(1))
        aidToStrings[ti["assessmentItem"]].append(stringid)
    # Assemble exercise type map
    aidToPtype = {}
    for ptype, aids in exerciseInfo["problemTypes"].items():
        for aid in aids:
            aidToPtype[aid] = ptype
    # Extract structure map
    aidToStructure = valmap(json.loads, exerciseInfo["translatedAssessmentItems"])
    # Assemble into one list of objects
    result = {}
    aids = set(itertools.chain(aidToStrings.keys(), aidToPtype.keys(), aidToStructure.keys()))
    for aid in aids:
        result[aid] = {
            "type": aidToPtype.get(aid, None),
            "strings": aidToStrings.get(aid, []),
            "structure": aidToStructure.get(aid, []),
        }
    return result


def fetch_and_write_exercise_infos(lang, exercise):
    # Create dir
    directory = os.path.join("exercises", lang)
    os.makedirs(directory, exist_ok=True)
    filename = os.path.join(directory, "exercise.json")
    # Fetch
    try:
        exerciseInfo = fetch_exercise_info(lang, exercise)
        # Write
        with open(filename, "w") as outfile:
            json.dump(exerciseInfo, outfile)
        print("Written {}".format(exercise))
    except Exception as ex:
        traceback.print_exc()

def fetch_all_exercises(lang):
    response = requests.get("https://www.khanacademy.org/api/internal/translate/progress_nodes?lang={}".format(lang))
    nodes = response.json()["nodes"]
    futures = [executor.submit(fetch_and_write_exercise_infos, lang, key) for key in nodes["exercises"].keys()]
    for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
        f.result() # Ignore

fetch_all_exercises("de")