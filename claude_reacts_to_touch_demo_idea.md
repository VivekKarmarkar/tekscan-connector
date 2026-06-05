# Demo Idea — "Claude Code Literally Senses Force, Live"

A small, raw, **unstaged** video demo of the project's actual thesis: a real external force reaches an AI coding agent in real time and it reacts to it. Built on the `claude-reacts-to-touch` global skill.

## The one-line pitch

> Split-screen, single continuous take: **your hand pressing the FlexiForce strip** (webcam) on one side, **Claude Code calling "GO", reading the live force, and narrating your exact press** (terminal) on the other. No cuts, no narration, no production.

## Why this beats the polished explainer

The existing `tekscan_explainer.mp4` is *produced* — narration, SAM masks, force-synced music, edits. Impressive, but **staged**, so a skeptic can wave it away. This demo's entire value is the opposite: **raw + live + unedited.** The credibility *is* the rawness. You can't fake "I pressed, and 6 seconds later the AI described exactly the shape of my press, including the moment my finger lifted off."

The loop, visible in one frame:
```
your hand → FlexiForce strip → Tekscan MCU → USB (FTDI) → pyftdi → gui_web.py → Claude reads /data → reacts
   (webcam, left)                                                                   (terminal, right)
```

## The killer structure — call-and-response with a NAMED pattern

Don't freestyle a press. Have Claude **call the pattern on camera first**, then read it back:

> Claude: *"two quick taps, then one long hard hold"* → you perform it → Claude prints the bar graph and reads back the exact shape.

This is **falsifiable proof in a single shot** — a recording or a replay cannot know the pattern you performed *on command, just now*. Details that sell it: a clean **release-to-zero gap** mid-press (Claude catches the finger lifting completely off), a near-max **spike** at a called moment, a buzzer-beater.

## Prerequisites (so the take doesn't bite us)

1. **Arm the sensor FRESH before hitting record.** The handle arms once per *real* power-up — do the cold-start ritual first: unplug → wait **≥ 60 s** → strip seated → replug → launch `probe/gui_web.py` **once** → confirm `http://localhost:8777` is streaming. Do NOT record a wedged sensor. (See `debug_log.md`.)
2. **The skill is read-only**, so once streaming, `claude-reacts-to-touch` cannot burn the one-shot during the recording — safe to invoke as many rounds as you want.
3. **Embrace the rhythm honestly:** GO → press ~6 s → reaction prints. The latency beat is *fine* — it makes the liveness legible (viewer sees the cause, then the effect). Don't fight it; the call-and-response *is* the format.

## Keep it unedited

One continuous split-screen take. No cuts. The instant it's edited, it reads as "produced" and loses the "this is real" punch. A single take of GO → press → reaction is the whole demo.

## Recording mechanics

Mirror the earlier `tekscan_live_demo.mp4`: split-screen `ffmpeg` —
- screen via `x11grab` (the Claude Code terminal showing GO + the bar-graph reaction),
- webcam via `v4l2` (the hand on the sensor),
- composited side-by-side, single file.

Claude drives it: start recording → invoke `claude-reacts-to-touch` → call the pattern → react → stop. Out comes a raw clip.

## Status

Idea, parked for "in a while." The `claude-reacts-to-touch` skill is shipped and read-only; the cold-start ritual is documented. Ready to shoot whenever the sensor is freshly armed and streaming.
