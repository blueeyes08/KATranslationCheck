import itertools

def chunks(l, n=1000):
    """
    Yield successive n-sized chunks from l.
    https://stackoverflow.com/a/312464/2597135
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

def get_chunk(client, keys):
    """
    Get a single chunk
    """
    missing = []
    vals = client.get_multi(keys)
    return vals, missing

def datastore_get_all(executor, client, keys):
    all_missing = []
    all_vals = []
    for vals, missing in executor.map(lambda chunk: get_chunk(client, chunk), chunks(keys)):
        all_missing += missing
        all_vals += vals
    return all_missing, all_vals
