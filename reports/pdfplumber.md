# Report prepared for pdfplumber

**Where:** `setup.py`

```python
python_requires=">=3.8",
...
classifiers=[
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    ...
]
```

**The conflict:** the classifiers start at 3.10, while `python_requires` admits 3.8 and 3.9.

**Why it matters:** this is the opposite direction to the usual drift. pip will happily install on
3.8 and 3.9, which the classifiers no longer claim to support, so a user on those versions gets an
install that succeeds and a package nobody is testing for them. If 3.8 and 3.9 are supported, the
classifiers are missing two lines; if they are not, `python_requires` should say `>=3.10`.
