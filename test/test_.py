from dataclasses import asdict, dataclass, field
from typing import Union

from dataclass_tools.tools import (
    DESERIALIZER_OPTIONS,
    DataClass,
    DeSerializerOptions,
    deserialize_dataclass,
    serialize_dataclass,
)
from hypothesis import given
from hypothesis import strategies as st
from pytest import fixture


@dataclass
class Child:
    age: float
    name: str


@given(st.floats(), st.characters())
def test_serialize_flat_structure(age, name):

    child = Child(age=age, name=name)
    assert serialize_dataclass(child) == asdict(child)


@given(st.floats(), st.characters())
def test_deserialize_flat_structure(age, name):

    child = Child(age=age, name=name)
    dct = serialize_dataclass(child)
    assert deserialize_dataclass(dct, Child, build_instance=True) == child


@given(st.tuples(st.tuples(st.floats(), st.characters())), st.characters())
def test_serialize_tupple_nested_strucuture(childs_tuples, name_parent):
    @dataclass
    class Parent:
        childs: tuple[Child]
        name: str

    childs = tuple(Child(age=age, name=name_child) for age, name_child in childs_tuples)
    parent = Parent(childs=childs, name=name_parent)

    assert serialize_dataclass(parent) == asdict(parent)


@given(st.tuples(st.tuples(st.floats(), st.characters())), st.characters())
def test_deserialize_tupple_nested_strucuture(childs_tuples, name_parent):
    @dataclass
    class Parent:
        childs: tuple[Child]
        name: str

    childs = tuple(Child(age=age, name=name_child) for age, name_child in childs_tuples)
    parent = Parent(childs=childs, name=name_parent)
    dct = serialize_dataclass(parent)
    assert deserialize_dataclass(dct, Parent, build_instance=True) == parent


@given(st.lists(st.tuples(st.floats(), st.characters())), st.characters())
def test_serialize_list_nested_strucuture(childs_list, name_parent):
    @dataclass
    class Parent:
        childs: list[Child]
        name: str

    childs = list(Child(age=age, name=name_child) for age, name_child in childs_list)
    parent = Parent(childs=childs, name=name_parent)

    assert serialize_dataclass(parent) == asdict(parent)


@given(st.lists(st.tuples(st.floats(), st.characters())), st.characters())
def test_deserialize_list_nested_strucuture(childs_tuples, name_parent):
    @dataclass
    class Parent:
        childs: list[Child]
        name: str

    childs = list(Child(age=age, name=name_child) for age, name_child in childs_tuples)
    parent = Parent(childs=childs, name=name_parent)
    dct = serialize_dataclass(parent)
    assert deserialize_dataclass(dct, Parent, build_instance=True) == parent


@given(st.lists(st.tuples(st.floats(), st.characters())), st.characters())
def test_serialize_list_nested_strucuture_subs_by_attr(childs_list, name_parent):
    options = DeSerializerOptions(subs_by_attr="name")

    @dataclass
    class Parent:
        childs: list[Child] = field(metadata={DESERIALIZER_OPTIONS: options})
        name: str

    childs = list(Child(age=age, name=name_child) for age, name_child in childs_list)
    parent = Parent(childs=childs, name=name_parent)
    parent_dict = asdict(parent)
    parent_dict.update({"childs": [name_child for _, name_child in childs_list]})
    assert serialize_dataclass(parent) == parent_dict


@given(
    st.lists(st.tuples(st.floats(), st.characters()), unique_by=lambda x: x[1]),
    st.characters(),
)
def test_deserialize_list_nested_strucuture_subs_by_attr(childs_list, name_parent):
    options = DeSerializerOptions(subs_by_attr="name")

    @dataclass
    class Parent:
        childs: list[Child] = field(metadata={DESERIALIZER_OPTIONS: options})
        name: str

    childs = list(Child(age=age, name=name_child) for age, name_child in childs_list)
    childs_dict = {child.name: child for child in childs}
    field_dict_pairs = {"childs": childs_dict}
    parent = Parent(childs=childs, name=name_parent)
    parent_dict = asdict(parent)
    parent_dict.update({"childs": [name_child for _, name_child in childs_list]})
    assert (
        deserialize_dataclass(
            parent_dict,
            Parent,
            build_instance=True,
            dict_of_collections=field_dict_pairs,
        )
        == parent
    )


@given(st.lists(st.tuples(st.floats(), st.characters())))
def test_serialize_dict_field(childs_list):
    @dataclass
    class Persons:
        persons: dict[str, Child]

    _persons = {
        name_child: Child(age=age, name=name_child) for age, name_child in childs_list
    }
    persons = Persons(persons=_persons)
    assert serialize_dataclass(persons) == asdict(persons)


@given(st.lists(st.tuples(st.floats(), st.characters())))
def test_deserialize_dict_field(childs_list):
    @dataclass
    class Persons:
        persons: dict[str, Child]

    _persons = {
        name_child: Child(age=age, name=name_child) for age, name_child in childs_list
    }
    persons = Persons(persons=_persons)
    assert deserialize_dataclass(asdict(persons), Persons) == asdict(persons)


@given(st.floats(), st.characters())
def test_serialize_overwrite_key(age, name):
    OVERWRITE_KEY = "no_name"
    options = DeSerializerOptions(overwrite_key=OVERWRITE_KEY)

    @dataclass
    class Child:
        age: float
        name: str = field(metadata={DESERIALIZER_OPTIONS: options})

    child = Child(age=age, name=name)
    child_dict = {"age": age, OVERWRITE_KEY: name}
    assert serialize_dataclass(child) == child_dict


@given(st.floats(), st.characters())
def test_serialize_overwrite_key(age, name):
    OVERWRITE_KEY = "no_name"
    options = DeSerializerOptions(overwrite_key=OVERWRITE_KEY)

    @dataclass
    class Child:
        age: float
        name: str = field(metadata={DESERIALIZER_OPTIONS: options})

    child = Child(age=age, name=name)
    child_dict = {"age": age, OVERWRITE_KEY: name}
    assert serialize_dataclass(child) == child_dict


@given(st.floats(), st.characters())
def test_deserialize_overwrite_key(age, name):
    OVERWRITE_KEY = "no_name"
    options = DeSerializerOptions(overwrite_key=OVERWRITE_KEY)

    @dataclass
    class Child:
        age: float
        name: str = field(metadata={DESERIALIZER_OPTIONS: options})

    child = Child(age=age, name=name)
    child_dict = {"age": age, OVERWRITE_KEY: name}
    assert deserialize_dataclass(child_dict, Child) == asdict(child)


@given(st.characters(), st.characters(), st.characters())
def test_serialize_types_with_Uninon(name_child, name_parent, job_parent):
    options = DeSerializerOptions(add_type=True)

    @dataclass
    class Child:
        name: str

    @dataclass
    class Adult:
        name: str
        job: str

    @dataclass
    class Person:
        person: Union[Child, Adult] = field(metadata={DESERIALIZER_OPTIONS: options})

    child = Child(name=name_child)
    adult = Adult(name=name_parent, job=job_parent)
    persons = Person(adult)
    persons_dict = {
        "person": {"typ": "Adult", "name": name_parent, "job": job_parent},
    }
    assert serialize_dataclass(persons) == persons_dict


@given(st.characters(), st.characters(), st.characters())
def test_deserialize_types_with_Uninon(name_child, name_parent, job_parent):
    @dataclass
    class Child:
        name: str

    @dataclass
    class Adult:
        name: str
        job: str

    table = {"Child": Child, "Adult": Adult}
    options = DeSerializerOptions(add_type=True, subtype_table=table)

    @dataclass
    class Person:
        person: Union[Child, Adult] = field(metadata={DESERIALIZER_OPTIONS: options})

    child = Child(name=name_child)
    adult = Adult(name=name_parent, job=job_parent)
    persons = Person(adult)
    persons_dict = {
        "person": {"typ": "Adult", "name": name_parent, "job": job_parent},
    }

    assert deserialize_dataclass(persons_dict, Person) == asdict(persons)


@given(st.characters(), st.characters(), st.characters())
def test_serialize_types_in_list(name_child, name_parent, job_parent):
    options = DeSerializerOptions(add_type=True)

    @dataclass
    class Child:
        name: str

    @dataclass
    class Adult:
        name: str
        job: str

    @dataclass
    class Persons:
        persons: list[Union[Child, Adult]] = field(
            metadata={DESERIALIZER_OPTIONS: options}
        )

    child = Child(name=name_child)
    adult = Adult(name=name_parent, job=job_parent)
    persons = Persons([child, adult])
    persons_dict = {
        "persons": [
            {"typ": "Child", "name": name_child},
            {"typ": "Adult", "name": name_parent, "job": job_parent},
        ]
    }
    assert serialize_dataclass(persons) == persons_dict


@given(st.characters(), st.characters(), st.characters())
def test_deserialize_types_in_list(name_child, name_parent, job_parent):
    @dataclass
    class Child:
        name: str

    @dataclass
    class Adult:
        name: str
        job: str

    table = {"Child": Child, "Adult": Adult}
    options = DeSerializerOptions(add_type=True, subtype_table=table)

    @dataclass
    class Persons:
        persons: list[Union[Child, Adult]] = field(
            metadata={DESERIALIZER_OPTIONS: options}
        )

    child = Child(name=name_child)
    adult = Adult(name=name_parent, job=job_parent)
    persons = Persons([child, adult])
    persons_dict = {
        "persons": [
            {"typ": "Child", "name": name_child},
            {"typ": "Adult", "name": name_parent, "job": job_parent},
        ]
    }
    assert deserialize_dataclass(persons_dict, Persons) == asdict(persons)


@given(st.characters(), st.integers(), st.characters(), st.integers(), st.characters())
def test_serialize_flatten(name, age, street_name, house_number, city):
    @dataclass
    class Person:
        name: str
        age: float

    @dataclass
    class StreetAdress:
        street_name: str
        house_number: int
        city: str

    options = DeSerializerOptions(flatten=True, add_type=True)

    @dataclass
    class Citezen:
        person: Person
        location: StreetAdress = field(metadata={DESERIALIZER_OPTIONS: options})

    person = Person(name=name, age=age)
    location = StreetAdress(
        street_name=street_name, house_number=house_number, city=city
    )
    citezen = Citezen(person=person, location=location)
    citezen_dict = {
        "person": asdict(person),
        **asdict(location),
        **{"location": "StreetAdress"},
    }
    assert serialize_dataclass(citezen) == citezen_dict


@given(st.characters(), st.integers(), st.characters(), st.integers(), st.characters())
def test_deserialize_flatten(name, age, street_name, house_number, city):
    @dataclass
    class Person:
        name: str
        age: float

    @dataclass
    class StreetAdress:
        street_name: str
        house_number: int
        city: str

    table = {"StreetAdress": StreetAdress}
    options = DeSerializerOptions(flatten=True, add_type=True, subtype_table=table)

    @dataclass
    class Citezen:
        person: Person
        location: StreetAdress = field(metadata={DESERIALIZER_OPTIONS: options})

    person = Person(name=name, age=age)
    location = StreetAdress(
        street_name=street_name, house_number=house_number, city=city
    )
    citezen = Citezen(person=person, location=location)
    citezen_dict = {
        "person": asdict(person),
        **asdict(location),
        **{"location": "StreetAdress"},
    }
    assert deserialize_dataclass(citezen_dict, Citezen) == asdict(citezen)
