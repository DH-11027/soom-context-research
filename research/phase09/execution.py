"""Four fixed entry paths. No audit, gold, monkeypatch or internal timer here."""
from bindings import P8E, P8R
import off_fresh
import off_selective

METHODS = ("fresh_instrumented", "fresh_uninstrumented",
           "selective_instrumented", "selective_uninstrumented")


def components(method):
    if method == "fresh_instrumented":
        return lambda: None, lambda public, cache, namespace: P8E.run("fresh", public, cache, namespace)
    if method == "fresh_uninstrumented":
        return lambda: None, lambda public, cache, namespace: off_fresh.run(public, "text_scoped")
    if method == "selective_instrumented":
        return P8R.SelectiveCache, lambda public, cache, namespace: P8E.run("selective", public, cache, namespace)
    if method == "selective_uninstrumented":
        return off_selective.SelectiveCache, lambda public, cache, namespace: off_selective.run(public, cache, namespace=namespace)
    raise ValueError(method)


def workload(prepared, factory, run):
    """Caller surrounds the whole call by exactly one external timer interval.

    prepared contains only tuple(stream(tuple(public,namespace), ...)), with
    whitelisted public fields. Cache is new per stream; its construction and
    destruction are inside. Outputs are produced and discarded identically.
    """
    for stream in prepared:
        cache = factory()
        for public, namespace in stream:
            run(public, cache, namespace)
        del cache

