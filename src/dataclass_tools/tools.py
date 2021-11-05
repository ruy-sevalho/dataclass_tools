from dataclasses import dataclass, Field, field, fields, is_dataclass
from typing import Any, Optional, Protocol, Union, get_args, runtime_checkable
from copy import copy, deepcopy
from enum import Enum


class KeyTypeError(ValueError):
    """Raised when a attr chosen as value for dataclass, which is used to be a key of
    that instance in a dictionary, is of invalid type. This error considereds a subset
    of all valid key types, since we want to them to also be json valid keys.
    """


DEFAULT_TYPE_LABEL = "typ"
METADATA_KEY = "dataclass_tools"
PERMITED_KEY_TYPES = Union[str, int, float, bool]


@runtime_checkable
class DataClass(Protocol):
    """Simple protocol to check if object is a dataclass."""

    __dataclass_fields__: dict[str, Field]


@runtime_checkable
class GetType(Protocol):
    """Callable[type, str], return should be a string naming the type."""

    def __call__(self, typ: type) -> str:
        pass


def _get_type_default(typ) -> str:
    """Default naming function for a type."""
    return typ.__name__


@dataclass
class DeSerializerOptions:
    """Options for field serializer function.

    subs_by_attr: attribute name to substitute the dataclass value, usually to be used as key in dict containg actual instances

    flatten: If True will flatten the dataclass serialized dict into the parent object. In case of list and tuples as values
    of fields this options will be overiden a values flattended automaticaly

    type_label: key to be used for 'type' of value. Default value is 'typ', or in flattened fields the field name.

    type_name: How to name the field's type. Can be a string, in which case that value will be used, or a callable that
    receives a class and returns a string

    subtype_table: dict containg mapping of type_labels to the specific class.

    overwrite_key: key to used in place of field's name in serialized dict of object
    """

    subs_by_attr: Optional[str] = None
    flatten: bool = False
    add_type: Union[bool, str] = False
    type_label: Optional[str] = None
    type_name: Union[GetType, str] = _get_type_default
    subtype_table: Optional[dict[get_args(PERMITED_KEY_TYPES), type]] = None
    overwrite_key: Optional[str] = None


def _get_field_options(field_: Field) -> DeSerializerOptions:
    return field_.metadata.get(METADATA_KEY, DeSerializerOptions())


def _get_type_str(type_name: Union[GetType, str], typ: type):
    """Returns a string to name a type."""

    if isinstance(type_name, str):
        return str
    if isinstance(type_name, GetType):
        return type_name(typ)


def _get_type_key(field_: Field):
    """Returns a key for the type of a field, to be used in dictionary representation of dataclass."""

    options = _get_field_options(field_)
    name = options.overwrite_key or field_.name
    # The default type label to be used depends the obj will be flattened or not
    # This was my best way to do it so far, has room for improvement
    default_label = DEFAULT_TYPE_LABEL if not options.flatten else name
    return options.type_label or default_label


def _get_and_process_value(obj, field_: Field):
    """Returns the obj serialized as a dict. Should be called on individual instances, not collections."""

    options = _get_field_options(field_)
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

    options = _get_field_options(field_)
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
        _serialize_field(getattr(obj, field_.name), field_) for field_ in fields(obj)
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
        raise TypeError(f"obj must be a dataclass, not '{type(obj)}'")
    return _get_value(obj)


def deserialize_dataclass(
    dct: dict,
    dataclass: DataClass,
    build_instance: bool = False,
    attr_dict_pairs: Optional[
        dict[get_args(PERMITED_KEY_TYPES), dict[get_args(PERMITED_KEY_TYPES), Any]]
    ] = None,
):
    """Derializes a dataclass instance."""

    if not isinstance(dataclass, DataClass):
        raise TypeError(
            f"dataclass argument must be a dataclass isntance, not '{type(dataclass).__name__}'"
        )
    input_dict = _deserialize_dataclass(dataclass, dct)
    return input_dict


def _deserialize_dataclass(dct: dict, dataclass: DataClass):
    """Derializes a dataclass instance."""

    list_of_input_dict = [
        _deserialize_field(field_, dct) for field_ in fields(dataclass)
    ]
    return {key: value for x in list_of_input_dict for key, value in x.items()}


def _get_field_type(field_: Field, dct: dict):
    options = _get_field_options(field_)
    name = options.overwrite_key or field_.name
    typ = field_.type
    if options.add_type:
        type_key = _get_type_key(field_)
        if options.flatten:
            type_repr = dct[type_key]
        else:
            type_repr = dct[name][type_key]
        table = options.subtype_table
        typ = table[type_repr]
    return typ


def _get_field_keys(field_: Field):
    options: DeSerializerOptions = _get_field_options(field_)
    typ = _get_field_type()
    if options.flatten:
        inner_keys = _get_field_keys()

    return


def _deserialize_options_check(options: DeSerializerOptions):
    if options.add_type and not options.subtype_table:
        raise TypeError(
            "If add_type is specified for a field a subtype_table must be given also."
        )
    return


def _deserialize_field(field_: Field, raw_dct: dict):
    """Deserializes a field instance."""

    options = _get_field_options(field_)
    # Some combinations of options values don't make sense together so they are checked here
    _deserialize_options_check(options)
    name = options.overwrite_key or field_.name
    if hasattr(field_.type, "__origin__"):
        origin: type = field_.type.__origin__
        if origin == list or origin == tuple:
            inner_type_field = copy(field_)
            inner_type_field: type = field_.type.__agrs__[0]
            value = origin(
                _deserialize_field(inner_type_field, item) for item in raw_dct[name]
            )
        elif origin == dict:
            value = dict()
    typ = _get_field_type(field_, raw_dct)

    input_dict = raw_dct[name]

    if options.flatten:
        field_keys = _get_field_keys(field_)
        input_dict = {key: raw_dct[key] for key in field_keys}

    if is_dataclass(typ):
        value = _deserialize_dataclass(input_dict, typ)

    return {field_.name: value}


def _deserialize_value(field_: Field, obj):
    return
