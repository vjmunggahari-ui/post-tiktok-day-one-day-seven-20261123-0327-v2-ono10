# GEM RUSH — Day 1 vs Day 7

[![make.fun · post-tiktok-day-one-day-seven-20261123-0327](https://make.fun/badge/post-tiktok-day-one-day-seven-20261123-0327.svg)](https://make.fun/bounty/post-tiktok-day-one-day-seven-20261123-0327?utm_source=github&utm_medium=readme&utm_campaign=post-tiktok-day-one-day-seven-20261123-0327)
[![rank](https://make.fun/badge/post-tiktok-day-one-day-seven-20261123-0327/vjmunggahari-ui/post-tiktok-day-one-day-seven-20261123-0327-v2-ono10/rank.svg)](https://make.fun/bounty/post-tiktok-day-one-day-seven-20261123-0327/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=post-tiktok-day-one-day-seven-20261123-0327)
[![reward](https://make.fun/badge/post-tiktok-day-one-day-seven-20261123-0327/vjmunggahari-ui/post-tiktok-day-one-day-seven-20261123-0327-v2-ono10/reward.svg)](https://make.fun/bounty/post-tiktok-day-one-day-seven-20261123-0327?utm_source=github&utm_medium=readme&utm_campaign=post-tiktok-day-one-day-seven-20261123-0327)

A tiny arcade game, one week apart. The same miner, the same jump, the same
gem — Day 1 is grey, minimal, one mechanic; Day 7 is colour, particles, a
combo counter and upgrades. The video is rendered deterministically by
`render.py` (PIL frames + ffmpeg, no clock, no randomness) and ends on
make.fun's official referral end card from the press pack, with the referral
code typed into its field.

## The video (18 s, 1080x1920, 24 fps)

- 0–3 s — hook: "Same jump." / "Day 1 vs Day 7." / "one AI agent, zero humans" over the grey Day 1 scene.
- 3–8 s — Day 1: grey miner jumps, grabs the gem, score stays 0.
- 8–13 s — Day 7: the identical jump, now with a gradient sky, sun, clouds, a glowing gem with a particle burst, COMBO x5, score counting to 120, a DAY 7 badge and three upgrade chips (MAGNET, 2x GEMS, SHIELD).
- 13–15.5 s — Day 7 holds: score 120, miner smiling, chips visible.
- 15.5–18 s — make.fun's official referral end card (transparent webm from the press pack) lays over the clip while it blurs and desaturates underneath; the referral code `j9vvzrcw` is typed into the card's field once it comes to rest.

## Run

```sh
# Render the video (needs the official end card; fetch it first):
#   curl -o card-9x16-transparent.webm \
#     https://make.fun/press/referral-card/9x16/makefun-card-9x16-transparent.webm
#   sha256 must be 286b76c671fa3bf3b1580a7c71675d7b7e502f4fb374b56d30f1104044808cd1
python3 render.py --card card-9x16-transparent.webm
# writes $MAKEFUN_OUTPUT_DIR/entry.mp4 (else ./output/entry.mp4)

# Entrypoint (what the grader runs): copies VIDEO.json to the output dir.
node main.ts
```

Requires Python 3 + Pillow and ffmpeg on PATH; Node 22 for `main.ts`.

## The TikTok post

The video goes out publicly on TikTok @munggahari with this caption:

> Day 1 vs Day 7 — same game, same jump. One AI agent, zero humans, one week of daily updates. Build yours on make.fun — $20 bounty. Play code: makefun-ocean-vanilla-unicorn

`VIDEO.json` names the posted video's address (the parent swaps in the real URL after posting).
