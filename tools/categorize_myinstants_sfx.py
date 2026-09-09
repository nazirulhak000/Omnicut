"""
tools/categorize_myinstants_sfx.py
====================================
Categorize mi_* sound files in 02_Assets/SFX/ into 10 subfolders
based on keyword matching on the filename.

Categories (subfolders created inside 02_Assets/SFX/):
  transition/   - whoosh, swoosh, swipe, whip, pan effects
  notification/ - ding, ping, bell, beep, pop, alert, ring
  meme/         - vine-boom, bruh, fart, oof, sus, skibidi, sigma, rizz, etc.
  game/         - roblox, mario, minecraft, pokemon, fnaf, gta, sonic, etc.
  anime/        - naruto, gojo, anime, demon, slayer, one-piece, etc.
  music/        - song, music, beat, phonk, remix, theme, bgm, jingle
  reaction/     - laugh, wow, gasp, scream, yay, yes, no, wtf, bruh reactions
  horror/       - horror, scary, creepy, ghost, scare, jump, siren
  thai/         - Thai-language or Thai-context sounds (romanized Thai patterns)
  other/        - everything else that doesn't match

Rules:
- Only processes files matching pattern mi_*.mp3
- Original 47 files (no mi_ prefix) stay in root SFX/ unchanged
- Files moved (not copied) to avoid duplicate storage
- If a file already exists in destination, skip it
- Dry-run mode available with --dry-run

Usage:
  python tools/categorize_myinstants_sfx.py           # run for real
  python tools/categorize_myinstants_sfx.py --dry-run # preview only
  python tools/categorize_myinstants_sfx.py --report  # show current state
"""

import sys
import re
import shutil
import pathlib
import argparse
import logging
from collections import defaultdict

# Fix Windows terminal encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFX_DIR = ROOT / "02_Assets" / "SFX"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# ─── Category keyword rules (order = priority) ──────────────────────────────
# Each entry: (category_name, [list of keyword patterns])
# Matching is done on the lowercased filename stem (without mi_ prefix and extension)
# Use regex-compatible strings; they are joined with | and searched with re.search()

CATEGORIES: list[tuple[str, list[str]]] = [
    # ── transition effects ──────────────────────────────────────────────────
    ("transition", [
        r"whoosh", r"woosh", r"whosh", r"swoosh", r"swipe", r"whip.?pan",
        r"swipe", r"whoosh", r"transition", r"pan.?wipe", r"air.?swipe",
        r"slide.?in", r"slide.?out", r"whip$", r"wipe$", r"woooosh",
        r"^woosh", r"sfx.?air", r"swoosh",
    ]),

    # ── notification / UI sounds ────────────────────────────────────────────
    ("notification", [
        r"notif", r"\bding\b", r"\bping\b", r"\bbell\b", r"\bbeep\b",
        r"\bpop\b", r"bubble.?pop", r"alert", r"chime", r"\bring\b",
        r"doorbell", r"phone.?ring", r"ringtone", r"iphone", r"messenger",
        r"whatsapp", r"discord", r"facebook", r"tiktok.?notif", r"your.?phone",
        r"message", r"inbox", r"yo.?phone", r"triple.?ping", r"reward",
        r"level.?up", r"achievement", r"unlock", r"complete", r"success",
        r"correct", r"star.?sound", r"gasp.?chime",
    ]),

    # ── game sounds ─────────────────────────────────────────────────────────
    ("game", [
        r"roblox", r"\bmario\b", r"minecraft", r"pokemon", r"fnaf",
        r"five.?night", r"freddy", r"gta", r"sonic", r"zelda", r"doom",
        r"counter.?strike", r"half.?life", r"fortnite", r"among.?us",
        r"undertale", r"terraria", r"hollow.?knight", r"celeste",
        r"mega.?man", r"kirby", r"pikmin", r"splatoon", r"bayonetta",
        r"mm2", r"murder.?mystery", r"jailbreak", r"piggy", r"doors",
        r"little.?nightmares", r"granny", r"squid.?game", r"brawl",
        r"clash", r"pubg", r"cod\b", r"overwatch", r"league", r"dota",
        r"valorant", r"apex", r"battlefield", r"limbus", r"path.?exile",
        r"genshin", r"honkai", r"wuthering", r"blue.?archive", r"arknights",
        r"identity.?v", r"dead.?by", r"freddy", r"mortal.?kombat",
        r"scorpion.?come", r"street.?fighter", r"mkx", r"injustice",
        r"escape.?room", r"poppy", r"playtime", r"baldi", r"bendy",
        r"skribbl", r"fall.?guys", r"rocket.?league", r"chess", r"tetris",
        r"8.?bit", r"pixel", r"chiptune", r"coin.?pick", r"1.?up",
        r"game.?over", r"press.?start", r"insert.?coin",
    ]),

    # ── anime / manga ───────────────────────────────────────────────────────
    ("anime", [
        r"\banime\b", r"naruto", r"gojo", r"jujutsu", r"demon.?slayer",
        r"tanjiro", r"nezuko", r"one.?piece", r"luffy", r"zoro", r"nami",
        r"dragon.?ball", r"goku", r"vegeta", r"bleach", r"ichigo",
        r"attack.?titan", r"aot\b", r"eren", r"levi", r"fullmetal",
        r"edward", r"alphonse", r"hunter.?x", r"killua", r"gon\b",
        r"hisoka", r"jojo", r"joestar", r"giorno", r"dio\b", r"za.?warudo",
        r"berserk", r"sword.?art", r"sao\b", r"re.?zero", r"emilia",
        r"rem\b", r"konosuba", r"aqua\b", r"megumin", r"overlord",
        r"ainz", r"death.?note", r"light\b", r"ryuk", r"chainsaw",
        r"denji", r"makima", r"spy.?family", r"yor\b", r"loid\b", r"anya",
        r"my.?hero", r"mha\b", r"deku", r"bakugo", r"todoroki",
        r"shoto", r"uraraka", r"inuyasha", r"sailor.?moon", r"evangelion",
        r"shinji", r"rei\b", r"asuka", r"gurren", r"kamina", r"simon\b",
        r"black.?clover", r"fairy.?tail", r"erza", r"natsu", r"gray\b",
        r"danmachi", r"sword.?art", r"re.?zero", r"shield.?hero",
        r"\bara.?ara\b", r"\buwu\b", r"\bnani\b", r"yowai.?mo",
        r"senpai", r"kawaii", r"sugoi", r"hidoi", r"yamete", r"kudesai",
        r"baka\b", r"neko\b", r"oni\b", r"moe\b", r"isekai", r"waifu",
        r"mai.?waifu", r"anime.?wow", r"anime.?shine", r"isekai",
        r"limbus.?company", r"project.?moon",
    ]),

    # ── music / jingle / song ───────────────────────────────────────────────
    ("music", [
        r"\bsong\b", r"\bmusic\b", r"\bbeat\b", r"\bphonk\b", r"\bremix\b",
        r"\btheme\b", r"\bjingle\b", r"\bbgm\b", r"\bsoundtrack\b",
        r"\blo.?fi\b", r"\brap\b", r"\bhip.?hop\b", r"\bedm\b",
        r"careless.?whisper", r"saxophone", r"trumpet", r"piano",
        r"guitar", r"bass.?boost", r"phonk", r"drift", r"sigma.?music",
        r"boss.?music", r"dramatic.?music", r"epic.?music", r"battle.?music",
        r"sad.?music", r"happy.?music", r"suspense", r"tension",
        r"opening", r"ending", r"ost\b", r"intro\b", r"outro\b",
        r"ringtone", r"anthem", r"waltz", r"fanfare", r"overture",
        r"symphony", r"orchestra", r"concert", r"choir", r"chorus",
        r"melody", r"harmony", r"riff", r"solo\b", r"drop\b",
        r"build.?up", r"bass.?drop", r"snare", r"kick\b", r"clap\b",
        r"sax\b", r"flute", r"violin", r"cello", r"harp\b",
        r"dream.?running", r"running.?in", r"never.?gonna", r"rickroll",
        r"friday\b", r"happy\b.*birthday", r"we.?are.?the",
        r"im.?blue", r"old.?town.?road", r"gangnam",
        r"ultra.?instinct", r"wild.?hunt", r"salesman.?squid",
        r"spiderman.?meme.?song", r"indian.?song",
        r"whats.?up.?danger", r"gta.?san",
    ]),

    # ── horror / scary ──────────────────────────────────────────────────────
    ("horror", [
        r"horror", r"scary", r"creepy", r"scream", r"terror", r"ghost",
        r"haunt", r"scare", r"jump.?scare", r"jumpscare", r"monster",
        r"creature", r"evil", r"demon\b", r"devil", r"witch", r"zombie",
        r"dead\b", r"death\b", r"kill\b", r"murder", r"stab", r"knife",
        r"blood", r"gore", r"dark\b", r"shadow", r"nightmare", r"curse",
        r"possessed", r"paranormal", r"exorcism", r"ouija", r"ritual",
        r"satanic", r"hell\b", r"abyss", r"void\b", r"crypt",
        r"coffin", r"grave", r"cemetery", r"graveyard", r"skull",
        r"skeleton", r"spider", r"spider.?man.*scare", r"freddy.?scream",
        r"horrorscare", r"nuclear.?alarm", r"siren", r"alarm",
        r"doll.?green", r"little.?girl.?singing", r"creepy.?little",
        r"x.?files", r"twilight.?zone",
    ]),

    # ── thai language / thai content ────────────────────────────────────────
    # Strategy: Thai romanization has very distinctive character sequences.
    # Common patterns in romanized Thai from myinstants Thai section:
    #   - Consonant combos unique to Thai: kh, ph, th, ch, ng, cch
    #   - Double vowels: aa, uu, ii, uu, oo
    #   - Typical suffixes: -maihw, -aihw, -uuai, -aedng, -aek, -aew
    #   - Thai laughter: 555 (ha = 5 in Thai slang)
    ("thai", [
        # === Specific known Thai sounds ===
        r"tbmuk", r"tlktbmuk", r"tlk\b",
        r"fahhh", r"faaah", r"faae\b",
        r"aimaihwaelw", r"aimmaiw",
        r"sngsay", r"sngsa\b",
        r"thuukt", r"tuukt\b",
        r"wuued\b", r"wued\b",
        r"tununuuuu", r"tununu",
        r"wingng", r"wingeyaaa", r"wingngngkhue",
        r"singsakdi", r"sngskdi", r"singsakdisiththi",
        r"tuengopa", r"teuengopa",
        r"phmkh", r"phomkh",
        r"dukdik",
        r"ngng\b",
        r"khidd\b",
        r"prakaas", r"prkaasr", r"prakaasraangwal",
        r"ephlng", r"ephlngaekepnaikhr",
        r"epnlaan\b", r"epnlan\b",
        r"raebidkratch", r"raebidkracchkaetk",
        r"yuuaimaihw", r"yuaimaihw",
        r"yaaaihmii", r"yaaaihmiikhrang",
        r"yaadiik",
        r"yaangniimant", r"yaangniiman",
        r"yaathamaebb",
        r"cchiib", r"cchibnaakh",
        r"obh.?combi", r"obh\b",
        r"prbmuue",
        r"diitebtaa",
        r"epnaakhr", r"epnakr\b",
        r"7.?tbmuk", r"7tbmuk",
        r"1.?epnlaan",
        r"08.?epidtawai",
        r"ceeday.?huh",
        r"7.?11.?sound.?thailand",
        r"7.?11.?hello", r"7.?11.?mp3",
        r"^mi_m_fixed",
        r"arkh\b",
        r"thuukt.?ng",
        r"dng.?kuuaek",
        r"yuuaimaihw.?uuon", r"yuuaimaihw.?naacchuun",
        r"yamate.?kudesai",
        r"winkku",
        r"aetr\b",
        r"baangracchan",
        r"20.?20.?20.?7.?67.?ver.?thai",
        # === aacchaaryaedng (อาจารย์แดง) series ===
        r"aacchaaryaedng",
        r"aacchaaryaedngkraedk",
        r"aacchaaryaedngdabebil",
        r"aacchaaryaednghii",
        r"aacchaaryaedngkraed",
        # === Broad romanized Thai patterns ===
        # These character combos are VERY rare in English/Japanese/Korean
        r"kracchk", r"kraacch",
        r"epidtaw", r"epidt\b",
        r"ebrk\b", r"ebrkhma",
        r"faaphaa", r"3.?faaphaa",
        r"2aimaidaedkkuuhr",
        r"uuai\b",                      # -uuai ending (อยู่ไม่ไหว)
        r"aihw\b",                      # -aihw ending (ไหว)
        r"aihmaiw",
        r"maihw\b",                     # ไม่ไหว
        r"maihd\b",
        r"aedng\b",                     # แดง
        r"aednch\b", r"aednm\b",
        r"aekaimr",                     # เอกไมร์
        r"aengnnn",
        r"aewddd",
        r"aeycchang",
        r"irj\b",                       # Thai romanization ending suffix
        r"khrangthii", r"khrang\b",
        r"thamaebb",
        r"naakchuun", r"naakh\b",
        r"khuuaekaelw", r"khuuaek",
        r"ebrkh\b",
        r"epnaikhrs",
        r"aehuue",
        r"cchit\b",
        r"iisaan\b",
        r"muuengtham", r"muengthai",
        r"thrrmakratuk", r"thrrm\b",
        r"khratukcchit",
        r"oddediiyw",
        r"manaihm",
        r"kraedaakhuu",
        r"daebilhii",
        r"thaatuth",
        r"ngchaaw\b",
        r"aehuuenaakh",
        r"aeao\b",
        r"aauh\b",
        r"aengnnn",
        r"abandon.?weird.?route",       # Thai meme
        r"weird.?route.?jingle",
        r"3.?2.?1.?go.?green",          # Thai countdown meme
        r"555555",                       # Thai "hahaha" (5 = ha)
        r"5555\b",
        r"1ai.?sas",
        r"kracchkaetk",
        r"epidtawtlk",
        r"12.?kracchkeetk",
        r"7.?epidtawtlk",
        r"13.?ebrk",
        r"19.?ebrk",
        r"2aimaida",
        r"daen\b", r"daen.?b\b",
        r"dng\b",
        r"500.?cigarettes",             # Thai TikTok meme
        r"aednch3",
        r"1.?baangracchan",
        r"1.?108\b",
        r"20.?20.?20.?7\b",
    ]),


    # ── meme / internet culture ─────────────────────────────────────────────
    ("meme", [
        r"vine.?boom", r"\bbruh\b", r"\boof\b", r"\bsus\b", r"skibidi",
        r"\brizz\b", r"\bsigma\b", r"ohio\b", r"\bnpc\b", r"\bbonk\b",
        r"coffin.?dance", r"he.?died", r"sad.?violin", r"mlg",
        r"airhorn", r"air.?horn", r"wasted", r"wrong.?answer",
        r"buzzer", r"error\b", r"record.?scratch", r"dry.?fart",
        r"wet.?fart", r"fart.?meme", r"fart\b", r"queef",
        r"dexter.?meme", r"dank.?meme", r"meme\b",
        r"big.?smoke", r"john.?cena", r"john.?wick", r"to.?be.?continued",
        r"ear.?rape", r"loud.?sound", r"bass.?boost", r"bass.?boosted",
        r"mic.?up", r"ratio\b", r"bozo\b", r"clown",
        r"windows.?xp", r"windows.?7", r"windows.?error", r"windows.?startup",
        r"win31", r"windows.?11", r"windows.?xp.?startup",
        r"among.?sus", r"red.?sus", r"impostor",
        r"what.?the.?hell", r"what.?the.?fuck", r"wtf.?boom",
        r"vine.?boom", r"myinstant", r"instant.?sound",
        r"hit.?or.?miss", r"i.?guess.?they.?never.?miss",
        r"bottom.?text", r"sanctuary.?guardian",
        r"a.?few.?moments.?later", r"spongebob", r"patrick",
        r"you.?stupid", r"idiot", r"you.?are.?an.?idiot",
        r"boomheadshot", r"headshot",
        r"get.?out", r"get.?rekt", r"rekt\b",
        r"peppa.?pig", r"peppa\b",
        r"granny\b",  # scary game but also meme
        r"ambatukam", r"amogus",
        r"skeletons.?clatter", r"rahhh.?skeleton",
        r"nyoom", r"boioioing", r"boing\b",
        r"nope\b", r"\boof\b", r"reeee", r"triggered",
        r"fnaf.?meme", r"fnaf.?har",
        r"my.?mommy.?said",
        r"i.?need.?to.?be.?bred",
        r"cat.?laughing", r"cat.?singing",
        r"zeep.?glorp",  # green alien cat
        r"mr.?beast",
        r"woo.?vu.?luvub",
        r"muhehehe", r"hehehe",
    ]),

    # ── reaction sounds ──────────────────────────────────────────────────────
    ("reaction", [
        r"\blaugh\b", r"laughter", r"giggle", r"chuckle", r"haha\b",
        r"hehehe", r"lol\b", r"rofl", r"\bwow\b", r"\bgasp\b",
        r"shocked", r"shock\b", r"oh.?my", r"omg\b", r"\byay\b",
        r"\byes\b", r"yes.?king", r"yes.?lara", r"\bno\b",
        r"\bwhat\b", r"what.?the", r"oh.?no\b", r"uh.?oh",
        r"aww\b", r"awww", r"cute", r"adorable", r"daww",
        r"booo\b", r"boo\b", r"crowd.?boo", r"crowd.?cheer",
        r"applause", r"clapping", r"cheer\b", r"hooray",
        r"tada\b", r"fanfare", r"confetti",
        r"dramatic\b", r"dun.?dun.?dun", r"ba.?dum.?tss",
        r"ba.?dum", r"rimshot",
        r"\bwhat\b", r"wait.?what", r"\bbruh\b",
        r"pog\b", r"poggers", r"monka", r"pepega",
        r"sigh\b", r"exhale", r"groan", r"moan\b",
        r"scream\b", r"yell\b", r"shout\b",
        r"cry\b", r"crying", r"sob\b", r"whimper",
        r"angry\b", r"rage\b", r"mad\b",
        r"surprised", r"surprise\b",
        r"nervous", r"awkward",
        r"excited", r"excitement",
        r"confused", r"huh\b", r"eh\b", r"uhh",
        r"pain\b", r"ouch\b", r"ow\b",
        r"yippee", r"woo\b", r"whoo",
        r"groan\b", r"ugh\b",
        r"ceeday.?huh",
        r"you.?what.?spongebob",
        r"you.?will.?not.?kill",
        r"get.?out.?meme",
        r"where.?are.?you.?going",
        r"why.?do.?i.?hear",
        r"you.?gotta.?move",
        r"i.?see.?you",
        r"nice\b", r"\bgood\b", r"\bgreat\b",
        r"what.?a.?good.?boy",
        r"you.?are.?my.?sunshine",
        r"semangat",  # "semangat" = spirit/enthusiasm in Malay/Thai context
    ]),
]

# ── fallback category ─────────────────────────────────────────────────────────
FALLBACK_CATEGORY = "other"

# ─── categorize function ─────────────────────────────────────────────────────

def categorize(filename: str) -> str:
    """
    Given a filename like 'mi_vine-boom.mp3', return the category name.
    Returns FALLBACK_CATEGORY if no rule matches.
    """
    stem = filename.lower()
    # Remove mi_ prefix and extension
    if stem.startswith("mi_"):
        stem = stem[3:]
    stem = pathlib.Path(stem).stem  # remove extension

    for category, patterns in CATEGORIES:
        for pat in patterns:
            if re.search(pat, stem, re.IGNORECASE):
                return category

    return FALLBACK_CATEGORY


# ─── main logic ──────────────────────────────────────────────────────────────

def run(dry_run: bool = False, verbose: bool = False):
    SFX_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all mi_*.mp3 files in root SFX_DIR only (not subfolders)
    mi_files = [
        f for f in SFX_DIR.iterdir()
        if f.is_file() and f.name.startswith("mi_") and f.suffix.lower() == ".mp3"
    ]

    log.info("Found %d mi_*.mp3 files to categorize", len(mi_files))

    # Count by category first
    category_counts: dict[str, int] = defaultdict(int)
    plan: list[tuple[pathlib.Path, pathlib.Path]] = []  # (src, dest)

    for f in sorted(mi_files):
        cat = categorize(f.name)
        dest_dir = SFX_DIR / cat
        dest = dest_dir / f.name
        category_counts[cat] += 1
        plan.append((f, dest))
        if verbose:
            log.info("  [%s] %s", cat, f.name)

    # Print preview
    log.info("=" * 60)
    log.info("Category breakdown:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        log.info("  %-15s %4d files  ->  %s", cat + "/", count, SFX_DIR / cat)
    log.info("=" * 60)

    if dry_run:
        log.info("[DRY-RUN] No files moved. Run without --dry-run to proceed.")
        return

    # Create subdirectories and move files
    moved = 0
    skipped = 0
    errors = 0

    for src, dest in plan:
        dest.parent.mkdir(exist_ok=True)
        if dest.exists():
            log.debug("Skip (exists): %s", dest.name)
            skipped += 1
            continue
        try:
            shutil.move(str(src), str(dest))
            moved += 1
        except Exception as e:
            log.error("Error moving %s: %s", src.name, e)
            errors += 1

    log.info("=" * 60)
    log.info("Done: moved=%d  skipped=%d  errors=%d", moved, skipped, errors)

    # Verify originals untouched
    originals = [
        f for f in SFX_DIR.iterdir()
        if f.is_file() and not f.name.startswith("mi_")
    ]
    log.info("Original files in SFX/ root: %d (unchanged)", len(originals))

    # Count result per subfolder
    log.info("\nFiles per category folder:")
    for cat in sorted(set(c for c, _ in CATEGORIES) | {FALLBACK_CATEGORY}):
        folder = SFX_DIR / cat
        if folder.exists():
            count = len(list(folder.glob("*.mp3")))
            log.info("  %-15s %4d files", cat + "/", count)


def report():
    """Show current state of SFX directory."""
    log.info("Current state of %s", SFX_DIR)
    log.info("-" * 50)

    root_files = [f for f in SFX_DIR.iterdir() if f.is_file()]
    log.info("Root files: %d", len(root_files))

    for entry in sorted(SFX_DIR.iterdir()):
        if entry.is_dir():
            count = len(list(entry.glob("*.mp3")))
            log.info("  %-20s %4d files", entry.name + "/", count)

    log.info("-" * 50)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Categorize mi_*.mp3 files in 02_Assets/SFX/ into subfolders"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview categorization without moving files"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show each file and its assigned category"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Show current state of SFX directory"
    )
    args = parser.parse_args()

    if args.report:
        report()
    else:
        run(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
