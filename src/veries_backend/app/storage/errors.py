from __future__ import annotations


class StorageError(Exception):
    pass


class StorageNotConfiguredError(StorageError):
    pass


class StorageDependencyMissingError(StorageError):
    pass


class StorageObjectTooLargeError(StorageError):
    pass
