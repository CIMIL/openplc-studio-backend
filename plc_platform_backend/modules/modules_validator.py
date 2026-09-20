from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from plc_platform_backend.modules.modules_models import (
    ModuleConstraint,
    ModuleParameterSpec,
    ModuleSpec,
    ModuleType,
    ParameterValidation,
)
from plc_platform_backend.modules.modules_service import ModuleService

MAX_NESTED_DEPTH = 3
_ADVANCED_PLC_OMITTED_SETTINGS = {
    "crossfade",
    "fade_in",
    "crossfade_frequencies",
    "crossover_order",
}
_NUMERIC_TYPES = {"int", "float"}
_EPISILON = 1e-9


@dataclass
class ValidationMessage:
    setting: str | None
    message: str


def _get_attr(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _format_number(value: float | int) -> str:
    if isinstance(value, float) and value.is_integer():
        return f"{value:.0f}"
    return str(value)


class ModuleConfigValidator:
    """Validates run module settings against the modules manifest."""

    def __init__(self, module_service: ModuleService) -> None:
        self.module_service = module_service

    def validate_module(
        self,
        module_type: ModuleType,
        module: Any,
        depth: int = 0,
        prefix: str = "",
        omitted_settings: set[str] | None = None,
    ) -> list[ValidationMessage]:
        module_name = _get_attr(module, "name")
        spec = self.module_service.get_module_spec(module_name, module_type)
        if spec is None:
            return [
                ValidationMessage(
                    setting=None, message=f"Module '{module_name}' was not found."
                )
            ]

        values = {
            _get_attr(setting, "name"): _get_attr(setting, "value")
            for setting in _get_attr(module, "settings") or []
        }

        messages: list[ValidationMessage] = []
        messages.extend(
            self._validate_settings(spec, values, prefix, omitted_settings or set())
        )
        messages.extend(self._validate_constraints(spec, values, prefix))
        if depth < MAX_NESTED_DEPTH:
            messages.extend(self._validate_nested(spec, values, depth, prefix))
        return messages

    def _validate_settings(
        self,
        spec: ModuleSpec,
        values: dict[str, Any],
        prefix: str,
        omitted_settings: set[str],
    ) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        for parameter in spec.settings:
            if parameter.name in omitted_settings and parameter.name not in values:
                continue
            messages.extend(
                self._validate_parameter(parameter, values.get(parameter.name), prefix)
            )
        return messages

    def _validate_parameter(
        self, parameter: ModuleParameterSpec, value: Any, prefix: str
    ) -> list[ValidationMessage]:
        validation = parameter.validation
        label = f"{prefix}{parameter.name}"

        if value is None:
            if parameter.type == "list_CrossfadeSettings":
                return [ValidationMessage(label, f"{label} must be a list.")]
            if parameter.type in {"dict_str_list_PLCSettings", "dict_str_list_int"}:
                return [ValidationMessage(label, f"{label} must be a mapping.")]
            return []

        if parameter.type == "list_CrossfadeSettings":
            return [] if isinstance(value, list) else [ValidationMessage(label, f"{label} must be a list.")]
        if parameter.type == "dict_str_list_PLCSettings":
            return [] if isinstance(value, dict) else [ValidationMessage(label, f"{label} must be a mapping.")]
        if parameter.type == "Enum" and parameter.values is not None and value not in parameter.values:
            return [
                ValidationMessage(
                    label,
                    f"{label} must be one of: {', '.join(map(str, parameter.values))}.",
                )
            ]
        if parameter.type == "bool" and not isinstance(value, bool):
            return [ValidationMessage(label, f"{label} must be a boolean.")]
        if validation is None:
            return []

        if parameter.type in _NUMERIC_TYPES:
            return self._validate_number(label, value, validation)
        if parameter.type == "str":
            return self._validate_string(label, value, validation)
        if parameter.type == "list_int":
            if not isinstance(value, list):
                return [ValidationMessage(label, f"{label} must be a list.")]
            return self._validate_list(label, value, validation)
        if parameter.type == "dict_str_list_int":
            if not isinstance(value, dict):
                return [ValidationMessage(label, f"{label} must be a mapping.")]
            messages: list[ValidationMessage] = []
            for key, items in value.items():
                if not isinstance(items, list):
                    messages.append(
                        ValidationMessage(
                            f"{label}.{key}", f"{label}.{key} must be a list."
                        )
                    )
                    continue
                messages.extend(self._validate_list(f"{label}.{key}", items, validation))
            return messages
        return []

    def _validate_list(
        self, label: str, value: list[Any], validation: ParameterValidation
    ) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        if validation.min_items is not None and len(value) < validation.min_items:
            messages.append(
                ValidationMessage(
                    label,
                    f"{label} must contain at least {validation.min_items} item(s).",
                )
            )
        if validation.max_items is not None and len(value) > validation.max_items:
            messages.append(
                ValidationMessage(
                    label,
                    f"{label} must contain at most {validation.max_items} item(s).",
                )
            )
        if validation.unique:
            try:
                is_unique = len(set(value)) == len(value)
            except TypeError:
                is_unique = True
            if not is_unique:
                messages.append(
                    ValidationMessage(label, f"{label} must not contain duplicates.")
                )
        if validation.sorted is not None and len(value) > 1:
            pairs = list(zip(value, value[1:]))
            if validation.sorted == "ascending" and not all(a < b for a, b in pairs):
                messages.append(
                    ValidationMessage(
                        label, f"{label} must be in ascending order."
                    )
                )
            if validation.sorted == "descending" and not all(a > b for a, b in pairs):
                messages.append(
                    ValidationMessage(
                        label, f"{label} must be in descending order."
                    )
                )
        if validation.item is not None:
            for index, item in enumerate(value):
                messages.extend(
                    self._validate_number(f"{label}[{index}]", item, validation.item)
                )
        return messages

    def _validate_number(
        self, label: str, value: Any, validation: ParameterValidation
    ) -> list[ValidationMessage]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return [ValidationMessage(label, f"{label} must be a number.")]

        messages: list[ValidationMessage] = []
        if validation.min is not None:
            minimum = _format_number(validation.min)
            if validation.exclusive_min and value <= validation.min:
                messages.append(
                    ValidationMessage(label, f"{label} must be greater than {minimum}.")
                )
            elif not validation.exclusive_min and value < validation.min:
                messages.append(
                    ValidationMessage(
                        label, f"{label} must be greater than or equal to {minimum}."
                    )
                )
        if validation.max is not None:
            maximum = _format_number(validation.max)
            if validation.exclusive_max and value >= validation.max:
                messages.append(
                    ValidationMessage(label, f"{label} must be less than {maximum}.")
                )
            elif not validation.exclusive_max and value > validation.max:
                messages.append(
                    ValidationMessage(
                        label, f"{label} must be less than or equal to {maximum}."
                    )
                )
        if validation.step:
            quotient = value / validation.step
            if abs(quotient - round(quotient)) > _EPISILON:
                messages.append(
                    ValidationMessage(
                        label,
                        f"{label} must be a multiple of {_format_number(validation.step)}.",
                    )
                )
        return messages

    def _validate_string(
        self, label: str, value: Any, validation: ParameterValidation
    ) -> list[ValidationMessage]:
        if not isinstance(value, str):
            return [ValidationMessage(label, f"{label} must be a string.")]

        messages: list[ValidationMessage] = []
        if validation.min_length is not None and len(value) < validation.min_length:
            messages.append(
                ValidationMessage(
                    label,
                    f"{label} must be at least {validation.min_length} character(s) long.",
                )
            )
        if validation.max_length is not None and len(value) > validation.max_length:
            messages.append(
                ValidationMessage(
                    label,
                    f"{label} must be at most {validation.max_length} character(s) long.",
                )
            )
        if validation.pattern is not None:
            try:
                matches = re.fullmatch(validation.pattern, value)
            except re.error:
                matches = True
            if not matches:
                messages.append(
                    ValidationMessage(
                        label, f"{label} must match the pattern {validation.pattern}."
                    )
                )
        return messages

    def _validate_constraints(
        self, spec: ModuleSpec, values: dict[str, Any], prefix: str
    ) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        for constraint in spec.constraints:
            messages.extend(self._apply_constraint(constraint, values, prefix))
        return messages

    def _apply_constraint(
        self, constraint: ModuleConstraint, values: dict[str, Any], prefix: str
    ) -> list[ValidationMessage]:
        setting = values.get(constraint.setting)
        related = (
            values.get(constraint.related_setting)
            if constraint.related_setting
            else None
        )
        label = f"{prefix}{constraint.setting}"
        fallback = (
            f"{label} and {constraint.related_setting} are inconsistent."
            if constraint.related_setting
            else f"{label} is invalid."
        )

        if constraint.type == "less_than":
            if setting is None or related is None:
                return []
            try:
                is_valid = setting < related
            except TypeError:
                return []
            if not is_valid:
                return [
                    ValidationMessage(label, constraint.message or fallback)
                ]
            return []

        if constraint.type == "length_relation":
            if setting is None or related is None:
                return []
            try:
                is_valid = len(setting) == len(related) + (constraint.offset or 0)
            except TypeError:
                return []
            if not is_valid:
                return [
                    ValidationMessage(label, constraint.message or fallback)
                ]
            return []

        if constraint.type == "keys_match":
            if not isinstance(setting, dict):
                return []
            messages: list[ValidationMessage] = []
            keys = set(setting.keys())
            if constraint.allowed_key_sets and keys not in [
                set(key_set) for key_set in constraint.allowed_key_sets
            ]:
                messages.append(
                    ValidationMessage(label, constraint.message or fallback)
                )
            if isinstance(related, dict) and len(related) > 0 and set(related) != keys:
                messages.append(
                    ValidationMessage(label, constraint.message or fallback)
                )
            return messages

        if constraint.type == "per_key_length_relation":
            if not isinstance(setting, dict) or not isinstance(related, dict):
                return []
            messages = []
            for key, items in setting.items():
                if key not in related:
                    continue
                try:
                    is_valid = len(items) == len(related[key]) + (constraint.offset or 0)
                except TypeError:
                    continue
                if not is_valid:
                    messages.append(
                        ValidationMessage(
                            f"{label}.{key}", constraint.message or fallback
                        )
                    )
            return messages

        return []

    def _validate_nested(
        self,
        spec: ModuleSpec,
        values: dict[str, Any],
        depth: int,
        prefix: str,
    ) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        for parameter in spec.settings:
            value = values.get(parameter.name)
            if parameter.type == "list_CrossfadeSettings":
                if not isinstance(value, list):
                    continue
                for index, item in enumerate(value):
                    messages.extend(
                        self.validate_module(
                            ModuleType.CrossfadeSettings,
                            item,
                            depth + 1,
                            prefix=f"{prefix}{parameter.name}[{index}].",
                        )
                    )
            elif parameter.type == "dict_str_list_PLCSettings":
                if not isinstance(value, dict):
                    continue
                for band, items in value.items():
                    if not isinstance(items, list):
                        continue
                    for index, item in enumerate(items):
                        messages.extend(
                            self.validate_module(
                                ModuleType.PLCAlgorithm,
                                item,
                                depth + 1,
                                prefix=f"{prefix}{parameter.name}.{band}[{index}].",
                                omitted_settings=_ADVANCED_PLC_OMITTED_SETTINGS,
                            )
                        )
        return messages