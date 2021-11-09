from dataclasses import asdict, dataclass, field
from typing import Union
from pytest import fixture
from hypothesis import given, strategies as st

from dataclass_tools.tools import (
    DataClass,
    deserialize_dataclass,
    serialize_dataclass,
    DeSerializerOptions,
    METADATA_KEY,
)


@given(st.floats(), st.characters())
def test_float_str_flat_strucuture(age, name):
    @dataclass
    class Child:
        age: float
        name: str

    child = Child(age=age, name=name)
    assert serialize_dataclass(child) == asdict(child)


@given(st.tuples(st.tuples(st.floats(), st.characters())), st.characters())
def test_float_str_tupple_nested_strucuture(childs_tuples, name_parent):
    @dataclass
    class Child:
        age: float
        name: str

    @dataclass
    class Parent:
        childs: tuple[Child]
        name: str

    childs = tuple(Child(age=age, name=name_child) for age, name_child in childs_tuples)
    parent = Parent(childs=childs, name=name_parent)

    assert serialize_dataclass(parent) == asdict(parent)


@given(st.lists(st.tuples(st.floats(), st.characters())), st.characters())
def test_float_str_list_nested_strucuture(childs_list, name_parent):
    @dataclass
    class Child:
        age: float
        name: str

    @dataclass
    class Parent:
        childs: list[Child]
        name: str

    childs = list(Child(age=age, name=name_child) for age, name_child in childs_list)
    parent = Parent(childs=childs, name=name_parent)

    assert serialize_dataclass(parent) == asdict(parent)


@given(st.lists(st.tuples(st.floats(), st.characters())))
def test_dict_field(childs_list):
    @dataclass
    class Person:
        age: float
        name: str

    @dataclass
    class Persons:
        persons: dict[str, Person]

    _persons = {
        name_child: Person(age=age, name=name_child) for age, name_child in childs_list
    }
    persons = Persons(persons=_persons)
    assert serialize_dataclass(persons) == asdict(persons)


@given(st.floats(), st.characters())
def test_overwrite_key(age, name):
    OVERWRITE_KEY = "no_name"
    options = DeSerializerOptions(overwrite_key=OVERWRITE_KEY)

    @dataclass
    class Child:
        age: float
        name: str = field(metadata={METADATA_KEY: options})

    child = Child(age=age, name=name)
    child_dict = {"age": age, OVERWRITE_KEY: name}
    assert serialize_dataclass(child) == child_dict


@given(st.characters(), st.characters(), st.characters())
def test_types(name_child, name_parent, job_parent):
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
        persons: list[Union[Child, Adult]] = field(metadata={METADATA_KEY: options})

    child = Child(name=name_child)
    adult = Adult(name=name_parent, job=job_parent)
    person = Persons([child, adult])
    persons_dict = {
        "persons": [
            {"typ": "Child", "name": name_child},
            {"typ": "Adult", "name": name_parent, "job": job_parent},
        ]
    }
    assert serialize_dataclass(person) == persons_dict


@given(st.characters(), st.integers(), st.characters(), st.integers(), st.characters())
def test_flatten(name, age, street_name, house_number, city):
    @dataclass
    class Person:
        name: str
        age: float

    @dataclass
    class StreetAdress:
        street_name: str
        house_number: int
        city: str

    options = DeSerializerOptions(flatten=True)

    @dataclass
    class Citezen:
        person: Person
        location: StreetAdress = field(metadata={METADATA_KEY: options})

    person = Person(name=name, age=age)
    location = StreetAdress(
        street_name=street_name, house_number=house_number, city=city
    )
    citezen = Citezen(person=person, location=location)
    citezen_dict = {"person": asdict(person), **asdict(location)}
    assert serialize_dataclass(citezen) == citezen_dict
