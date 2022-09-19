
from typing import Dict, Union, cast
from urllib.request import urlopen

try:
    import tqdm  # type: ignore
    tqdm_available = True
except ImportError:
    tqdm_available = False


def fetch_url(url: str, desc: Union[str, None] = None) -> bytearray:
    with urlopen(url) as urlreq:
        if tqdm_available and (urlreq.headers['content-length'] is not None):
            size = int(urlreq.headers['content-length'])
            remaining = size
            data = bytearray()
            with tqdm.tqdm(total=size, unit='B', unit_scale=True, unit_divisor=1024, desc=desc) as t:
                while remaining > 0:
                    blocksize = min(remaining, 1024 * 128)
                    data.extend(urlreq.read(blocksize))
                    remaining = remaining - blocksize
                    t.update(blocksize)
            return data
        else:
            print('Fetching: ' + url)
            return cast(bytearray, urlreq.read())


download_cache: Dict[str, bytearray] = {}


def fetch_url_cached(url: str, desc: str = '') -> bytearray:
    data = download_cache.get(url, None)
    if data is None:
        data = fetch_url(url, desc)
        download_cache[url] = data
    return data
