"""Approved-master inputs and non-destructive, deterministic overlay compositions.

The resolver is an owner-aware domain adapter, never a caller-provided path.
Only a server-generated composition hash is approved for this mode; arbitrary
AI HTML cannot replace, retime, mute, or style the locked master track.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import html
import json
import math
from pathlib import Path
import re
import shutil

from scripts.channel_store import ChannelError, is_valid_channel_id


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode()).hexdigest()


def _manifest(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ChannelError(409, "overlay_snapshot_changed", "Approved-master snapshot manifest is unavailable or corrupted") from exc


class HyperFramesOverlay:
    """Freeze a specifically approved input and create a new review candidate."""

    def __init__(self, root, *, resolver, probe=None):
        self.root = Path(root).resolve()
        self.resolver = resolver
        if probe is None:
            from scripts.hyperframes_render import probe_video
            probe = probe_video
        self.probe = probe

    def _path(self, value, *, channel_id=None):
        relative = Path(value)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ChannelError(422, "overlay_path_invalid", "Overlay files must use workspace-relative paths")
        path = self.root / relative
        for parent in [path, *path.parents]:
            if parent == self.root:
                break
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise ChannelError(422, "overlay_path_invalid", "Overlay paths cannot use symlinks or junctions")
        if self.root not in path.resolve().parents:
            raise ChannelError(422, "overlay_path_invalid", "Overlay file escapes the workspace")
        if channel_id:
            parts = relative.parts
            project = len(parts) >= 3 and parts[:2] == ("03_Projects", channel_id)
            export = len(parts) >= 4 and parts[0] == "04_Exports" and parts[1] in {"Ready_to_post", "Posted"} and parts[2] == channel_id
            # Gadget Media has its own registered owner-aware project namespace.
            gadget = len(parts) >= 4 and (parts[:2] == ("03_Projects", "GadgetMedia") or parts[:3] == ("04_Exports", "Ready_to_post", "GadgetMedia") or parts[:2] == ("04_Exports", "GadgetMedia"))
            if not (project or export or gadget):
                raise ChannelError(422, "overlay_path_invalid", "Approved master must be in its channel's project or export namespace")
        return path

    def inspect(self, channel_id, binding):
        if not is_valid_channel_id(channel_id):
            raise ChannelError(422, "channel_invalid", "Invalid channel")
        master = deepcopy(self.resolver(channel_id, deepcopy(binding)))
        if not isinstance(master, dict) or master.get("approved") is not True or master.get("channel_id") != channel_id:
            raise ChannelError(404, "overlay_master_not_approved", "No exact approved master belongs to this channel")
        for field in ("project_id", "artifact_id", "revision", "path", "sha256"):
            if master.get(field) is None or master.get(field) == "":
                raise ChannelError(422, "overlay_master_invalid", f"Approved master lacks {field}")
        path = self._path(master["path"], channel_id=channel_id)
        if not path.is_file() or path.suffix.lower() != ".mp4" or path.stat().st_size > 2 * 1024 ** 3 or _sha(path) != master["sha256"]:
            raise ChannelError(409, "overlay_master_changed", "Approved master file no longer matches its recorded hash")
        specs = self.probe(path)
        try:
            valid = specs["width"] == 1080 and specs["height"] == 1920 and abs(float(specs["fps"]) - 30) < .01 and 0 < float(specs["duration"]) <= 300 and math.isfinite(float(specs["duration"]))
        except (KeyError, ValueError, TypeError):
            valid = False
        if not valid:
            raise ChannelError(422, "overlay_master_specs_invalid", "Approved master must be 1080x1920, 30 FPS, and at most 300 seconds")
        approved = {key: master.get(key) for key in ("channel_id", "project_id", "slot_id", "artifact_id", "revision", "path", "sha256")}
        approved["specs"] = {key: specs.get(key) for key in ("width", "height", "fps", "duration", "audio")}
        approved["master_digest"] = _digest(approved)
        return approved

    def freeze(self, channel_id, project_dir, binding, *, approval):
        source = self.inspect(channel_id, binding)
        if not isinstance(approval, dict) or approval.get("approved") is not True or approval.get("master_digest") != source["master_digest"]:
            raise ChannelError(409, "overlay_approval_required", "Explicit approval must match this exact master revision and hash")
        directory = self._path(project_dir, channel_id=channel_id)
        if not re.fullmatch(r"HF_[0-9a-f]{32}", directory.name) or directory.parent != self.root / "03_Projects" / channel_id:
            raise ChannelError(422, "overlay_project_invalid", "Overlay snapshots belong to a managed HyperFrames project")
        frozen = directory / "overlay_inputs" / source["master_digest"]
        self._path(frozen.relative_to(self.root).as_posix())
        frozen.mkdir(parents=True, exist_ok=True)
        media, manifest = frozen / "master.mp4", frozen / "master.json"
        own, own_manifest = False, False
        try:
            if not media.exists():
                with media.open("xb") as output, self._path(source["path"]).open("rb") as original:
                    own = True
                    shutil.copyfileobj(original, output)
            if _sha(media) != source["sha256"] or self.inspect(channel_id, binding) != source:
                raise ChannelError(409, "overlay_master_changed", "Approved master changed while creating its immutable backup")
            snapshot = {**source, "frozen_path": media.relative_to(self.root).as_posix(), "source_binding": deepcopy(binding)}
            if manifest.exists():
                if _manifest(manifest) != snapshot:
                    raise ChannelError(409, "overlay_snapshot_changed", "Existing approved-master snapshot was changed")
            else:
                with manifest.open("x", encoding="utf-8") as output:
                    own_manifest = True
                    json.dump(snapshot, output, ensure_ascii=False, sort_keys=True)
            return snapshot
        except Exception:
            if own:
                media.unlink(missing_ok=True)
            if own_manifest:
                manifest.unlink(missing_ok=True)
            raise

    def validate_layers(self, channel_id, duration, layers):
        """Read-only raster/timing/owner/hash preflight, returning normalized layers."""
        if not is_valid_channel_id(channel_id) or isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 0 < duration <= 300:
            raise ChannelError(422, "overlay_layers_invalid", "Use a valid channel and approved finite master duration")
        if not isinstance(layers, list) or len(layers) > 24:
            raise ChannelError(422, "overlay_layers_invalid", "At most 24 explicit visual layers are allowed")
        duration = float(duration)
        validated = []
        for original in layers:
            layer = deepcopy(original)
            if not isinstance(layer, dict) or (set(layer) - {"sha256"}) != {"path", "x", "y", "width", "height", "start", "duration"}:
                raise ChannelError(422, "overlay_layers_invalid", "Use only explicit image geometry and timing")
            if not isinstance(layer["path"], str) or not layer["path"] or any(isinstance(layer[key], bool) for key in ("x", "y", "width", "height", "start", "duration")):
                raise ChannelError(422, "overlay_layers_invalid", "Use a local raster path and explicit numeric geometry")
            try:
                x, y, width, height, start, length = [float(layer[key]) for key in ("x", "y", "width", "height", "start", "duration")]
                valid = all(math.isfinite(n) for n in (x, y, width, height, start, length)) and x >= 48 and y >= 48 and width > 0 and height > 0 and x + width <= 900 and y + height <= 1500 and start >= 0 and length > 0 and start + length <= duration + .001
            except (ValueError, TypeError):
                valid = False
            path = self._path(layer["path"])
            parts = Path(layer["path"]).parts
            if not (parts[0] == "02_Assets" or parts[:2] == ("03_Projects", channel_id)):
                raise ChannelError(422, "overlay_layers_invalid", "Overlay image belongs to an unsupported owner namespace")
            if not valid or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"} or not path.is_file():
                raise ChannelError(422, "overlay_layers_invalid", "Layers must be unchanged local raster images within the safe zone and master duration")
            try:
                digest = _sha(path)
            except OSError as exc:
                raise ChannelError(422, "overlay_layers_invalid", "Overlay raster is unavailable") from exc
            if layer.get("sha256") not in (None, digest):
                raise ChannelError(409, "overlay_layer_changed", "Overlay image changed before approval")
            layer["sha256"] = digest
            from PIL import Image
            try:
                if path.stat().st_size > 32 * 1024 ** 2:
                    raise ValueError("Raster overlay exceeds its byte limit")
                with Image.open(path) as image:
                    if image.width * image.height > 16_000_000 or getattr(image, "n_frames", 1) != 1:
                        raise ValueError("Overlay must be a bounded single raster frame")
                    image.verify()
            except (OSError, ValueError, Image.DecompressionBombError) as exc:
                raise ChannelError(422, "overlay_layers_invalid", "Overlay must be a valid single raster frame below 32 MiB and 16 megapixels") from exc
            validated.append(layer)
        return validated

    def compose(self, snapshot, destination, layers):
        """Return a sealed submission directory + worker contract.

        Layers are local raster images with finite clip windows. No authored
        scripts, fonts, text, CSS, transforms, or additional media are accepted.
        Existing master captions remain in their original pixels/audio clock.
        """
        channel_id = snapshot["channel_id"]
        media = self._path(snapshot["frozen_path"], channel_id=channel_id)
        manifest = media.with_name("master.json")
        approved = {key: snapshot.get(key) for key in ("channel_id", "project_id", "slot_id", "artifact_id", "revision", "path", "sha256", "specs")}
        if _digest(approved) != snapshot["master_digest"] or media.parent.name != snapshot["master_digest"] or media.name != "master.mp4" or media.parent.parent.name != "overlay_inputs":
            raise ChannelError(409, "overlay_snapshot_changed", "Approved-master digest or snapshot namespace changed")
        if not manifest.is_file() or _manifest(manifest) != snapshot or _sha(media) != snapshot["sha256"]:
            raise ChannelError(409, "overlay_snapshot_changed", "Approved-master snapshot no longer matches its approval")
        destination = self._path(destination, channel_id=channel_id)
        # Do not permit output into a source namespace or an approved export.
        parts = destination.relative_to(self.root).parts
        if len(parts) != 5 or parts[:2] != ("03_Projects", channel_id) or not re.fullmatch(r"HF_[0-9a-f]{32}", parts[2]) or parts[3] != "overlay_compositions" or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", parts[4]):
            raise ChannelError(422, "overlay_output_invalid", "Compose into a new managed HyperFrames overlay directory")
        if destination.exists():
            raise ChannelError(409, "overlay_output_exists", "Each composition requires a new revision directory")
        duration = float(snapshot["specs"]["duration"])
        validated = [(layer, self._path(layer["path"]), tuple(float(layer[key]) for key in ("x", "y", "width", "height", "start", "duration")))
                     for layer in self.validate_layers(channel_id, duration, layers)]
        destination.mkdir(parents=True)
        files = []
        created = []
        def discard():
            for target in created:
                self._path(target.relative_to(self.root).as_posix()).unlink(missing_ok=True)
            destination.rmdir()
        def copy(source, name, expected):
            target = destination / name
            try:
                with target.open("xb") as output, source.open("rb") as stream:
                    created.append(target)
                    shutil.copyfileobj(stream, output)
                actual = _sha(target)
                if actual != expected:
                    raise ChannelError(409, "overlay_layer_changed", "Approved media changed during composition snapshot creation")
                files.append({"path": name, "sha256": actual})
            except Exception:
                discard()
                raise
        copy(media, "master.mp4", snapshot["sha256"])
        visual = []
        for index, (layer, path, geometry) in enumerate(validated):
            name = f"overlay-{index}{path.suffix.lower()}"
            copy(path, name, layer["sha256"])
            x, y, width, height, start, length = geometry
            visual.append(f'<img id="overlay-{index}" class="clip" src="{html.escape(name)}" data-start="{start}" data-duration="{length}" data-track-index="{index + 2}" style="position:absolute;left:{x}px;top:{y}px;width:{width}px;height:{height}px;object-fit:contain" alt="">')
        audio = bool(snapshot["specs"].get("audio"))
        audio_html = f'<audio id="master-audio" src="master.mp4" data-start="0" data-duration="{duration}" data-track-index="1" data-volume="1"></audio>' if audio else ""
        document = f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:black}}#root{{position:relative;width:100%;height:100%;overflow:hidden}}#master-video{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}}</style></head><body><div id="root" data-composition-id="approved-master-overlay" data-width="1080" data-height="1920" data-duration="{duration}"><video id="master-video" class="clip" src="master.mp4" data-start="0" data-duration="{duration}" data-track-index="0" muted></video>{audio_html}{"".join(visual)}</div></body></html>'
        entry = destination / "index.html"
        try:
            with entry.open("x", encoding="utf-8") as stream:
                created.append(entry)
                stream.write(document)
        except Exception:
            discard()
            raise
        files.append({"path": "index.html", "sha256": _sha(entry)})
        contract = {"master_digest": snapshot["master_digest"], "master_sha256": snapshot["sha256"],
                    "master_path": "master.mp4", "composition_sha256": files[-1]["sha256"],
                    "duration_seconds": duration, "audio": audio, "source": deepcopy(snapshot)}
        return {"source_dir": destination.relative_to(self.root).as_posix(), "files": files,
                "asset_contract": {"approved_master_overlay": contract, "required_audio": [{"role": "music", "sha256": snapshot["sha256"]}] if audio else []},
                "inputs": {"audio_mode": "music_only" if audio else "silent", "duration_seconds": duration,
                           **({"music_path": snapshot["frozen_path"]} if audio else {})},
                "snapshot": deepcopy(snapshot)}
