# Report prepared for urllib3

**Where:** `README.md:11`

```html
<a href="https://github.com/urllib3/urllib3/actions?query=workflow%3ACI"><img alt="Coverage Status"
 src="https://img.shields.io/badge/coverage-100%25-success" /></a>
```

**The claim:** coverage is 100%.

**What backs it:** nothing. The number is written into the badge URL by hand, so it is not produced
by a coverage run and does not change when coverage does. The link points at the CI workflow, which
makes it read like a live status badge.

`README.md:30` repeats the claim in prose ("100% test coverage").

**Not a bug report, and possibly intentional** — urllib3 does enforce full coverage in CI, so the
number is currently true. The point is narrower: the badge cannot stop being true, because nothing
computes it. A shields endpoint badge, or a coverage service badge, would assert the same thing and
be able to go red.

Related: #2551 removed the codecov link from the README, which is presumably when the static badge
replaced it.
