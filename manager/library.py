"""Small source-aware library projection used by manager clients."""
from .sources import SourceStore


def descriptors(store: SourceStore):
    result = []
    for source in store.records:
        for mod in store.load(source['id']).mods:
            result.append(dict(mod, source_id=source['id'], selected=mod['id'] in source['selected_ids']))
    return result
