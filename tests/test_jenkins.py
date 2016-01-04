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


def test_pretty_errors_1():
    errors = {"id": ["one error"]}
    assert '"id" - one error' == jenkins.pretty_errors(errors)


def test_pretty_errors_2():
    errors = {"id": ["one error", "two error"]}
    assert '"id" - one error, two error' == jenkins.pretty_errors(errors)


def test_pretty_errors_3():
    errors = {"id": ["one error"],
              "url": ["one error"]}

    assert '"id" - one error' in jenkins.pretty_errors(errors)
    assert '"url" - one error' in jenkins.pretty_errors(errors)

