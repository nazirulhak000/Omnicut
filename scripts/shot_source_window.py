"""Frame-bounded AI footage allocation, preserving the narration's duration."""
import math

FPS = 30


def scene_window_key(match):
    """Recognize fresh dictionaries of the same approved semantic source."""
    if not isinstance(match, dict) or "end_time" not in match:
        return None
    return (match.get("source_path"), match.get("scene_id"),
            match.get("scene_start", match.get("start_time", 0)),
            match.get("scene_end", match["end_time"]))


class SourceWindowLedger:
    """Consume actual played frame spans, excluding timeline gaps and holds."""

    def __init__(self):
        self.consumed = {}
        self.windows = {}

    def allocate(self, match, raw_duration, requested_start, duration):
        window = source_window(match, raw_duration)
        if not window:
            return None
        key = scene_window_key(match)
        if key in self.consumed:
            # Catalog suggestions use nominal cue lengths. Final visual spans
            # can differ after J-lead/beat snapping: the played cursor wins.
            first_window = self.windows[key]
            window = (first_window[0], min(first_window[1], window[1]))
            requested_start = self.consumed[key]
        else:
            self.windows[key] = window
            requested_start = max(requested_start, float(match.get("consumed_source_until", 0)))
        allocation = allocate_window(window, requested_start, duration)
        if not allocation["hold_only"]:
            self.consumed[key] = math.ceil(allocation["source_end"] * FPS - 1e-6) / FPS
        else:
            self.consumed[key] = window[1] / FPS
        return allocation


def source_window(match, raw_duration):
    if not isinstance(match, dict) or "end_time" not in match:
        return None  # Legacy matches have no declared semantic end.
    try:
        start = max(0.0, float(match.get("start_time", 0)))
        end = min(float(match["end_time"]), float(match.get("scene_end", raw_duration)), raw_duration)
    except (TypeError, ValueError, OverflowError):
        return None
    if not all(math.isfinite(v) for v in (start, end)):
        return None
    first, stop = math.ceil(start * FPS - 1e-6), math.floor(end * FPS + 1e-6)
    return (first, stop) if stop > first else None


def adjacent_window_match(match, window, raw_duration, needed):
    """A synthetic match for the footage right next to ``window``.

    Used when a short AI window would otherwise freeze for longer than the
    allowed hold: the shot continues on the adjacent source footage (after
    the window, or before it when that covers more) so the picture keeps
    moving without jumping to an unrelated topic. Returns (match, seconds
    covered) or (None, 0.0) when no adjacent footage exists.
    """
    first, stop = window[0] / FPS, window[1] / FPS
    after = (stop, min(float(raw_duration), stop + needed))
    before = (max(0.0, first - needed), first)
    best = max((after, before), key=lambda span: span[1] - span[0])
    covered = best[1] - best[0]
    if covered < 1 / FPS:
        return None, 0.0
    adjacent = {key: value for key, value in match.items() if key != "consumed_source_until"}
    adjacent.update({
        "start_time": best[0],
        "end_time": best[1],
        "scene_start": best[0],
        "scene_end": best[1],
        "scene_id": f"{match.get('scene_id', 'ai')}+adjacent",
        "adjacent_to": {"start": first, "end": stop},
    })
    return adjacent, covered


def coalesce_short_windows(groups, boundaries, onsets, matches, raw_duration,
                           max_hold=None, overrides=None, exhausted=None):
    """Play a short shared match once, then hold; retain cuts when it fits.

    With ``max_hold`` (seconds) and an ``overrides`` dict, a shortfall longer
    than ``max_hold`` is not frozen: after the window plays once the shot
    continues on adjacent footage. The continuation group is a new list
    object; ``overrides[id(list)] = (list, adjacent_match)`` tells the caller
    which match it plays. When no adjacent footage can cover the shortfall,
    the legacy play-once-then-hold behaviour is kept and the id of the held
    cue list is added to ``exhausted`` (a set) so callers can tag it.
    Without ``max_hold`` the behaviour is exactly the legacy one.
    """
    output, times, starts = [], [boundaries[0]], [onsets[0]]
    index = 0
    while index < len(groups):
        match = matches[groups[index][0]] if groups[index][0] < len(matches) else None
        stop = index + 1
        while stop < len(groups) and matches[groups[stop][0]] is match:
            stop += 1
        window = source_window(match, raw_duration)
        duration = boundaries[stop] - boundaries[index]
        window_len = (window[1] - window[0]) / FPS if window else 0.0
        if (
            window and max_hold is not None and overrides is not None
            and duration > window_len + max_hold + 1e-6
        ):
            cues = [cue for group in groups[index:stop] for cue in group]
            play = max(window_len, .5)
            split = math.floor((boundaries[index] + play) * FPS + 1e-6) / FPS
            needed = boundaries[stop] - split
            adjacent, covered = adjacent_window_match(match, window, raw_duration, needed)
            if adjacent is not None and needed >= .2 and covered >= needed - max_hold - 1e-6 \
                    and split - boundaries[index] >= .2:
                continuation = list(cues)
                overrides[id(continuation)] = (continuation, adjacent)
                output.append(cues)
                times.append(split)
                starts.append(None)
                output.append(continuation)
                times.append(boundaries[stop])
                starts.append(onsets[stop])
                index = stop
                continue
            if exhausted is not None:
                exhausted.add(id(cues))
            cursor = boundaries[index]
            while cursor < boundaries[stop] - 1e-6:
                remaining = boundaries[stop] - cursor
                length = min(9.5, remaining)
                if 0 < remaining - length < .2:
                    length = remaining - .2
                cursor = min(boundaries[stop], round((cursor + length) * FPS) / FPS)
                if boundaries[stop] - cursor < 1 / FPS:
                    cursor = boundaries[stop]
                output.append(cues)
                times.append(cursor)
                starts.append(onsets[stop] if cursor == boundaries[stop] else None)
        elif window and duration > window_len + 1e-6:
            cues = [cue for group in groups[index:stop] for cue in group]
            cursor = boundaries[index]
            while cursor < boundaries[stop] - 1e-6:
                remaining = boundaries[stop] - cursor
                # Leave room for beat/motion adjustment at a topic boundary;
                # renderer and preview both cap a freeze tail at ten seconds.
                length = min(9.5, remaining)
                if 0 < remaining - length < .2:
                    length = remaining - .2
                cursor = min(boundaries[stop], round((cursor + length) * FPS) / FPS)
                # Keep the exact final narration endpoint, including subframes.
                if boundaries[stop] - cursor < 1 / FPS:
                    cursor = boundaries[stop]
                output.append(cues)
                times.append(cursor)
                starts.append(onsets[stop] if cursor == boundaries[stop] else None)
        else:
            for i in range(index, stop):
                output.append(groups[i])
                times.append(boundaries[i + 1])
                starts.append(onsets[i + 1])
        index = stop
    return output, times, starts


def allocate_window(window, requested_start, duration):
    first, stop = window
    cursor = max(first, min(math.floor(requested_start * FPS + 1e-6), stop - 1))
    frames = min(stop - cursor, max(1, math.ceil(duration * FPS - 1e-6)))
    # Round seeks downward: rounding upward can seek to the next source frame.
    start = math.floor(cursor / FPS * 1_000_000) / 1_000_000
    end = min(stop / FPS, start + duration, (cursor + frames) / FPS)
    freeze = max(0.0, duration - (end - start))
    return {"raw_offset": start, "source_end": end, "freeze_tail": freeze,
            "source_window": {"start": first / FPS, "end": stop / FPS},
            "hold_only": requested_start * FPS >= stop - 1e-6}
