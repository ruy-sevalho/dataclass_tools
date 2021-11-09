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


@dataclass
class ToolsField:
    field_: Field

    def __post_init__(self):
        self.options = self.field_.metadata.get(METADATA_KEY, DeSerializerOptions())

    @property
    def _key(self):
        return self.options.overwrite_key or self.field_.name

    def _type_str(self, typ: type):
        """Returns a string to name a type."""
        name = self.options.type_name

        if isinstance(name, str):
            return str
        if isinstance(name, GetType):
            return name(typ)
        else:
            raise ValueError(
                """type_name option must be either a string or a callable that receives 
                a type an returns a string.
                """
            )

    @property
    def _type_key(self):
        """Returns a key for the type of a field, to be used in dictionary representation of dataclass."""

        # The default type label to be used depends the obj will be flattened or not
        # This was my best way to do it so far, has room for improvement
        default_label = DEFAULT_TYPE_LABEL if not self.options.flatten else self._key
        return self.options.type_label or default_label

    def _get_and_process_value(self, obj):
        """Returns the obj serialized as a dict. Should be called on individual instances,
        not collections.
        """

        options = self.options
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
            type_str = self._type_str(type(obj))
            # Putting the type entry in the begging seemed to make more sense
            value = {**{self._type_key: type_str}, **value}
        return value

    def _serialize_field(
        self,
        obj: Any,
        in_collection: bool = False,
    ):
        """Returns a dataclass field serialized."""

        options = self.options
        name = self._key
        if isinstance(obj, (list, tuple)):
            value: Union[list, tuple, dict] = type(obj)(
                self._serialize_field(item, in_collection=True) for item in obj
            )
            return {name: value}
        elif isinstance(obj, dict):
            value = dict()
            for key, item in obj.items():
                f: Field = field()
                f.name = deepcopy(key)

                # f.name = deepcopy(key)
                value.update(**ToolsField(f)._serialize_field(item))
        else:
            value = self._get_and_process_value(obj)
        if options.flatten or in_collection:
            return value
        return {name: value}

    def _field_type(self, dct: dict, in_collection=False):
        typ: type = self.field_.type
        if self.options.add_type:
            if self.options.add_type and not self.options.subtype_table:
                raise TypeError(
                    "If add_type is specified for a field a subtype_table must be given also."
                )
            if self.options.flatten or in_collection:
                type_repr = dct[self._type_key]
            else:
                type_repr = dct[self._key][self._type_key]
            table = self.options.subtype_table
            typ = table[type_repr]
        return typ

    def _field_keys(self, dct: dict, in_collection=False):
        if self.options.flatten:
            typ = self._field_type(dct, in_collection=in_collection)
            if not isinstance(typ, DataClass):
                raise (
                    ValueError(
                        f"'{typ.__name__}' cannot be deserialized with flattened=True, only dataclass fields can."
                    )
                )
            inner_keys = []
            if self.options.add_type:
                inner_keys.append(self._type_key)
            for inner_field in fields(typ):
                tools_inner_field = ToolsField(inner_field)
                key = tools_inner_field._key
                inner_dict = dct[key]
                if tools_inner_field.options.flatten:
                    inner_dict = dct
                inner_keys.append(tools_inner_field._field_keys(inner_dict))
            return inner_keys
        return self._key

    def _deserialize_field(
        self, raw_dct: dict, in_collection=False, build_instance=False
    ) -> dict[str, Any]:
        """Deserializes a field instance."""

        if hasattr(self.field_.type, "__origin__"):
            if self.options.flatten:
                raise ValueError(
                    f"'{type(self.field_.type)}' can't be flattened, only dataclasses"
                )
            origin: type = self.field_.type.__origin__
            if origin == list or origin == tuple:
                inner_type_field = copy(self.field_)
                inner_type_field.type = self.field_.type.__args__[0]
                value = origin(
                    ToolsField(inner_type_field)._deserialize_field(
                        item, in_collection=True
                    )
                    for item in raw_dct[self._key]
                )
            elif origin == dict:
                if self.options.flatten:
                    raise (
                        ValueError(
                            f"Only flattened dataclass fields can be deseirialized, 'dict' cannot"
                        )
                    )
                inner_type_field = copy(self.field_)
                inner_type_field.type = self.field_.type.__agrs__[1]
                value = {
                    key: ToolsField(inner_type_field)._deserialize_field(
                        raw_dct=value, build_instance=build_instance
                    )
                    for key, value in raw_dct[self._key].items()
                }
        if in_collection or self.options.flatten:
            value = raw_dct
        else:
            value = raw_dct[self._key]
        typ = self._field_type(value)
        if is_dataclass(typ):
            value = deserialize_dataclass(value, typ)
        if self.options.flatten or in_collection:
            return value
        return {self.field_.name: value}


def _serialize_dataclass(obj: DataClass) -> dict[str, Any]:
    """Returns a serilized dataclass object."""

    list_of_dict_repr = [
        ToolsField(field_)._serialize_field(getattr(obj, field_.name))
        for field_ in fields(obj)
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
        raise TypeError(f"obj must be a dataclass, not '{type(obj).__name__}'")
    return _serialize_dataclass(obj)


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
    input_dict = _deserialize_dataclass(dct, dataclass)
    return input_dict


def _deserialize_dataclass(dct: dict, dataclass: DataClass):
    """Derializes a dataclass instance."""

    list_of_input_dict = [
        ToolsField(field_)._deserialize_field(dct) for field_ in fields(dataclass)
    ]
    return {key: value for x in list_of_input_dict for key, value in x.items()}
