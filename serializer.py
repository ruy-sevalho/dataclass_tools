from dataclasses import dataclass, Field, field
from typing import Any, Optional, Protocol, Union, get_args, runtime_checkable
from copy import copy, deepcopy
from enum import Enum


class KeyTypeError(ValueError):
    """Raised when a attr chosen as value for dataclass, which is used to be a key of
    that instance in a dictionary, is of invalid type.
    """


DEFAULT_TYPE_LABEL = "typ"
METADATA_KEY = "dataclass_tools"
PERMITED_KEY_TYPES = Union[str, int, float]


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
    """Callable[type, str], return should be a string naming the type."""

    def __call__(self, typ: type) -> str:
        pass


def _get_type_default(typ) -> str:
    """Default naming function for a type."""
    return typ.__name__


@dataclass
class SerializerOptions:
    """Options for field serializer function.

    subs_by_attr: attribute name to substitute the dataclass value, usually to be used as key in dict containg actual instances

    flatten: If True will flatten the dataclass serialized dict into the parent object. In case of list and tuples as values
    of fields this options will be overiden a values flattended automaticaly

    type_label: key to be used for 'type' of value. Default value is 'typ', or in flattened fields the field name.

    type_name: How to name the field's type. Can be a string, in which case that value will be used, or a callable that
    receives a class and returns a string

    overwrite_key: key to used in place of field's name in serialized dict of object
    """

    subs_by_attr: Optional[str] = None
    flatten: bool = False
    add_type: Union[bool, str] = False
    type_label: Optional[str] = None
    type_name: Union[GetType, str] = _get_type_default
    overwrite_key: Optional[str] = None


SerializerOptions()


def _get_type_str(type_name: Union[GetType, str], typ: type):
    """Returns a string to name a type."""

    if isinstance(type_name, str):
        return str
    if isinstance(type_name, GetType):
        return type_name(typ)


def _get_type_key(field_: Field):
    """Returns a key for the type of a field, to be used in dictionary representation of dataclass."""

    options: SerializerOptions = field_.metadata.get(METADATA_KEY, SerializerOptions())
    name = options.overwrite_key or field_.name
    # The default type label to be used depends the obj will be flattened or not
    # This was my best way to do it so far, has room for improvement
    default_label = DEFAULT_TYPE_LABEL if not options.flatten else name
    return options.type_label or default_label


def _get_and_process_value(obj, field_: Field):
    """Returns the obj serialized as a dict. Should be called on individual instances, not collections."""

    options: SerializerOptions = field_.metadata.get(METADATA_KEY, SerializerOptions())
    # Attr should be a unique value, to be used as key in dictionary
    if options.subs_by_attr:
        attr = getattr(obj, options.subs_by_attr)
        if not isinstance(attr, get_args(PERMITED_KEY_TYPES)):
            raise KeyTypeError(
                f"attr chosen to substitute dataclass value is assumed will be used as key in dictionary, so cannot be of '{type(attr).__name__}' type."
            )
        return getattr(obj, options.subs_by_attr)
    value = _get_value(obj)
    if options.add_type:
        type_key = _get_type_key(field_)
        type_str = _get_type_str(options.type_name, type(obj))
        # Putting the type entry in the begging seemed to make more sense
        value = {**{type_key: type_str}, **value}
    return value


def _serialize_field(
    obj: Any,
    field_: Field,
    in_list: bool = False,
):
    """Returns a dataclass field serialized."""

    options: SerializerOptions = field_.metadata.get(METADATA_KEY, SerializerOptions())
    name = options.overwrite_key or field_.name
    if isinstance(obj, (list, tuple)):
        value: Union[list, tuple, dict] = type(obj)(
            _serialize_field(item, field_, in_list=True) for item in obj
        )
        return {name: value}
    elif isinstance(obj, dict):
        value = dict()
        for key, item in obj.items():
            f: Field = field()
            f.name = deepcopy(key)
            value.update(**_serialize_field(item, f))
    else:
        value = _get_and_process_value(obj, field_)
    if options.flatten or in_list:
        return value
    return {name: value}


def _serialize_dataclass(obj: DataClass) -> dict[str, Any]:
    """Returns a serilized dataclass object."""

    list_of_dict_repr = [
        _serialize_field(getattr(obj, field_.name), field_)
        for field_ in obj.__dataclass_fields__.values()
    ]
    return {key: value for x in list_of_dict_repr for key, value in x.items()}


def _get_value(obj):
    """Returns the serialzed value of an object. Should called on single objects, not conatainers such as lists and dicts."""

    if isinstance(obj, DataClass):
        return _serialize_dataclass(obj)
    if isinstance(obj, Enum):
        return Enum.name
    else:
        return deepcopy(obj)


def serialize_dataclass(
    obj: DataClass,
) -> dict[str, Any]:
    """Serializes a dataclass instance."""

    if not isinstance(obj, DataClass):
        raise TypeError(f"to_dict() argument must be a dataclass, not '{type(obj)}'")
    return _get_value(obj)
