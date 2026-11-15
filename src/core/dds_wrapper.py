import hashlib
import importlib
import importlib.machinery
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from endplay_provider import EndplayProvider

LOGGER = logging.getLogger(__name__)
DDS_PROVIDERS = ("none", "dds3", "scanned", "endplay")
_DDS_DLL_DIRECTORY_HANDLES = []


class DdsProviderUnavailable(RuntimeError):
    """Raised when a selected optional DDS provider cannot be loaded."""


class DdsWrapper:
    def __init__(
            self,
            provider: str = "none",
            source_folder: str | Path | None = None,
    ):
        self.provider = "none"
        self._backend: ModuleType | EndplayProvider | None = None
        self.source_folder = self.normalize_source_folder(source_folder)
        self.set_provider(provider)

    @staticmethod
    def normalize_source_folder(
            source_folder: str | Path | None,
    ) -> Path:
        repository_root = Path(__file__).resolve().parents[2]
        folder = (
            repository_root / "dds"
            if source_folder is None
            else Path(source_folder).expanduser()
        )
        if not folder.is_absolute():
            folder = repository_root / folder
        return folder.resolve()

    @staticmethod
    def is_provider_installed(
            provider: str,
            source_folder: str | Path | None = None,
    ) -> bool:
        if provider == "scanned":
            return (
                    DdsWrapper._find_scanned_dds_extension(source_folder)
                    is not None
            )
        if provider == "dds3":
            extension_path = DdsWrapper._find_scanned_dds_extension(
                source_folder
            )
            if extension_path is None:
                return False
            try:
                DdsWrapper._load_scanned_dds(
                    DdsWrapper.normalize_source_folder(source_folder)
                )
                return True
            except (
                    ImportError,
                    OSError,
                    RuntimeError,
                    SystemError,
                    TypeError,
                    ValueError,
            ):
                LOGGER.exception(
                    "The registered DDS extension could not be loaded."
                )
                return False
        if provider == "endplay":
            return EndplayProvider.is_installed()
        return provider == "none"

    def set_provider(
            self,
            provider: str,
            source_folder: str | Path | None = None,
    ) -> None:
        if provider not in DDS_PROVIDERS:
            raise ValueError(f"Unsupported DDS provider: {provider}")
        requested_folder = (
            self.source_folder
            if source_folder is None
            else self.normalize_source_folder(source_folder)
        )
        if provider == self.provider and requested_folder == self.source_folder:
            return
        if provider == "none":
            self.provider = provider
            self.source_folder = requested_folder
            self._backend = None
            return

        try:
            backend = self._load_provider(provider, requested_folder)
        except (
                ImportError,
                OSError,
                RuntimeError,
                SystemError,
                TypeError,
                ValueError,
        ) as error:
            raise DdsProviderUnavailable(
                f"The optional DDS source '{provider}' could not be loaded: {error}"
            ) from error

        self.provider = provider
        self.source_folder = requested_folder
        self._backend = backend

    @staticmethod
    def _load_provider(
            provider: str,
            source_folder: Path,
    ) -> ModuleType | EndplayProvider:
        if provider in {"dds3", "scanned"}:
            return DdsWrapper._load_scanned_dds(source_folder)
        if provider == "endplay":
            return EndplayProvider()
        raise ValueError(f"Unsupported DDS provider: {provider}")

    @staticmethod
    def _find_scanned_dds_extension(
            source_folder: str | Path | None = None,
    ) -> Path | None:
        if source_folder is not None and not str(source_folder).strip():
            return None
        source_root = DdsWrapper.normalize_source_folder(source_folder)
        search_roots = [source_root]
        if (source_root / "dds").is_dir():
            search_roots.append(source_root / "dds")
        seen_directories = set()
        binary_dirs = []
        for root in search_roots:
            candidates = [
                root,
                root / "python" / "dds3",
                root / "dds3",
                root / "bazel-bin" / "python" / "dds3",
            ]
            for environment_name in (".venv", "venv"):
                environment = root / environment_name
                candidates.extend(
                    (
                        environment / "Lib" / "site-packages" / "dds3",
                        environment / "lib" / "site-packages" / "dds3",
                    )
                )
                python_directories = environment / "lib"
                if python_directories.is_dir():
                    candidates.extend(
                        python_directory
                        / "site-packages"
                        / "dds3"
                        for python_directory in python_directories.glob(
                            "python*"
                        )
                    )
            for candidate in candidates:
                normalized = candidate.resolve()
                if normalized not in seen_directories:
                    seen_directories.add(normalized)
                    binary_dirs.append(normalized)

        for binary_dir in binary_dirs:
            if any(
                    (binary_dir / f"_dds3{suffix}").is_file()
                    for suffix in importlib.machinery.EXTENSION_SUFFIXES
            ):
                return binary_dir / next(
                    f"_dds3{suffix}"
                    for suffix in importlib.machinery.EXTENSION_SUFFIXES
                    if (binary_dir / f"_dds3{suffix}").is_file()
                )
        return None

    @staticmethod
    def _load_scanned_dds(source_folder: Path) -> ModuleType:
        extension_path = DdsWrapper._find_scanned_dds_extension(source_folder)
        if extension_path is None:
            raise ImportError(
                f"No built DDS extension was found in '{source_folder}'."
            )

        module_key = str(extension_path.resolve())
        module_suffix = hashlib.sha256(
            module_key.encode("utf-8")
        ).hexdigest()[:16]
        module_name = f"_bridge_demonstration_scanned_dds3_{module_suffix}"
        extension_module_name = f"{module_name}._dds3"
        loaded_module = sys.modules.get(extension_module_name)
        if loaded_module is not None:
            return loaded_module

        package = sys.modules.get(module_name)
        if package is None:
            package = ModuleType(module_name)
            package.__path__ = [str(extension_path.parent)]
            sys.modules[module_name] = package
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            dll_directories = {
                extension_path.parent,
                DdsWrapper.normalize_source_folder(source_folder),
            }
            for dll_directory in dll_directories:
                if dll_directory.is_dir():
                    _DDS_DLL_DIRECTORY_HANDLES.append(
                        os.add_dll_directory(str(dll_directory))
                    )
        spec = importlib.util.spec_from_file_location(
            extension_module_name,
            extension_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError(
                f"The DDS extension at '{extension_path}' could not be loaded."
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[extension_module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(extension_module_name, None)
            raise
        setattr(package, "_dds3", module)
        return module

    def is_available(self) -> bool:
        return self.provider != "none" and self._backend is not None

    def calc_dd_table_pbn(self, pbn_deal: str) -> Optional[dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("No DDS source is selected; double-dummy analysis cannot run.")

        try:
            if self.provider in {"dds3", "scanned"}:
                result = self._dds3_backend().calc_all_tables_pbn(
                    [pbn_deal],
                    mode=-1,
                )
                tables = result.get("tables")
                if not tables:
                    raise ValueError("DDS returned no double-dummy table for the deal.")
                return tables[0]
            return self._endplay_backend().calc_dd_table_pbn(pbn_deal)
        except Exception:
            LOGGER.exception(
                "Double-dummy table calculation failed using %s.",
                self.provider,
            )
            return None

    def solve_board_pbn(
            self,
            pbn_deal: str,
            target: int = -1,
            solutions: int = 2,
            mode: int = 0,
            *,
            trump: int = 4,
            first: int = 0,
            current_trick_suit=(0, 0, 0),
            current_trick_rank=(0, 0, 0),
    ) -> Optional[Any]:
        if not self.is_available():
            raise RuntimeError("No DDS source is selected; board solving cannot run.")

        try:
            if self.provider in {"dds3", "scanned"}:
                return self._dds3_backend().solve_board_pbn(
                    pbn_deal,
                    trump=trump,
                    first=first,
                    current_trick_suit=current_trick_suit,
                    current_trick_rank=current_trick_rank,
                    target=target,
                    solutions=solutions,
                    mode=mode,
                )
            return self._endplay_backend().solve_board_pbn(
                pbn_deal,
                target=target,
                solutions=solutions,
                mode=mode,
                trump=trump,
                first=first,
                current_trick_suit=current_trick_suit,
                current_trick_rank=current_trick_rank,
            )
        except Exception:
            LOGGER.exception("DDS board solving failed using %s.", self.provider)
            return None

    def _dds3_backend(self) -> ModuleType:
        if not isinstance(self._backend, ModuleType):
            raise RuntimeError("The dds3 provider is not active.")
        return self._backend

    def _endplay_backend(self) -> EndplayProvider:
        if not isinstance(self._backend, EndplayProvider):
            raise RuntimeError("The Endplay provider is not active.")
        return self._backend
