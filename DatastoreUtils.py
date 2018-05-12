import itertools
from concurrent.futures import ThreadPoolExecutor

def _chunks(l, n=1000):
    """
    Yield successive n-sized chunks from l.
    https://stackoverflow.com/a/312464/2597135
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

def _get_chunk(client, keys):
    """
    Get a single chunk
    """
    missing = []
    vals = client.get_multi(keys, missing=missing)
    return vals, missing

class DatastoreChunkClient(object):
    """
    Provides a thin wrapper around a Google Cloud Datastore client providing means
    of reading nd
    """
    def __init__(self, client, executor=None):
        self.client = client
        if executor is None:
            executor = ThreadPoolExecutor(16)
        self.executor = executor
    
    def get_multi(self, keys):
        """
        Thin wrapper around client.get_multi() that circumvents
        the 1000 read requests limit by doing 1000-sized chunked reads
        in parallel using self.executor.

        Returns (values, missing).
        """
        all_missing = []
        all_vals = []
        for vals, missing in self.executor.map(lambda chunk: _get_chunk(self.client, chunk), _chunks(keys, 1000)):
            print(vals, missing)
            all_vals += vals
            all_missing += missing
        return all_vals, all_missing

    def put_multi(self, entities):
        """
        Thin wrapper around client.put_multi() that circumvents
        the 400 read requests limit by doing 400-sized chunked reads
        in parallel using self.executor.

        Returns (values, missing).
        """
        for vals, missing in self.executor.map(lambda chunk: self.client.put_multi(chunk), _chunks(entities, 400)):
            pass
