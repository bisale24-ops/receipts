# Report prepared for python-docx

**Where:** `pyproject.toml`

```toml
classifiers = [
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    ...
]
requires-python = ">=3.9"
```

**The conflict:** the trove classifiers advertise 3.7 and 3.8, while `requires-python` tells pip the
package needs 3.9 or newer.

**Why it matters:** pip enforces `requires-python` and ignores the classifiers. PyPI displays the
classifiers. A user on 3.7 or 3.8 sees a package that says it supports them and gets
`ERROR: Package 'python-docx' requires a different Python` when they install it.

**The fix is one of two lines:** drop the 3.7 and 3.8 classifiers, or lower `requires-python` if
those versions are in fact supported.
