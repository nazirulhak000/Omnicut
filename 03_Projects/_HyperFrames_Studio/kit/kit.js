// OmniCut HyperFrames kit — behaviour shared by every clip.
// Clip files own their cuts and motion; this owns the channel-standard pieces.
window.HF = {
  // Full-frame paper flash on #flash. Usage: const flash = HF.flash(tl); flash(3.06, 0.95, 0.32);
  flash(tl) {
    return (t, peak = 0.85, dur = 0.28) =>
      tl.fromTo("#flash", { opacity: peak }, { opacity: 0, duration: dur, ease: "power2.out", immediateRender: false }, t);
  },

  // Karaoke captions injected by kit/build.py: static clause, the spoken word turns volt.
  captions(tl) {
    document.querySelectorAll(".cap").forEach((cap) => {
      const t0 = Number(cap.dataset.start);
      tl.fromTo(cap.firstElementChild, { y: 26, opacity: 0 }, { y: 0, opacity: 1, duration: 0.16, ease: "power3.out" }, t0);
      const words = [...cap.querySelectorAll(".w")];
      words.forEach((w, i) => {
        const s = Number(w.dataset.s);
        tl.set(w, { color: "#ffe600" }, s);
        tl.fromTo(w, { scale: 1 }, { scale: 1.1, duration: 0.08, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }, s);
        if (i + 1 < words.length) tl.set(w, { color: "#fffbe8" }, Number(words[i + 1].dataset.s));
      });
    });
  },

  // Meme sticker card: springs in tilted at tIn, drops out before tOut.
  meme(tl, sel, tIn, tOut, rot = -4) {
    tl.fromTo(sel, { scale: 0.2, rotation: rot - 18, opacity: 0 }, { scale: 1, rotation: rot, opacity: 1, duration: 0.42, ease: "back.out(2)" }, tIn);
    tl.to(sel, { scale: 0.6, opacity: 0, duration: 0.18, ease: "power2.in" }, tOut - 0.18);
  },

  // Frame-stepped sprite sheet (one row, `frames` cells) — seek-safe flipbook for real cut-out
  // stickers (GIF frames with alpha). Element needs .sprite + background-image.
  sprite(tl, sel, frames, t0, dur, ease = "none") {
    const el = document.querySelector(sel);
    el.style.backgroundSize = `${frames * 100}% 100%`;
    const p = { f: 0 };
    const draw = () => (el.style.backgroundPosition = `${(Math.round(p.f) / (frames - 1)) * 100}% 0%`);
    draw();
    tl.fromTo(p, { f: 0 }, { f: frames - 1, duration: dur, ease, onUpdate: draw }, t0);
  },

  // Prepare an SVG stroke for a draw-on; returns the "fully hidden" dash offset.
  // The gap is a little longer than the path so round caps leave no dot before the draw starts.
  dash(el) {
    const len = el.getTotalLength();
    el.style.strokeDasharray = `${len} ${len + 4}`;
    return len + 2;
  },
};
