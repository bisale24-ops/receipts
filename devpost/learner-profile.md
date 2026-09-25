---
doc: learner-profile
status: approved
---

# Learner profile

**Who.** Aleksandr Khrukalo, Bishkek. Independent developer, KHLab. Seven Android apps live in the
Amazon Appstore, an agent skill contributed upstream to a vendor's own skill set, and four earlier
proofs of concept in this hackathon — each asking one question of a different artifact: what
evidence backs this claim?

**What I am practising here.** Turning four command-line proofs of concept into one product. The
previous four were judged by me the way a maintainer judges a script: does it give the right
answer. That is not the same as a product, and the gap is the whole exercise — one question, one
run, one page a person can send to someone else, and a plain statement of what was not checked.

**What I already know.** Python, `ast`, git plumbing, packaging metadata, pytest, CI, and the four
checkers themselves, which I wrote.

**Where I get it wrong.** Twice in the last week I called something a finding before reproducing
it. Both times the check was right and my reading of it was wrong. The rule I am holding to here:
before any finding leaves the machine, reproduce the claim against the thing it accuses.

**What "done" looks like for me.** It runs on a repository I did not write, the findings survive
being checked by hand, and the page says plainly which questions it could not ask and why.
