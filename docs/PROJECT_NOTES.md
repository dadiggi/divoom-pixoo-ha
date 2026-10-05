# Project notes – Divoom Pixoo 64 animated Home Assistant dashboard

Handoff summary for continuing development in a new chat session.
Repository: **https://github.com/dadiggi/divoom-pixoo-ha** (public).

---

## 1. Owner setup

| Item | Value |
|---|---|
| Display | Divoom Pixoo 64 at `192.168.50.223`, usually at **low brightness (< 40–50 %)** |
| Home Assistant | Reachable from the Pixoo over plain **http** on the LAN (`http://192.168.50.X:8123`) |
| HA integration | [gickowtf/pixoo-homeassistant](https://github.com/gickowtf/pixoo-homeassistant) (`divoom_pixoo`). Its "List of pages in YAML" holds two `gif` pages. |
| Location / language | Zagreb, Croatia. Day names are shown in Croatian: PO UT SR ČE PE SU NE. |
| Page rotation | Two Pixoo pages, `duration: 5` each, so each page reappears every 10 s |

### Entities used

| Purpose | Entity |
|---|---|
| Indoor temperature | `sensor.netatmo_smart_thermostat_current_temperature` |
| Outdoor temperature | `sensor.outdoor_module_temperature` |
| Indoor humidity | `sensor.wellbeing_electrolux_air_purifier_humidity` |
| Outdoor humidity | attribute `humidity` of `weather.openweathermap_current` |
| Air quality index | `sensor.zagreb_1_croatia_air_quality_index` |
| Washer state machine | `input_select.washing_machine_state_machine` |
| Dryer state machine | `input_select.dryer_state_machine` |
| Bambu P1S printer | `sensor.p1s_01p00c462500605_print_status`, `_remaining_time` (minutes), `_print_progress` (%) |
| Weather + forecasts | `weather.meteo` (daily **and** hourly via `weather.get_forecasts`) |
| Sun | `sun.sun` (`next_rising`, `next_setting`, `below_horizon`) |

- **Washer/dryer states** follow the "Appliance notifications" blueprint: `idle`, `job_ongoing`, `job_completed`, `paused`, `detached_overload`, `unplugged`.
- **Printer status mapping:** printing/running/busy → run; paused → pause; preparing/slicing/init → prep; finished/completed → done; error/failed → err; idle; offline.

---

## 2. Architecture

```
HA automation (every minute + on any relevant state change)
  → weather.get_forecasts (daily + hourly)
  → builds a JSON payload → base64 → shell_command.pixoo_animated_render
      → python3 /config/pixoo/pixoo_render.py <base64>
          → writes /config/www/pixoo/{weather.gif, dashboard_0.gif, dashboard_1.gif,
                                      dashboard_2.gif, dashboard.gif, status.txt}
Pixoo integration: two page_type: gif pages download the GIFs from /local/pixoo/ and loop them on-device.
```

**Why this design:** a `components` page in the integration is pushed as one still frame (`PicNum: 1`), so it can't animate. A `gif` page makes the Pixoo download and loop a GIF itself, so animation is smooth and nothing streams per frame.

**GIF format:**
- 64×64, `MO.L` frames × 125 ms: 16 at default settings (2 s loop), up to 32 for slow speeds, 1 when moving parts and effects are both 0. Pillow merges identical consecutive frames, so still stretches cost nothing.
- One shared 255-colour palette (median cut, no dithering).
- Typically 10–55 KB per file.
- Written atomically (tmp file + `os.replace`).

**Render time:** about 0.7–2.1 s per run on a desktop at default motion; slow motion speeds (24–32 frames) up to ~3.5 s. Van Gogh/comic plus a theme are the heaviest. Pillow is the only dependency and already ships with HA.

### Repository layout

```
pixoo/pixoo_render.py                       the renderer (~6,100 lines, single file)
homeassistant/packages/pixoo_animated.yaml  HA package: helpers, shell_command, automation
homeassistant/pixoo_pages.yaml              paste into the Pixoo integration page list
legacy/components_flat.yaml                 first static components-page version (no script)
legacy/components_3d.yaml                   3D static components-page version (stencil-gradient digits)
docs/previews/*.gif|png                     previews used in README
docs/PROJECT_NOTES.md                       this file
README.md, LICENSE (MIT)
```

### Install / update on HA

1. Copy `pixoo/pixoo_render.py` to `/config/pixoo/pixoo_render.py`.
2. Copy `homeassistant/packages/pixoo_animated.yaml` to `/config/packages/`.
3. Make sure `configuration.yaml` has `homeassistant: packages: !include_dir_named packages`.
4. **Restart** HA whenever the package changes. A script-only change needs no restart; the next minute's render picks it up.

**Pixoo page URLs** (`pixoo_pages.yaml`):
- `.../local/pixoo/weather.gif?v={{ as_timestamp(now()) | int }}`
- `.../local/pixoo/dashboard_{{ ((as_timestamp(now()) | int) // 10) % 2 }}.gif?v=...`

The `?v=` part is a cache-buster.

### Debugging
- `http://<HA-IP>:8123/local/pixoo/status.txt` shows the last render time, design, theme, colours, `all_idle`, and any tracebacks.
- Render failures are written to the HA log (logger `pixoo_render`).
- A failed page renders a "RENDER ERROR" GIF instead of disappearing, and the other pages are still written.
- The automation trace shows `returncode` / `stderr` of the shell command.
- `python3 pixoo_render.py --demo` renders built-in demo data. The env var `PIXOO_OUT` overrides the output folder.

---

## 3. HA helpers (in the package)

| Helper | Options | Meaning |
|---|---|---|
| `input_select.pixoo_design` | classic, mondrian, van_gogh, hokusai, klimt, digital_rain, block_3d, hud, comic, mech, platformer, purist, kid, kid_dark, starship, rotate, rotate (no classic) | **What** it looks like (layout + style) |
| `input_select.pixoo_theme` | original, seasonal (auto), neon, steel, synthwave, crimson_desert, christmas, halloween, retro_platformer, rotate | **How** it's coloured; works on **every** design |
| `input_select.pixoo_rotation` | daily, every 6 hours, hourly | Interval used when design and/or theme = `rotate` (they rotate independently, theme offset by 3) |
| `input_select.pixoo_colors` | vivid (recommended), extra vivid, soft, off | LED calibration (gamma + saturation); not a style |
| `input_select.pixoo_background` | design default + 24 backgrounds (black, midnight, charcoal, forest, burgundy, ocean, white paper, black paper, kraft paper, notebook, graph paper, blueprint, chalkboard, wood, brick, carbon, denim, linen, terrazzo, starfield, day sky, sunset, polka dots, stripes) | Background for classic, hud, digital_rain, block_3d, mech, purist, kid, kid_dark. Art designs, comic, platformer and starship keep their own (owner's choice). |
| `input_select.pixoo_language` | english, hrvatski | Labels of purist and kid |
| `input_number.pixoo_motion_level` | 0–5 (default 5) | Moving parts: how much moves |
| `input_number.pixoo_motion_speed` | 0–5 (default 3) | Moving parts speed |
| `input_number.pixoo_effects_frequency` | 0–5 (default 3) | How often effects happen |
| `input_number.pixoo_effects_speed` | 0–5 (default 3) | Effect speed |
| `input_boolean.pixoo_initialized` | on/off | Set by the first-run automation after applying slider defaults |
| `input_text.pixoo_saved_settings` | JSON ≤ 255 chars (worst case 177) | Snapshot from `script.pixoo_save_settings`; `script.pixoo_restore_settings` applies it; `script.pixoo_reset_motion` sets 5/3/3/3 |

**Restore rule:** never give these helpers `initial:` — in HA that overrides the restored value on every restart (the first motion patch had this bug; fixed). Without `initial`, an input_number with no history starts at `min` (0 = still image), which is why the `pixoo_first_run_defaults` automation exists.

Defaults (5/3/3/3, design default background) reproduce the pre-motion-control output; only the effects moved to the event scheduler changed slightly (AQI shine, Klimt shimmer, rain sweeps, HUD glitch timing).

**`seasonal (auto)`** is `original` most of the year, `halloween` from Oct 24–31 and `christmas` from Dec 1 to Jan 6. The legacy values `auto`, `rotate daily`, `rotate hourly` and `rotate daily (art only)` are still parsed.

---

## 4. Payload sent to the script (JSON keys)

| Key | Contents |
|---|---|
| `design`, `theme`, `rotation`, `vivid` | The helper values |
| `background`, `lang` | Background name, label language |
| `motion`, `motion_speed`, `fx`, `fx_speed` | Motion helpers as ints (template uses `| float(default) | int`, so unknown states fall back to defaults; the script clamps to 0–5) |
| `t_in`, `t_out`, `h_in`, `h_out`, `aqi` | Raw sensor states |
| `wm`, `td`, `pr` | Appliance states |
| `wm_age`, `td_age`, `pr_age` | Seconds since `last_changed` (resets on HA restart) |
| `pr_left`, `pr_pct` | Printer time left (minutes) and progress (%) |
| `time` ("HH:MM"), `date` ("4.10"), `dow` | `dow` is the Croatian 2-letter day name |
| `today` | ISO date |
| `sun` | `sun.sun` state |
| `sunrise`, `sunset` | "HH:MM" |
| `wind_speed`, `wind_unit`, `wind_bearing` | Still sent but **unused** (the wind card was removed) |
| `weather` | `{condition, temperature}` from `weather.meteo` |
| `forecast` | Up to 5 daily entries `{d, wd, date, c, hi, lo}`. If the first entry is today, it supplies today's high/low. |
| `hourly_ok`, `hourly` | Remaining hours of **today** only: `{t, p (precip %), mm, c}` |

---

## 5. Shared behaviour (all designs)

- **Two pages:** a dashboard (temperatures, humidity, AQI, umbrella forecast, appliances) and a weather page (time, date, day, current condition, current temperature, today's high/low, 4-day forecast).
- **Bottom-row logic:**
  - All of washer, dryer and printer idle or off: show **sunrise/sunset only**.
  - Anything active: alternate on each page visit between the appliances and sunrise/sunset. `dashboard_0` = appliances, `dashboard_1` = sun card, and `dashboard_2` is a copy of `dashboard_1` for old `% 3` URLs.
- **Idle appliances** show "last used" age, e.g. 🕒 3M / 2H / 2D.
- **Umbrella forecast:** looks at the remaining hours of today. Rain is expected if any hour has ≥ `RAIN_PROB` (40 %), ≥ `RAIN_MM` (0.2 mm), or a rainy condition. It shows an open umbrella with rain, or a closed umbrella with sun. It's hidden if no hourly data is available.
- **Night:** a `sunny` condition is replaced by `clear-night` when the sun is below the horizon.
- **LED colour correction** (`led_correct`): saturation boost, then gamma. Presets: vivid (1.8, 1.3), extra vivid (2.2, 1.5), soft (1.4, 1.15), off. This fixes washed-out colours at low panel brightness, where dark navy otherwise showed as bright blue.
- **Readability rule:** values must never be scrambled or animated into wrong digits. The digital-rain "decode scramble" was removed for exactly this reason; it showed 10:11 instead of 10:31. Use highlight sweeps (`glint`) instead.

---

## 6. Designs

| Design | Key look |
|---|---|
| **classic** | Bevelled 3D tiles, gradient digits with a glint sweep. AQI is a continuous colour gauge (lit to the value, dotted beyond, travelling shine, pointer). Appliance status strips. Hand-tuned per-theme palettes and tile styles (brick, snow, steel). |
| **mondrian** | Black grid with white and primary-colour cells that change with data. Outdoor cell: blue < 10 °C, yellow 10–25 °C, red > 25 °C. Blue umbrella cell for rain, yellow with a red square for dry. Washer fills blue, dryer red, printer fills yellow with progress. Colour squares run along the lines ("boogie-woogie"). |
| **van_gogh** | Swirling brushstroke sky (flow field with vortices), star-like orbs (AQI orb, sun), wind-swept wheat field. Text uses a dark outline over darkened "calm zones". |
| **hokusai** | Woodblock paper, gradient skies, title cartouches, AQI in a red seal stamp, paper umbrella with Hiroshige-style slanting rain, scrolling waves, snow-capped mountain. |
| **klimt** | Gold-leaf mosaic (spirals, rings, gems, eyes, checks) with a shimmer sweep, black panels flecked with gold, gold-leaf numbers (silver-blue when cold, red-gold when hot), gem-tile AQI gauge. |
| **digital_rain** | Falling glyph-code columns, terminal panels, terminal font. Rain density follows the real weather. A white sweep runs over values. |
| **block_3d** | Perspective room with moving floor grid. Extruded 3D block font. Isometric appliance boxes, shaded spheres, AQI cubes (current one hovering). Forecast as 3D bars (height = high, colour = condition, bars grow in). |
| **hud** | Holographic interface: dot grid, scan line, glitch frames. 270° ring gauges with 7-segment digits, radar sweep. Sun travels its real day arc. Forecast as a glowing line chart. |
| **comic** | Halftone panels with slanted gutters, speech bubbles (temperatures), captions (statuses), AQI "POW" burst with OK!/MEH/UGH!, action bursts and speed lines, rotating sunray panels. |
| **mech** | Steel bulkhead, amber CRT screens (scanlines, rolling band, glow), analog AQI needle dial, annunciator lamps (amber run, green done, red error blinking, blue rain, green dry), hazard stripe, NAV sun screen. |
| **platformer** | Original 8-bit world: AQI as 5 health hearts, temperatures on swinging wooden signs, parallax hills and clouds, sky follows time of day and weather, machines with bubbles and steam, spinning gems, forecast on floating islands. |

| **purist** | Clean and clear. Column headers TEMP / HUMID, labelled rows IN/OUT (SOBA/VANI), AQI number in its category colour + category word, "RAIN TODAY 17:00" (first rainy hour) or NO, appliance rows with words (RUNNING, DONE, IDLE FOR 2H, 62% 1H25). Weather: 2× clock, full day name + date with month name (no 4.10 ambiguity), current temp + ↑high ↓low, condition in words, 4-day table with 3-letter days, small calm icons, ↑/↓ temps. `fit()` picks the longest wording that fits. Ink adapts to the background (dark on light, light on dark); text gets a halo in the background's mean colour. |
| **kid** | Crayon drawing on white paper: house (IN) and tree (OUT) with hand-written temps coloured by warmth, raindrop humidity, AQI as a crayon face (smile → frown), purple umbrella in the rain or a sun in sunglasses, machines as boxes (water sloshing, dryer wiggles, printer toy growing with progress, gold star when done, red ! on error), sun card with smiling suns over a hill and big arrows. Weather: rainbow clock digits (2× crayon font), rainbow day name, big crayon weather drawing, bird flying past (level 4), forecast as little drawings. Crayon texture (paper grain gaps), wobbly circles, scribble fills that overshoot the outline, letters jittered on the line, "line boil" at motion level 5, glitter stars as its effect. Chalk palette on dark backgrounds. Temperatures are whole numbers here (kid style). |

| **kid_dark** | Same drawings as kid (`KID_STYLE = "dark"` switches `kid_pal()` to `KID_DARK_C`): saturated gel-pen colours for black, half-density hatching (`K["sparse"]`) so far fewer LEDs are lit, AQI face drawn as mood-coloured outline + dim hatching + bright features, snow in bright ink. Default background `black_paper`; tone `dark`. ~10 % average LED drive vs ~73 % for kid on white paper. |
| **starship** | Original starship bridge (owner asked for a Star Trek TNG look; declined as a protected production design, built an original one instead, like comic/mech/platformer before). Violet hull plating, bevelled frames with cut corners, viewport with nebula + stars rushing out from a vanishing point (`ss_space`, tier 3), ringed gas giant with drifting bands (`ss_planet`, tier 3), teal/gold readouts with big font, AQI as 8 sensor cells, rain drop / dry sun ring, crew stations per machine (`ss_station`, @protects: status header, drum/toolhead tier 1, console buttons tier 2), sunrise/sunset seen from orbit, running lights (effect clock) and a comet (effect event). Keeps its own backdrop. |

**Platformer hero:** an original **fox** with a teal scarf.
- The scarf flutters as he moves.
- At night he carries a glowing lantern.
- His hood is up when rain is expected.
- He does a happy spin with sparkles when the washer or dryer is "done".
- He walks under the sunrise and sunset signs when everything is idle.

### Fonts (renderer-embedded)
- **From the integration:** `pico` (3×5), `gicko` (6×6), `big` (eleven_pix 6×11).
- **Repaired pico glyphs:** about 36 upstream glyphs were cut to 4 rows (O, F, S, P, T, V, J, …). D is rounded so "2D" can't be read as "20". Croatian accents Č Ć Š Ž are drawn above the base glyph (`ACCENTS`).
- **Open-top 4s** in big and gicko so they can't be mistaken for 9s. The pico 9 has a closed bottom.
- **New fonts:**
  - `block`: pico ×2, 6×10.
  - `tall`: 3×7 terminal.
  - `seg7()`: 7-segment digits with optional unlit "dim" segments and glow.
  - `ext_text()`: extruded 3D text.
- **Purist / kid fonts:**
  - `plain` (3×5 labels): square 0 vs round O, diagonal S vs square 5, diagonal Z vs 2, B vs 8, open-top 4, 5-wide M/W, ↑ ↓ °. Croatian accents via `ACCENTS_FONT["plain"]`.
  - `clear` (4×7 values) and `clear2` (2× clock).
  - `crayon` (5×7 lopsided handwriting digits) and `crayon2` (2×).
  - `ACCENTS_FONT` overrides `ACCENTS` per font; `Canvas.glyph` and `_text` look it up.
- **Text rule learned the hard way:** captions, lamps and bubbles need **≥ 1 px padding** between text and their border, or the letters merge with the frame.

---

## 7. Theme system

- **On classic:** themes are hand-tuned palettes (`THEMES`, `apply_theme`) plus `decorate()`. `original` on classic is `neon`.
- **On every other design:** `theme_post()` recolours every pixel that isn't protected towards the theme's luminance ramp (`GRADES`, strength 0.82), then draws the theme decorations in "free mode":
  - snow + top-edge string lights (christmas)
  - embers (crimson_desert)
  - bats (halloween)
  - scanline + stars (synthwave)
  - clouds + coins (retro_platformer)
  - rivets + glints (steel)
- **Protected from recolouring:**
  - all text (via `Canvas.text`)
  - 7-segment digits
  - functions decorated with `@protects` (`x_lamp`, `c_caption`, `pl_status_bar`, `hud_wire_icon`, `x_needle_gauge`)
  - any colour returned by `aqi_color()` (collected in `_SEMANTIC`)
- **Adding a new indicator:** if it carries meaning through colour, decorate its drawing function with `@protects`.

---

## 7b. Motion system

- **`Motion` class, global `MO`.** `configure(level, mspeed, freq, espeed, seed)` once per page; `main()` sets `MO.g` (GIF frame) for each frame.
  - Loop length `MO.L`: speed table `SPEED_P = (32, 24, 20, 16, 12, 8)` GIF frames per 16-frame design cycle; `L = P` (or `2P` for 12/8). Level 0 with effects → 16–32; both 0 → 1 frame.
  - `MO.m(tier, rest=0)`: design frame (int 0–15) for a moving part of that tier, or the rest pose when `level < tier`. `MO.still(tier)` for inline checks.
  - `MO.e()`: continuous effect clock (0 when effects are off). `MO.fx`: effects enabled. `MO.density()`: particle density by frequency.
  - `MO.event(salt)`: progress 0–1 while an effect event runs, else None. Events per loop from the frequency; frequency 1/2 are gated by `seed % 4` / `seed % 2` (seed = minute of day + page number), so "rare" = some minutes only. Event length from `EVENT_LEN` by effect speed.
- **Design code still thinks in 16 frames**, so nothing inside the old designs had to change for speed: `f` is mapped by integer stepping. Seamless loops are kept because `L` is always a whole number of cycles.
- **Tiers without touching call sites:** `MOTION_TIERS` maps helper names to tiers (or a lambda on the bound arguments, e.g. icon size → 1 for the big current icon, 2 for small forecast icons). `_install_motion_tiers()` wraps them with `_timed()`, which replaces the `f` argument by the tier clock while **keeping the caller's phase offset** (`(f + n*3) % FRAMES` staggering) via a stack of `(value, tier, phase)`; a child never moves while its parent is frozen (`max(tier, parent_tier)`). Page functions get `MO.m(RENDER_TIER.get(design, 3))` as their own `f` (platformer/comic: 4).
- **Effects** read `MO` directly: `glint_pos` (all text glints, rain `r_scan`), AQI gauge shine, `k_glint` + gem sparkle (Klimt), `hud_bg` scan line, `hud_glitch`, `x_screen` CRT band, `decorate()` particles and the christmas edge lights, `kid_glitter`. Static theme ornaments (rivets, light strings, coin) stay when effects are off.
- **Adding an animated helper:** add its name to `MOTION_TIERS`. Adding an effect: use `MO.event(salt)` / `MO.e()` / `MO.fx`. New designs can call `MO.m(tier)` directly (purist and kid do).
- **Verification tools used:** a regression diff against the previous renderer at default settings (only the deliberately changed effects differ) and a "motion heatmap" (pixels that change during the loop, per design × level).

## 7c. Backgrounds and language

- `BACKGROUNDS` = name → `fn(x, y) -> rgb` (procedural, static). `BG_DESIGNS` = design → tone: `dark` (classic, hud, digital_rain, block_3d, mech, kid_dark; dimmed so mean luminance ≤ 52), `quiet` (purist; pattern contrast halved), `raw` (kid). `BG_DEFAULT`: purist black, kid white paper, kid_dark black paper.
- `resolve_background()` → global `BACKDROP` = `{name, pix, mean, light}` or None. `Canvas.__init__` paints it and keeps a per-canvas copy in `cv.bgl`; `is_bg()` treats backdrop pixels as background (so classic theme decorations still find free space). Classic tiles become translucent (`mix(bg, TILE, 0.35)`).
- Hooks: `hud_bg`, `rain_bg`, `b_room` (back wall only), `x_bulkhead` skip their own fill when `cv.bgl` is set.
- `LANGS["en"/"hr"]` + `tr(d)`: all purist/kid wording (state words, AQI categories, days, months, conditions, kid words). Helpers: `aqi_level`, `age_short`, `first_rain_hour`, `today_date`, `fc_weekday`, `fit`.

## 8. Code map (`pixoo/pixoo_render.py`)

- **Constants at the top:** `OUT_DIR`, `FRAMES=16`, `FRAME_MS=125`, `NIGHT_DIM`, `VIVID`, `RAIN_PROB=40`, `RAIN_MM=0.2`.
- **`Canvas` class:**
  - Drawing: `px`, `rect`, `tile`, `sprite`, `text(..., grad, glint, outline, colfn)`.
  - Theme support: `mask` (protected pixels), `is_bg`/`behind` (decorations behind content).
- **Shared helpers:** `appl_list`, `show_sun_card`, `today_and_next`, `cur_temp`, `cur_cond`, `cond_group`, `rain_outlook`, `age_text`, `temp_str`, `aqi_color`, `_hhmm`.
- **Design functions:** each design has a `render_dashboard_<name>(d, f, variant)` / `render_weather_<name>(d, f)` pair; classic is `render_dashboard` / `render_weather`. `page_renderers()` maps names to these pairs.
- **Selection:** `resolve_design`, `resolve_theme`, `rotation_slot`.
- **`main()` pipeline:** resolve design and theme, then for each frame apply the theme, call the renderer, and run `theme_post` if needed. Then `save_gif` (LED correction + shared palette) and write `status.txt`.
- **To add a design:**
  1. Write the two functions (use `MO.m(tier)` for motion, `MO.event()` for effects).
  2. Add the name to `ART_DESIGNS`.
  3. Add it to the `pixoo_design` options in the package.
  4. If it should accept backgrounds, add it to `BG_DESIGNS` (and skip its own fill when `cv.bgl` is set).
  5. Add a README row and a preview.

---

## 9. Workflow and conventions used so far

- **Pushing:** Claude can't push to GitHub from the chat (no credentials, and the GitHub connector wasn't available as a tool). Never paste tokens into chat. Each change is delivered as a **`git format-patch` file**, verified by applying it to a fresh clone of the public repo. The owner then runs:
  ```
  git pull
  git am <patch>
  git push
  ```
  Claude Code (desktop/terminal) was suggested for future direct commits and pushes.
- **Testing before every delivery:**
  - Fuzzing every design with messy values (`unavailable`, `None`, strings, negatives, out-of-range, malformed forecast/hourly).
  - Rendering through the real CLI path with a base64 payload.
  - A mock-HA Jinja render of the package template.
  - Timing and GIF-size checks.
  - Visual checks at true pixels **without** the LED-grid preview, because the grid preview can make dark text on light backgrounds look garbled.
- **Commit history** (oldest → newest):
  1. Initial animated themeable dashboard + weather
  2. Fix dashboard not rendering (glyph crash, per-page isolation, `status.txt`, renamed shell command)
  3. AQI gauge overhaul, sunrise/sunset card, animated weather icons, Steel theme
  4. Sunrise/sunset when idle, umbrella forecast, distinct 4/9, Croatian days
  5. Art designs: Mondrian, Van Gogh, Hokusai, Klimt
  6. FX designs: digital rain, block 3D, HUD (+ new fonts)
  7. Comic, mech, platformer; themes on every design; separate rotation interval
  8. Platformer fox hero
  9. Motion controls (moving parts level/speed, effects frequency/speed), purist and kid designs, 23 selectable backgrounds, English/Hrvatski labels
  10. kid_dark and starship designs, black paper background, settings save/restore scripts, fix: sliders no longer reset on restart
- **Content boundaries:** no copyrighted characters or recognisable franchise elements. Declined requests:
  - Spider-Man style → offered and built the comic design instead.
  - Iron Man style → mech cockpit instead.
  - Star Trek: The Next Generation look → original `starship` bridge design instead (no franchise interface style, insignia, ships or terms).
  - A Mario-like platformer and a Mario-described character → original platformer world and the fox instead.
  - Digital rain is a generic "falling code" style with no film references.
  - Art designs are original pixel art *in the style of* the artists, not copies of specific paintings.

---

## 10. Known caveats and ideas for later

- "Last used" ages restart counting after an HA restart (`last_changed` resets).
- Mondrian is very bright (white cells), so it may be too much at night. The kid design on white paper too (use `chalkboard` at night).
- Purist's "RAIN TODAY" counts any precipitation (also snow), same rule as the umbrella.
- Very slow motion speeds double the frames and render time; on slow HA hardware keep speed ≥ 2.
- Not tested on the physical Pixoo: GIFs up to 32 frames. If the device struggles, keep motion speed at 2–5 (≤ 24 frames).
- Wind data is still in the payload but unused; it could power a future card.
- **Ideas not yet built:**
  - Extra idle cards (Bambu nozzle/bed temperature or filament colour, energy today, CO₂, next calendar event, bin day) — needs entity IDs.
  - Night-time automatic dimming per design.
  - An upstream pull request to gickowtf/pixoo-homeassistant fixing the truncated `pico_8` glyphs.
