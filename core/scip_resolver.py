"""Loads a `scip print --json` index and resolves AWS-SDK call sites by symbol.

Replaces code2DFD's grep-based search for the SNS/SQS extractor: symbol identity
instead of text match, and instance-following (seed library class -> developer
instance identifier -> its method-call sites) — the code2DFD paper's "iterative
keyword search", done as a symbol-table lookup.
"""
import json


class Occurrence:
    __slots__ = ("rel_path", "symbol", "line", "start", "end", "is_def")

    def __init__(self, rel_path, symbol, rng, roles):
        self.rel_path = rel_path
        self.symbol = symbol
        self.line = rng[0] if rng else 0
        self.start = rng[1] if rng and len(rng) > 1 else 0
        self.end = rng[2] if rng and len(rng) > 2 else 0
        self.is_def = bool(roles & 1)

    @property
    def span(self):
        return (self.start, self.end)


class ScipIndex:
    def __init__(self, occurrences):
        self._occ = occurrences  # list[Occurrence]

    @classmethod
    def load(cls, path):
        data = json.load(open(path))
        occ = []
        for doc in data.get("documents", []):
            rel = doc.get("relative_path") or doc.get("relativePath", "?")
            for o in doc.get("occurrences", []):
                occ.append(Occurrence(rel, o.get("symbol", ""),
                                      o.get("range", [0]), o.get("symbol_roles", 0)))
        return cls(occ)

    def occurrences(self, descriptor):
        """All occurrences whose symbol id contains '/<descriptor>' (structured suffix).

        `descriptor` is like 'PublishCommand#' — matched as '/PublishCommand#' so the
        declaring filename (e.g. `PublishCommand.d.ts`) does not cause a false hit.
        """
        needle = "/" + descriptor
        return [o for o in self._occ if needle in o.symbol]

    def _instance_symbol_at(self, rel_path, line):
        """The instance-variable definition symbol declared on (rel_path, line).

        Skips whole-file/module symbols (which end with `` ` `` or ``/`` and have no
        member descriptor) so a module def sitting on the import line at column 0 is
        never mistaken for the client instance.
        """
        for o in self._occ:
            if o.rel_path == rel_path and o.line == line and o.is_def:
                if o.symbol.endswith("/") or o.symbol.endswith("`"):
                    continue
                return o.symbol
        return None

    def send_sites(self, client_class):
        """Iterative-search analog: find `new <client_class>()`, take the instance
        symbol defined on that line, and return that instance's non-def references
        (its `.send(...)` call sites).

        Only seeds from real constructor occurrences (`<constructor>` descriptor), not
        the import-line type reference — otherwise the import line's module symbol would
        be followed to unrelated cross-file imports.
        """
        sites = []
        for ctor in self.occurrences(client_class + "#"):
            if "<constructor>" not in ctor.symbol:
                continue
            inst = self._instance_symbol_at(ctor.rel_path, ctor.line)
            if not inst:
                continue
            for o in self._occ:
                if o.symbol == inst and not o.is_def:
                    sites.append(o)
        return sites
