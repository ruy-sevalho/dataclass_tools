from dataclasses import dataclass, Field, field
from typing import Any, Optional, Protocol, Tuple, Union, runtime_checkable
from copy import deepcopy
from enum import Enum

DEFAULT_TYPE_LABEL = "typ"
METADATA_KEY = "dataclass_tools"


@runtime_checkable
class DataClass(Protocol):
    """Simple protocol to check if object is a dataclass."""

    __dataclass_fields__: dict[str, Field]


class Named(DataClass):
    """DataClass with a name attribute."""

    name: str


class Serializer(Protocol):
    """Function that serializes an object with a given name in parent object structure."""

    def __call__(self, obj: DataClass, name: str, **kwds: Any) -> dict[str, Any]:
        pass


@runtime_checkable
class GetType(Protocol):
    """Function that gets a string representation of the 'type' of object. Usually the class name."""

    def __call__(self, obj) -> str:
        pass


def get_type_default(obj) -> str:
    return type(obj).__name__


@dataclass
class SerializerOptions:
    """Options for field serializtion function."""

    attr: Optional[str] = None
    flatten: bool = False
    add_type: Union[bool, str] = False
    type_name: Union[GetType, str] = get_type_default
    overwrite_key: Optional[str] = None


def _get_type_str(type_name: Union[GetType, str], obj: Any):
    if isinstance(type_name, str):
        return str
    if isinstance(type_name, GetType):
        return type_name(obj)


def _get_and_process_value(obj, field_: Field):
    options: SerializerOptions = field_.metadata.get(METADATA_KEY, SerializerOptions())
    value = _get_value(obj)
    name = options.overwrite_key or field_.name
    # Attr is usually a unique name, for reference purposes
    if options.attr:
        return getattr(obj, options.attr)
    if options.add_type:
        # The default type label to be used depends the obj will be flattened or not
        # This was my best way to do it so far, has room for improvement
        default_label = DEFAULT_TYPE_LABEL if not options.flatten else name
        type_key = default_label if options.add_type is True else options.add_type
        type_str = _get_type_str(options.type_name, obj)
        # Putting the type entry in the begging seemed to make more sense
        value = {**{type_key: type_str}, **value}
    return value


def _get_field_dict(
    obj: Any,
    field_: Field,
):
    options: SerializerOptions = field_.metadata.get(METADATA_KEY, SerializerOptions())
    name = options.overwrite_key or field_.name
    if isinstance(obj, (list, tuple)):
        value: Any = [_get_field_dict(item, field_) for item in obj]
        return {name: value}
    elif isinstance(obj, dict):
        value: dict = {}
        for key, item in obj.items():
            f: Field = field()
            f.name = deepcopy(key)
            value.update(**_get_field_dict(item, f))
    else:
        value = _get_and_process_value(obj, field_)
    if options.flatten:
        return value

    return {name: value}


def _dataclass_to_dict(obj: DataClass) -> dict[str, Any]:
    list_of_dict_repr = [
        _get_field_dict(getattr(obj, field_.name), field_)
        for field_ in obj.__dataclass_fields__.values()
    ]
    return {key: value for x in list_of_dict_repr for key, value in x.items()}


def _get_value(obj):
    if isinstance(obj, DataClass):
        return _dataclass_to_dict(obj)
    if isinstance(obj, Enum):
        return str(Enum)
    else:
        return deepcopy(obj)


def to_dict(obj: DataClass):
    if not isinstance(obj, DataClass):
        raise TypeError(f"to_dict() argument must be a dataclass, not '{type(obj)}'")
    return _get_value(obj)
