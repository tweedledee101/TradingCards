# Ragnarok Gamez — OBS Stream Setup

Everything here is static HTML/CSS/JS — no server, no build step. Pull this
repo on your streaming machine, open OBS, and point Browser Sources at the
local files.

## 1. Scene layout (bottom to top)

1. **Webcam / Phone** — your main face camera(s), Video Capture Device
   sources.
2. **Border overlay** — `border.html`, full-canvas Browser Source, sits on
   top of the cameras.
3. **Hot Buy overlay** — `hotbuy.html`, its own Browser Source, hidden until
   triggered.

## 2. Adding the overlays in OBS

For both `border.html` and `hotbuy.html`:

- Add Source → Browser Source
- Check "Local file", then browse to the file path
  (e.g. `.../stream-overlay/border.html`)
- Width: 1920, Height: 1080
- Check "Shutdown source when not visible" for `hotbuy.html` only (keeps it
  from running in the background between triggers)
- Check "Refresh browser when scene becomes active" — this is what makes the
  Hot Buy animation replay from the start every time you show it, instead of
  staying frozen on its last frame.

## 3. Triggering a Hot Buy alert

The animation plays once (~4.5s) and fades out on its own. To fire it:

1. Right-click the `hotbuy.html` source → Filters, or just toggle its eye
   icon — either way, assign an OBS Hotkey to it: Settings → Hotkeys →
   find "Show/Hide 'Hot Buy'" and set a key (e.g. F9).
2. Press the hotkey during the show when something hits — the browser
   refresh-on-show setting restarts the CSS animation each time.
3. To customize the text without editing code, change the source URL to
   include query params, e.g.:
   `border.html` stays as-is, but for `hotbuy.html` you can set the URL to
   `hotbuy.html?title=Kurtz%20Auto&sub=%24225` before a show, or duplicate
   the source per card if you want pre-built alerts ready to go.

## 4. Music without it coming through your mic

If you're streaming from a computer (OBS), add music as its own audio
source, never through the room/mic:

- **Local files/playlist**: Add Source → Media Source, point it at your
  music folder, enable "Loop". This appears as its own track in the Audio
  Mixer, separate from your Mic.
- **Spotify/browser audio**: Add Source → Application Audio Capture (BETA on
  Windows), select the app. Same result — it's captured digitally, not
  acoustically, so your mic never picks it up and there's no room echo/bleed.
- In the Audio Mixer, make sure Mic and Music are on separate tracks/levels
  so you can duck the music when you're talking without cutting it entirely.
- **Copyright note**: Whatnot (like Twitch) can auto-mute or flag streams
  playing commercial copyrighted music. Check Whatnot's current creator audio
  policy, or use a royalty-free source (Epidemic Sound, Soundstripe, etc.) so
  this doesn't get silently muted mid-show.

## 5. Webcam + phone as a second camera

Two options to get your phone into OBS as a second face-cam angle:

- **Phone-as-webcam app** (EpocCam, iVCam, Camo, or NDI HX Camera): install
  the app on your phone and its companion source/plugin in OBS. Add it as a
  Video Capture Device or NDI Source alongside your regular webcam.
- **Capture card**: if the phone outputs HDMI (via an adapter), a USB capture
  card turns it into a standard Video Capture Device source, generally lower
  latency than the app-based options.

Getting to Whatnot from OBS depends on whether your account has RTMP/desktop
streaming enabled — check your Whatnot seller settings for a stream key. If
it's mobile-app-only, the practical workaround is running the Whatnot app in
an Android emulator on the same machine and feeding it OBS's Virtual Camera +
Virtual Audio as the emulator's camera/mic input.
