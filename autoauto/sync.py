"""Sync a local `ScriptStore` with a `RemoteStore`.

Ties the two ends of the record -> cloud -> reuse loop together:

    push(name)   local  -> remote   (upload one recording)
    pull(name)   remote -> local    (download one recording)
    push_all()   upload everything local
    pull_all()   download everything remote
    sync()       union: upload local-only, download remote-only

Names are the store's flat ids (no `.sh` suffix), consistent on both ends.
"""
from __future__ import annotations

from .cloudstore import RemoteStore
from .store import ScriptStore


class StoreSync:
    def __init__(self, local: ScriptStore, remote: RemoteStore) -> None:
        self.local = local
        self.remote = remote

    def push(self, name: str) -> None:
        self.remote.put(name, self.local.load(name))

    def pull(self, name: str) -> str:
        content = self.remote.get(name)
        self.local.save(name, content)
        return content

    def push_all(self) -> list[str]:
        names = self.local.list()
        for n in names:
            self.push(n)
        return names

    def pull_all(self) -> list[str]:
        names = self.remote.list()
        for n in names:
            self.pull(n)
        return names

    def list_remote(self) -> list[str]:
        return self.remote.list()

    def rename(self, old: str, new: str) -> dict[str, bool]:
        """Rename on both ends where present. Returns which side was renamed."""
        local_ok = False
        if self.local.exists(old):
            self.local.rename(old, new)
            local_ok = True
        remote_ok = self.remote.rename(old, new)
        return {"local": local_ok, "remote": remote_ok}

    def sync(self) -> dict[str, list[str]]:
        """Reconcile: upload local-only names, download remote-only names.

        Names present on both sides are left untouched (no content diffing).
        """
        local = set(self.local.list())
        remote = set(self.remote.list())
        pushed = sorted(local - remote)
        pulled = sorted(remote - local)
        for n in pushed:
            self.push(n)
        for n in pulled:
            self.pull(n)
        return {"pushed": pushed, "pulled": pulled}
