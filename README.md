# Rellang - A relational calculus langauge

Just got started on this. It is my first time writing a programming language so happy for any feedback or contributions.

## Project Goals

- [ ] Parse set expressions
- [ ] Parse relational expressions

    - [ ] Fix parsing confusion between relations and sets for coproduct and product
    - [ ] Add converses and complements
- [x] Define set expressions
- [x] Define relational expressions
- [ ] Expand definitions statement
- [ ] export statement
  - [ ] Compile exported statements to latex code
- [ ] Functions to build expressions (taking set or relation expressions as arguments)
- [ ] Basic Structural relations, Full, Empty, Copy, First, Second, Collapse, Left, Right
- [ ] Defined Structural relations (standard library)
- [ ] VSCode extension for syntax highlighting, error messages inline


## Using vevn:

~/shared_python_venvs/ai

## Pytest

Uses pattern `filename__test.py`
Run ptw to run tests in watch mode.

## To Install Packages:

Install external packages
`pip install -r requirements.txt`

`pip install -r dev-requirements.txt`

Install my own package
`pip install -e .`

Single Command
`pip install -r dev-requirements.txt && pip install -r requirements.txt && pip install -e .`

## To Run Jupyter Notebook

jupyter notebook

## Type Hints

To make some type annoations work properly you need to add:
`from __future__ import annotations`
At the top of the file.
