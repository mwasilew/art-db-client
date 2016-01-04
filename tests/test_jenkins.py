import sys
import pytest
import argparse

import jenkins


def test_colon_separted_type_1():
    with pytest.raises(argparse.ArgumentTypeError):
        jenkins.colon_separted_type("name:")

def test_colon_separted_type_2():
    with pytest.raises(argparse.ArgumentTypeError):
        jenkins.colon_separted_type(":value")

def test_colon_separted_type_3():
    with pytest.raises(argparse.ArgumentTypeError):
        jenkins.colon_separted_type(":")

def test_colon_separted_type_4():
    with pytest.raises(argparse.ArgumentTypeError):
        jenkins.colon_separted_type("")

def test_colon_separted_type_5():
    assert len(jenkins.colon_separted_type("namex:value")) == 2
    assert len(jenkins.colon_separted_type("item_name:item_value")) == 2

