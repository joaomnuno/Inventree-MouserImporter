from __future__ import annotations

import logging
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml
from django.conf import settings
from django.utils.functional import cached_property
from inventree_part_import.config import set_config_dir

TEMPLATE_FILES = ("config.yaml", "categories.yaml", "parameters.yaml", "hooks.py")
SUPPLIERS_FILE = "suppliers.yaml"


class ImporterConfigurationError(RuntimeError):
    """Raised when the importer configuration cannot be assembled."""


@dataclass
class SupplierConfigFactory:
    name: str
    builder: Callable[[dict[str, Any]], dict[str, Any]]


class ImporterConfiguration:
    """Ensures inventree-part-import reads configs from our bundled samples."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._configured = False

    @cached_property
    def config_dir(self) -> Path:
        return settings.IMPORTER_CONFIG_DIR

    @cached_property
    def template_dir(self) -> Path:
        return settings.IMPORTER_CONFIG_TEMPLATE_DIR

    def ensure(self) -> Path:
        """Prepare the runtime config dir and point inventree-part-import at it."""
        with self._lock:
            if not self._configured:
                self._sync_templates()
                self._write_suppliers_config()
                set_config_dir(self.config_dir)
                self._configured = True
        return self.config_dir

    def _sync_templates(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.template_dir.exists():
            raise ImporterConfigurationError(
                f"Importer template dir '{self.template_dir}' does not exist"
            )
        for filename in TEMPLATE_FILES:
            source = self.template_dir / filename
            target = self.config_dir / filename
            if not source.exists():
                raise ImporterConfigurationError(
                    f"Missing '{filename}' in importer templates at {self.template_dir}"
                )
            if not target.exists():
                shutil.copy(source, target)

    def _write_suppliers_config(self) -> None:
        target = self.config_dir / SUPPLIERS_FILE
        try:
            current: dict[str, Any] = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        except FileNotFoundError:
            current = {}
        except yaml.YAMLError as exc:  # pragma: no cover - defensive
            raise ImporterConfigurationError(
                f"Unable to parse existing {SUPPLIERS_FILE}: {exc}"
            ) from exc

        suppliers = {
            factory.name: factory.builder(current.get(factory.name, {}))
            for factory in self._supplier_factories()
        }

        # Keep any suppliers we do not manage to avoid clobbering manual additions.
        for key, value in current.items():
            suppliers.setdefault(key, value)

        yaml_dump = yaml.safe_dump(suppliers, sort_keys=False)
        target.write_text(yaml_dump, encoding="utf-8")

    def _supplier_factories(self) -> list[SupplierConfigFactory]:
        factories: list[SupplierConfigFactory] = []
        for supplier in settings.IMPORTER_SUPPLIERS:
            supplier_lower = supplier.lower()
            try:
                if supplier_lower == "mouser":
                    factories.append(SupplierConfigFactory("mouser", self._build_mouser_config))
                elif supplier_lower == "digikey":
                    factories.append(SupplierConfigFactory("digikey", self._build_digikey_config))
                else:
                    logger.warning("Unknown importer supplier '%s' requested; skipping", supplier)
            except ImporterConfigurationError as exc:
                logger.warning("Skipping supplier '%s': %s", supplier_lower, exc)
        if not factories:
            raise ImporterConfigurationError("No supported suppliers configured")
        return factories

    def _build_mouser_config(self, existing: dict[str, Any]) -> dict[str, Any]:
        api_key = _require_env("MOUSER_API_KEY")
        currency = os.environ.get("MOUSER_CURRENCY", settings.DEFAULT_CURRENCY)
        scraping = _env_bool("MOUSER_SCRAPING", True)
        locale = os.environ.get("MOUSER_LOCALE", "www.mouser.com")

        existing = {**existing}
        existing.update(
            {
                "api_key": api_key,
                "currency": currency,
                "scraping": scraping,
                "locale_url": locale,
            }
        )
        return existing

    def _build_digikey_config(self, existing: dict[str, Any]) -> dict[str, Any]:
        client_id = _require_env("DIGIKEY_CLIENT_ID")
        client_secret = _require_env("DIGIKEY_CLIENT_SECRET")
        currency = os.environ.get("DIGIKEY_CURRENCY", settings.DEFAULT_CURRENCY)
        language = os.environ.get("DIGIKEY_LANGUAGE", settings.DEFAULT_LANGUAGE)
        location = os.environ.get("DIGIKEY_LOCATION", settings.DEFAULT_COUNTRY)

        existing = {**existing}
        existing.update(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "currency": currency,
                "language": language,
                "location": location,
            }
        )
        return existing


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value or value.strip().lower() in {"changeme", "placeholder"}:
        raise ImporterConfigurationError(f"Environment variable '{name}' is required")
    return value


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
logger = logging.getLogger(__name__)
