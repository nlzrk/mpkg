import os
from abc import ABC, abstractmethod


class Backend(ABC):
    name: str = ""
    binary: str = ""

    def is_available(self) -> bool:
        return os.path.exists(self.binary)

    @abstractmethod
    def install(self, package: str) -> bool: ...

    @abstractmethod
    def remove(self, package: str) -> bool: ...

    @abstractmethod
    def is_installed(self, package: str) -> bool: ...

    @abstractmethod
    def list_installed(self) -> set[str]: ...

    @abstractmethod
    def list_explicit(self) -> set[str]: ...
