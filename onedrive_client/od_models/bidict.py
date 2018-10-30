try:
    from bidict import loosebidict
except ImportError:
    import bidict
    class loosebidict(bidict.bidict):
        on_dup_val = bidict.OVERWRITE
