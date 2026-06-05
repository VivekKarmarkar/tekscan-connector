# GelSight — Price Point & Form-Factor Analysis
### From a FlexiForce strip up to "a little larger than a phone" — what fits, and what does it cost?

**Date:** 2026-06-04 · **Goal:** find GelSight sensors spanning the size range from the thin **FlexiForce strip** we used today up to **a bit larger than a phone**, with the **sweet spot ≈ iPhone-size**, and pin down the **prices**.

> **TL;DR:** Only the small, dev-oriented units have **public prices** — **DIGIT $355** and **GelSight Mini $510**. The iPhone-sized **Mobile Series 2**, the slightly-larger-than-phone **Max**, and the new **Modulus** are all **"contact sales."** The **Mini** anchors the FlexiForce/tiny end and is the obvious **starting point**; the **Mobile Series 2** is the **iPhone-size sweet spot**.

---

## Size anchors (for reference)

- **Tekscan FlexiForce A201 strip** — 191 mm × 14 mm × **0.2 mm thin**, 9.53 mm round sensing dot. *The thin, flexible-strip end of the scale.*
- **Phone / iPhone** — ~147–160 mm tall × ~71–78 mm wide × ~8 mm thick (iPhone 15 ≈ 147×72; Pro Max ≈ 160×77). *The user's stated sweet spot.*

> ⚠️ Note: **nothing in the GelSight line is a thin flexible strip.** GelSight sensors are **3D camera modules** (a camera looking up through a coated elastomer gel). The closest analog to the FlexiForce's *small footprint* is the **Mini**; the closest analog to a *phone's size* is the **Mobile Series 2**.

---

## 💲 Price & size table

| Product | Price (USD) | Body size | Sensing pad (FOV) | Size vs anchors | Linux / SDK |
|---|---|---|---|---|---|
| **DIGIT** | **$355** | fingertip-sized module | ~ fingertip | ~ FlexiForce *dot*, but a 3D block | (Meta/FAIR design; resold) |
| **GelSight Mini** ⭐ | **$510** (Robotics pkg $560) | **~32 × 28 mm** (matchbox/coin) | 18.6 × 14.3 mm | **smallest** — ~2× the FlexiForce dot | ✅ **open Python SDK, Linux** |
| **Mobile Series 2** 🎯 | **Contact sales** | grip 45×49×**158 mm**, tip 50×50 mm, 400 g | 17 × 14 mm | **≈ iPhone size** (sweet spot) | ❌ Windows GUI |
| **GelSight Max** | **Contact sales** | 67×67×**245 mm**, 727 g | 14.6 × 8.3 mm | **~1.5× iPhone length** — "a little larger than a phone" | ❌ Windows GUI |
| **GelSight Modulus** | **Contact sales** | handheld, SLR-style lenses, 165 g (Jul 2025) | swappable optics | phone-to-larger | ❌ Windows GUI |
| *Gel cartridges* (consumable) | Mini gel **$57** (marker $70) · DIGIT gel **$42** · Mobile/Max/Modulus **$600 ea** | — | — | the only "pad-only" items | — |

*All prices/dimensions quoted from GelSight's own online store and product datasheets (see Sources). The "$499" sometimes cited for the Mini is its 2023 launch price; the current store price is **$510**.*

---

## The ladder, smallest → largest

1. **DIGIT ($355)** — cheapest, fingertip robotic tactile module. Closest to the FlexiForce *sensing-area* footprint, but a 3D block not a flat film.
2. **GelSight Mini ($510)** ⭐ — **THE dev unit.** Matchbox/large-coin sized (~32×28 mm). 8 MP camera, 25 FPS, RGB LED, user-replaceable gel. ~18.6×14.3 mm active area (≈ 2× the FlexiForce dot). **Only publicly-priced full sensor + the open Linux SDK** → the obvious place to start.
3. **GelSight Mobile Series 2 (contact sales)** 🎯 — **iPhone-size sweet spot.** Handheld; 158 mm grip ≈ iPhone height, 50×50 mm tip, 400 g.
4. **GelSight Max (contact sales)** — 245 mm, 727 g — **"a little larger than a phone,"** the upper bound of the requested range.
5. **GelSight Modulus (contact sales)** — newest (Jul 2025), hot-swappable SLR-style lenses, 165 g.

**Interesting:** all three handhelds have a **fingertip-to-thumbprint-sized sensing pad** (~14–19 mm) regardless of how big the *housing* is — the size differences are mostly grip/optics, not sensing area.

---

## Recommendation

- **To start cheap, Linux-native, and agent-friendly → GelSight Mini ($510).** Publicly priced, open Python SDK, plug-and-play over USB. This is the one we'd buy first.
- **For the iPhone-size sweet spot → Mobile Series 2** (expect "contact sales" pricing and a Windows workflow — i.e., the Tekscan-style wall, which our proof-of-concept shows we can still crack).

### Product images
`gelsight_assets/`: `mini_hero.png`, `mini_case.png`, `mobile.png`, `max.png`, `modulus.png`, `digit.png`.

### Sources
gelsight.com/online-store (Mini $510, Robotics $560, DIGIT $355, gels), /product/gelsight-mini-system, /gelsightmini, Mini datasheet (FOV 18.6×14.3 mm, 8 MP/25 FPS), Mobile Series 2 OnePager (grip 45×49×158 mm, tip 50×50 mm, 400 g), /product/gelsight-mobile ("Request a Quote"), Max datasheet (67×67×245 mm, 727 g), /product/gelsight-max ("contact sales").

*See [`gelsight_preliminary_product_research.md`](gelsight_preliminary_product_research.md) for the API/SDK/Linux/agent findings.*
