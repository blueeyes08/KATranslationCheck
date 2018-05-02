#!/usr/bin/env python3
from bottle import run, request, response, Bottle, static_file
import simplejson as json
import random
import bs4
import dbm.dumb as dbm
from collections import namedtuple, Counter
from AutoTranslateCommon import transmap_filename
from XLIFFReader import parse_xliff_file

db = dbm.open("kagame.dbm", flag='c')

app = Bottle()

Translation = namedtuple("Translation", ["id", "source", "target"])

availableStrings = None
fileid = None
targetlang = ""
stringIDMap = {} # ID => string
# Client vote counter
clientVotes = Counter()

def extract_strings_from_xliff_soup(filename, soup):
    """
    Remove both untranslated and notes from the given soup.
    For the untranslated elements, in
    """
    results = []

    global fileid
    global targetlang
    fileid = soup.xliff.file.attrs["id"]
    targetlang = soup.xliff.file.attrs["target-language"].partition("-")[0]

    for trans_unit in soup.xliff.file.body.children: #body.find_all("trans-unit"):
        # Ignore strings
        if not isinstance(trans_unit, bs4.element.Tag):
            continue

        # Ignore other tags
        if trans_unit.name != "trans-unit":
            print("Encountered wrong tag: {}".format(trans_unit.name))
            continue

        source = trans_unit.source
        target = trans_unit.target
        # Broken XLIFF?
        if target is None:
            print(trans_unit.prettify())
            continue
        note = trans_unit.note
        is_untranslated = ("state" in target.attrs and target["state"] == "needs-translation")
        is_approved = ("approved" in trans_unit.attrs and trans_unit["approved"] == "yes")
        strid = trans_unit["id"]

        engl = source.text
        translated = target.text

        # only suggested strings
        if not is_untranslated and not is_approved:
            results.append(Translation(strid, engl, translated))

    return results

@app.hook('after_request')
def enable_cors():
    """
    You need to add some headers to each request.
    Don't use the wildcard '*' for Access-Control-Allow-Origin in production.
    """
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

@app.route('/api/strings')
def stringsAPI():
    ofs = int(request.query.offset)
    #choices = availableStrings[ofs:ofs+25]
    choices = [random.choice(availableStrings) for i in range(25)]
    response.content_type = 'application/json'
    return json.dumps(choices)

@app.post('/api/submit')
def submitAPI():
    cid = int(request.forms.get('client'))
    string = request.forms.get('string')
    score = request.forms.get('score')
    db["{}:{}".format(string, cid)] = score
    # Update stats
    clientVotes[cid] += 1
    # Find rank of user
    rank = 1
    for client, _ in clientVotes.most_common():
        if client == cid:
            break
        rank += 1
    return {"rank": rank, "count": clientVotes[cid]}

@app.get('/api/db')
def dbAPI():
    # Sort into separate upvotes and downvotes
    ctrPlus = Counter()
    ctrMinus = Counter()
    ctrVotes = Counter()
    ctrSkip = Counter()
    for sid, score in db.items():
        string, _, cid = sid.decode("utf-8").partition(":")
        string = int(string) # Crowdin IDs are numeric
        try:
            score = int(score.decode("utf-8"))
        except ValueError:
            continue
        if score > 0:
            ctrPlus[string] += score
        elif score == 0:
            ctrSkip[string] += 1
        else:
            ctrMinus[string] += score
        ctrVotes[string] += 1

    response.content_type = 'application/json'
    # Reformat to list of objs
    return json.dumps([{
        "url": "https://crowdin.com/translate/khanacademy/{}/enus-{}#{}".format(fileid, targetlang, strid),
        "id": strid,
        "english": stringIDMap[strid].source,
        "translated": stringIDMap[strid].target,
        "upvotes": ctrPlus[strid],
        "downvotes": ctrMinus[strid],
        "skip": ctrSkip[strid],
        "votes": cnt
    } for strid, cnt in ctrVotes.most_common()])

@app.get("/")
def index():
    return static_file("index.html", root='./game/ui')

def compute_client_vote_count():
    """
    from the db compute how many votes each client has taken
    """
    global clientVotes
    clientVotes = Counter()
    voteSum = 0
    for sid, score in db.items():
        cid = sid.decode("utf-8").partition(":")[2]
        cid = int(cid) # IDs are numeric
        clientVotes[cid] += 1
        voteSum += 1
    print("Total number of votes: {}".format(voteSum))


def run_game_server(args):
    global availableStrings
    global stringIDMap
    compute_client_vote_count()
    print()

    soup = parse_xliff_file(args.file)
    availableStrings = extract_strings_from_xliff_soup(args.file, soup)
    # Remap strings
    stringIDMap = {
        int(ti.id): ti
        for ti in availableStrings
    }

    print("Found {} strings".format(len(availableStrings)))
    run(app, host='0.0.0.0', port=9922)
