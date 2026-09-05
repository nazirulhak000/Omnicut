"""
Modular pipeline stages for OmniCut Pro Studio.
"""

from scripts.stages.source_resolution import SourceResolutionStage
from scripts.stages.script_stage import ScriptStage
from scripts.stages.voice_stage import VoiceStage
from scripts.stages.subtitle_stage import SubtitleStage
from scripts.stages.audio_mix_stage import AudioMixStage
from scripts.stages.shot_matching_stage import ShotMatchingStage
from scripts.stages.video_assembly_stage import VideoAssemblyStage

__all__ = [
    "SourceResolutionStage",
    "ScriptStage",
    "VoiceStage",
    "SubtitleStage",
    "AudioMixStage",
    "ShotMatchingStage",
    "VideoAssemblyStage",
]
