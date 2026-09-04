import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUp,
  Blend, ChevronsDown, ChevronsLeft, ChevronsRight, ChevronsUp,
  Droplets, Moon, Scissors, Sun, Waves, ZoomIn, ZoomOut,
} from 'lucide-react';

// One glyph per boundary type, so a glance down the timeline says what each
// cut actually does. Every transition used to draw the same Waves icon, which
// told the user only "something happens here".
//
// The pairs are meant to be readable against each other: a wipe is a double
// chevron and a slide is a single arrow (a wipe uncovers, a slide pushes), and
// the two circle effects borrow the zoom glyphs because that is what they read
// as on screen -- circleopen for a push-in, circleclose for a pull-back.
const TRANSITION_ICONS = {
  cut: Scissors,
  fade: Blend,
  fadeblack: Moon,
  fadewhite: Sun,
  dissolve: Droplets,
  wipeleft: ChevronsLeft,
  wiperight: ChevronsRight,
  wipeup: ChevronsUp,
  wipedown: ChevronsDown,
  slideleft: ArrowLeft,
  slideright: ArrowRight,
  slideup: ArrowUp,
  slidedown: ArrowDown,
  circleopen: ZoomIn,
  circleclose: ZoomOut,
};

/** Icon component for a transition id; Waves for anything unrecognised. */
export function transitionIcon(type) {
  return TRANSITION_ICONS[type] || Waves;
}

/** Renders the icon for `type` at the given size. */
export function TransitionIcon({ type, className = 'h-3 w-3' }) {
  const Icon = transitionIcon(type);
  return <Icon className={className} />;
}

export default TRANSITION_ICONS;
