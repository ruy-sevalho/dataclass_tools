"""
 # @ Author: Ruy Sevalho
 # @ Create Time: 2021-10-25 18:15:28
 # @ Modified by: Ruy Sevalho
 # @ Modified time: 2022-01-21 11:07:47
 # @ Description:
 """

from copy import copy, deepcopy
from dataclasses import Field, dataclass, fields, is_dataclass
from enum import Enum
from typing import Any, Optional, Protocol, Union, get_args, runtime_checkable

import quantities as pq


@dataclass
class NamePrint:
    """Strings for printing value name."""

    long: str
    abreviation: Optional[str] = None


@dataclass
class PrintWrapper:
    """Print wrapper for string or quantity values."""

    value: Any
    names: NamePrint


@dataclass
class PrintMetadata:
    long_name: str
    abreviation: Optional[str] = None
    units: str = ""

    @property
    def names(self):
        abr = self.abreviation or self.long_name
        return NamePrint(long=self.long_name, abreviation=abr)

    def print_value(self, value, include_names: bool = False):
        if isinstance(value, (int, float)):
            if self.units == "percent":
                value *= 100
            value = pq.Quantity(value, self.units)
        if include_names:
            return PrintWrapper(value, self.names)
        else:
            return value


class KeyTypeError(ValueError):
    """Raised when a attr chosen as value for dataclass, which is used to be a key of
    that instance in a dictionary, is of invalid type. This error considereds a subset
    of all valid key types, since we want to them to also be json valid keys.
    """


DEFAULT_TYPE_LABEL = "typ"
DESERIALIZER_OPTIONS = "dataclass_tools"
PERMITED_KEY_TYPES = Union[str, int, float, bool, Enum]


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
    receives a class(type) and returns a string

    subtype_table: dict containg mapping of type_labels to the specific class.

    overwrite_key: key to used in place of field's name in serialized dict of object
    """

    subs_by_attr: Optional[str] = None
    subs_collection_name: Optional[str] = None
    flatten: bool = False
    add_type: Union[bool, str] = False
    type_label: Optional[str] = None
    type_name: Union[GetType, str] = _get_type_default
    subtype_table: Optional[dict[get_args(PERMITED_KEY_TYPES), type]] = None
    overwrite_key: Optional[str] = None
    metadata: Optional[PrintMetadata] = None


@dataclass
class ToolsField:
    field_: Field

    def __post_init__(self):
        self.options = self.field_.metadata.get(
            DESERIALIZER_OPTIONS, DeSerializerOptions()
        )

    def _print_wrapper_builder(self, value, metadata: PrintMetadata):

        if isinstance(value, (int, float)):
            if metadata.units == "percent":
                value *= 100
            return PrintWrapper(pq.Quantity(value, metadata.units), metadata.names)
        else:
            return PrintWrapper(value, metadata.names)

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
    def _collection_key(self):
        """Key of collection in dictionay of collections for subs_by_attr option."""

        if not self.options.subs_collection_name:
            return self.field_.name

        return self.options.subs_collection_name

    @property
    def _type_key(self):
        """Returns a key for the type of a field, to be used in dictionary representation of dataclass."""

        # The default type label to be used depends the obj will be flattened or not
        # This was my best way to do it so far, has room for improvement
        default_label = DEFAULT_TYPE_LABEL if not self.options.flatten else self._key
        return self.options.type_label or default_label

    def _get_and_process_value(
        self,
        obj,
        print_format: bool = False,
        include_names: bool = False,
        flatten=False,
    ):
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
            value = attr
        else:
            value = _get_value(
                obj, printing_format=print_format, include_names=include_names
            )
            if options.add_type:
                type_str = self._type_str(type(obj))
                # Putting the type entry in the begging seemed to make more sense
                value = {**{self._type_key: type_str}, **value}
        if print_format:
            if not options.metadata:
                raise ValueError(
                    f"Must provide metadata option for field to serialize in print format"
                )
            if not flatten:
                value = options.metadata.print_value(value, include_names=include_names)
        return value

    def _serialize_field(
        self,
        obj: Any,
        in_collection: bool = False,
        printing_format: bool = False,
        include_names: bool = False,
    ):
        """Returns a dataclass field serialized."""

        options = self.options
        name = self._key
        if isinstance(obj, (list, tuple)):
            value: Union[list, tuple, dict] = type(obj)(
                self._serialize_field(
                    item,
                    in_collection=True,
                    printing_format=printing_format,
                    include_names=include_names,
                )
                for item in obj
            )
            return {name: value}
        elif isinstance(obj, dict):
            value = dict()
            for key, item in obj.items():
                value.update(
                    {
                        key: self._serialize_field(
                            item,
                            in_collection=True,
                            printing_format=printing_format,
                            include_names=include_names,
                        )
                    }
                )
        else:
            value = self._get_and_process_value(
                obj,
                print_format=printing_format,
                include_names=include_names,
                flatten=options.flatten,
            )
        if options.flatten or in_collection:
            return value
        return {name: value}

    def _field_type(self, dct: dict):
        typ: type = self.field_.type
        if self.options.add_type:
            if self.options.add_type and not self.options.subtype_table:
                raise TypeError(
                    """If add_type is specified for a field a subtype_table must be given 
                    also for deserialization to be possible.
                    """
                )
            type_repr = dct[self._type_key]
            table = self.options.subtype_table
            typ = table[type_repr]
        return typ

    def _deserialize_field(
        self,
        raw_dct: dict,
        in_collection=False,
        build_instance=False,
        dict_of_collections=None,
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
                        item,
                        in_collection=True,
                        build_instance=build_instance,
                        dict_of_collections=dict_of_collections,
                    )
                    for item in raw_dct[self._key]
                )
                return {self.field_.name: value}
            elif origin == dict:
                if self.options.flatten:
                    raise (
                        ValueError(
                            f"Only flattened dataclass fields can be deseirialized, 'dict' cannot"
                        )
                    )
                inner_type_field = copy(self.field_)
                inner_type_field.type = self.field_.type.__args__[1]
                value = {
                    key: ToolsField(inner_type_field)._deserialize_field(
                        raw_dct=value,
                        build_instance=build_instance,
                        in_collection=True,
                        dict_of_collections=dict_of_collections,
                    )
                    for key, value in raw_dct[self._key].items()
                }
                return {self.field_.name: value}
        if in_collection or self.options.flatten:
            value = raw_dct
        else:
            value = raw_dct.get(self._key)
        typ = self._field_type(value)
        if is_dataclass(typ):
            if not self.options.subs_by_attr:
                value = _deserialize_dataclass(
                    value,
                    typ,
                    dict_of_collections=dict_of_collections,
                    build_instance=build_instance,
                )
            if build_instance and self.options.subs_by_attr:
                value = dict_of_collections[self._collection_key][value]
        if in_collection:
            return value
        return {self.field_.name: value}


def _serialize_dataclass(
    obj: DataClass,
    printing_format: bool = False,
    include_names: bool = False,
) -> dict[str, Any]:
    """Returns a serilized dataclass object."""

    list_of_dict_repr = [
        ToolsField(field_)._serialize_field(
            getattr(obj, field_.name),
            printing_format=printing_format,
            include_names=include_names,
        )
        for field_ in fields(obj)
    ]
    return {key: value for x in list_of_dict_repr for key, value in x.items()}


def _get_value(obj, printing_format=False, include_names=False):
    """Returns the serialzed value of an object. Should called on single objects, not conatainers such as lists and dicts."""

    if isinstance(obj, DataClass):
        return _serialize_dataclass(
            obj, printing_format=printing_format, include_names=include_names
        )
    if isinstance(obj, Enum):
        return obj.name
    else:
        return deepcopy(obj)


def _deserialize_dataclass(
    dct: dict,
    dataclass: DataClass,
    in_collection: bool = False,
    build_instance: bool = True,
    dict_of_collections: Optional[
        dict[get_args(PERMITED_KEY_TYPES), dict[get_args(PERMITED_KEY_TYPES), Any]]
    ] = None,
):
    """Derializes a dataclass instance."""
    list_of_input_dict = [
        ToolsField(field_)._deserialize_field(
            dct,
            in_collection=in_collection,
            build_instance=build_instance,
            dict_of_collections=dict_of_collections,
        )
        for field_ in fields(dataclass)
    ]
    # flattening the list of input dicts to be able to call the class instance creator
    input_dict = {
        key: value
        for x in list_of_input_dict
        for key, value in x.items()
        if not value is None
    }

    if build_instance:
        instance = dataclass(**input_dict)
        return instance
    return input_dict


def serialize_dataclass(
    obj: DataClass,
    printing_format: bool = False,
    include_names: bool = False,
) -> dict[str, Any]:
    """Serializes a dataclass instance."""

    if not isinstance(obj, DataClass):
        raise TypeError(f"obj must be a dataclass, not '{type(obj).__name__}'")
    return _serialize_dataclass(
        obj, printing_format=printing_format, include_names=include_names
    )


def deserialize_dataclass(
    dct: dict,
    dataclass: DataClass,
    build_instance: bool = False,
    dict_of_collections: Optional[
        dict[get_args(PERMITED_KEY_TYPES), dict[get_args(PERMITED_KEY_TYPES), Any]]
    ] = None,
):
    """Deserializes a dataclass instance."""

    if not isinstance(dataclass, DataClass):
        raise TypeError(
            f"dataclass argument must be a dataclass isntance, not '{type(dataclass).__name__}'"
        )
    return _deserialize_dataclass(
        dct,
        dataclass,
        build_instance=build_instance,
        dict_of_collections=dict_of_collections,
    )
