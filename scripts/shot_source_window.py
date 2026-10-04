"""Frame-bounded AI footage allocation, preserving the narration's duration."""
import math

FPS = 30


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


def coalesce_short_windows(groups, boundaries, onsets, matches, raw_duration):
    """Play a short shared match once, then hold; retain cuts when it fits."""
    output, times, starts = [], [boundaries[0]], [onsets[0]]
    index = 0
    while index < len(groups):
        match = matches[groups[index][0]] if groups[index][0] < len(matches) else None
        stop = index + 1
        while stop < len(groups) and matches[groups[stop][0]] is match:
            stop += 1
        window = source_window(match, raw_duration)
        duration = boundaries[stop] - boundaries[index]
        if window and duration > (window[1] - window[0]) / FPS + 1e-6:
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
