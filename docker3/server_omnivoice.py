"""
OmniVoice TTS HTTP Server
Voice Design mode only - 600+ languages supported.
No reference audio needed - describe voice with text attributes.
"""

import os
import io
import logging
from typing import Optional, List
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import torch
import soundfile as sf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OmniVoice TTS Server - Voice Design Mode")

MODEL_PATH = os.getenv("MODEL_PATH", "/models/OmniVoice")
DEVICE = os.getenv("DEVICE", "cuda")

MODEL = None

# ============================================
# VOICE DESIGN ATTRIBUTES
# ============================================
# Use instruct parameter: "female, young adult, high pitch, british accent"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class Age(str, Enum):
    CHILD = "child"
    TEENAGER = "teenager"
    YOUNG_ADULT = "young adult"
    MIDDLE_AGED = "middle-aged"
    ELDERLY = "elderly"


class Pitch(str, Enum):
    VERY_LOW = "very low pitch"
    LOW = "low pitch"
    MODERATE = "moderate pitch"
    HIGH = "high pitch"
    VERY_HIGH = "very high pitch"


class Style(str, Enum):
    WHISPER = "whisper"


class EnglishAccent(str, Enum):
    AMERICAN = "american accent"
    BRITISH = "british accent"
    AUSTRALIAN = "australian accent"
    CANADIAN = "canadian accent"
    INDIAN = "indian accent"
    CHINESE = "chinese accent"
    KOREAN = "korean accent"
    JAPANESE = "japanese accent"
    PORTUGUESE = "portuguese accent"
    RUSSIAN = "russian accent"


# ============================================
# 600+ SUPPORTED LANGUAGES (ISO 639 codes)
# ============================================
# Full list from OmniVoice README

SUPPORTED_LANGUAGES = [
    # Major languages
    "en", "ru", "zh", "ja", "ko", "es", "fr", "de", "it", "pt",
    "tr", "az", "uk", "ar", "hi", "fa", "ur", "bn", "ta", "te",
    "ml", "mr", "gu", "kn", "pa", "th", "vi", "id", "ms", "jv",
    "su", "tl", "my", "km", "lo", "ne", "si", "am", "hy", "ka",
    "he", "yi", "gd", "cy", "br", "eu", "ca", "gl", "oc", "co",
    "bs", "bg", "hr", "cs", "da", "et", "fi", "el", "hu", "lv",
    "lt", "mk", "no", "pl", "ro", "sk", "sl", "sq", "sr", "sv",
    "af", "zu", "xh", "sw", "yo", "ig", "ha", "am", "om", "so",
    "rw", "ln", "lg", "ny", "mg", "mt", "is", "fo", "tt", "ba",
    "cv", "ky", "kk", "uz", "tk", "tg", "mn", "evn", "yue", "wuu",
    "hak", "nan", "min", "gan", "hsn", "cjy",
    
    # Extended language codes from OmniVoice (600+ total)
    "aae", "aal", "aao", "ab", "abb", "abn", "abr", "abs", "abv",
    "acm", "acw", "acx", "adf", "adx", "ady", "aeb", "aec", "afb",
    "afo", "ahl", "ahs", "ajg", "aju", "ala", "aln", "alo", "amu",
    "an", "anc", "ank", "anp", "anw", "aom", "apc", "apd", "arb",
    "arq", "ars", "ary", "arz", "as", "ast", "avl", "awo", "ayl",
    "ayp", "ba", "bag", "bas", "bax", "bba", "bbj", "bbl", "bbu",
    "bce", "bci", "bcs", "bcy", "bda", "bde", "bdm", "beb", "bew",
    "bfd", "bft", "bhr", "bjj", "bjk", "bjn", "bjt", "bkh", "bkm",
    "bky", "bmm", "bmq", "bn", "bnm", "bnn", "bns", "bo", "bou",
    "bqg", "bra", "brh", "bri", "brx", "bsh", "bsj", "bsk", "btm",
    "btv", "bug", "bum", "buo", "bux", "bwr", "bxf", "byc", "bys",
    "byv", "byx", "bzc", "bzw", "ccg", "ceb", "cen", "cfa", "cgg",
    "chq", "cjk", "ckb", "ckl", "ckr", "cky", "cnh", "cpy", "cs",
    "cte", "ctl", "cut", "cux", "cv", "cy", "da", "dag", "dar",
    "dav", "dbd", "dcc", "de", "deg", "dgh", "dgo", "dje", "dmk",
    "dml", "dru", "dty", "dua", "dv", "dyu", "dzg", "ebr", "ebu",
    "ego", "eiv", "eko", "ekr", "el", "elm", "eo", "es", "esu",
    "et", "eto", "ets", "etu", "eu", "ewo", "ext", "eyo", "fa",
    "fan", "fat", "ff", "ffm", "fi", "fia", "fil", "fip", "fkk",
    "fmp", "fr", "fub", "fuc", "fue", "fuf", "fuh", "fui", "fuq",
    "fuv", "fy", "ga", "gbm", "gbr", "gby", "gcc", "gdf", "gej",
    "ges", "ggg", "gid", "gig", "giz", "gjk", "gju", "gl", "glw",
    "gn", "gol", "gom", "gsl", "gu", "gui", "gur", "guz", "gv",
    "gwc", "gwe", "gwt", "gya", "gyz", "hah", "hao", "haw", "haz",
    "hbb", "he", "hem", "hi", "hia", "hkk", "hla", "hno", "hoj",
    "hr", "hsb", "ht", "hu", "hue", "hul", "hux", "hwo", "hy", "hz",
    "ia", "ibb", "id", "ida", "idu", "ig", "ijc", "ijn", "ik",
    "ikw", "is", "ish", "iso", "it", "its", "itw", "itz", "ja",
    "jal", "jax", "jgo", "jmx", "jns", "jqr", "juk", "juo", "jv",
    "kab", "kai", "kaj", "kam", "kbd", "kbl", "kbt", "kcq", "kdh",
    "kea", "keu", "kfe", "kfk", "kfp", "khg", "khw", "kj", "kjc",
    "kjk", "kk", "kln", "kls", "km", "kmr", "kmy", "kn", "kna",
    "knn", "ko", "kol", "koo", "kpo", "kqo", "ks", "ksd", "ksf",
    "kto", "kuh", "kvx", "kw", "kwm", "kxp", "ky", "kyx", "lag",
    "lb", "lcm", "ldb", "lg", "lij", "lir", "lkb", "lla", "ln",
    "lnu", "lo", "loa", "lrk", "lss", "lt", "ltg", "lto", "lua",
    "luo", "lus", "lv", "lwg", "mab", "maf", "mai", "mau", "max",
    "mbo", "mcf", "mcn", "mcx", "mdd", "mde", "mdf", "mek", "mer",
    "meu", "mfm", "mfn", "mfo", "mfv", "mgg", "mgi", "mhk", "mhr",
    "mi", "mig", "miu", "mk", "mkf", "mki", "ml", "mlq", "mn",
    "mne", "mni", "mqy", "mr", "mrj", "mrr", "mrt", "ms", "mse",
    "msh", "msw", "mt", "mtr", "mtu", "mtx", "mua", "mug", "mui",
    "mve", "mvy", "mxs", "mxu", "mxy", "my", "myv", "mzl", "nal",
    "nan", "nap", "nb", "nbh", "ncf", "nco", "ncx", "ndi", "ng",
    "ngi", "nhg", "nhi", "nhn", "nhq", "nja", "nl", "nla", "nlv",
    "nmg", "nmz", "nn", "nnh", "noe", "npi", "nso", "ny", "nyu",
    "oc", "odk", "odu", "ogo", "om", "orc", "oru", "ory", "os",
    "pa", "pbs", "pbt", "pbu", "pcm", "pex", "phl", "phr", "pip",
    "piy", "pko", "pl", "plk", "plt", "pmq", "pms", "pmy", "pnb",
    "poc", "poe", "pow", "prq", "ps", "pst", "pt", "pua", "pwn",
    "qug", "qum", "qup", "qur", "qus", "quv", "qux", "quy", "qva",
    "qvi", "qvj", "qvl", "qwa", "qws", "qxa", "qxp", "qxt", "qxu",
    "qxw", "rag", "rm", "ro", "rob", "rof", "roo", "rth", "ru",
    "rup", "rw", "sa", "sah", "sat", "sau", "say", "sbn", "sc",
    "scl", "scn", "sd", "sei", "shu", "si", "sip", "siw", "sjr",
    "sk", "skg", "skr", "sl", "sn", "snc", "snk", "so", "sol",
    "sps", "sq", "sr", "src", "sro", "ssi", "ste", "sua", "sv",
    "sva", "sw", "szy", "ta", "tan", "tar", "tay", "tbf", "tcf",
    "tcy", "tdn", "tdx", "te", "tg", "tgc", "th", "the", "thq",
    "thr", "thv", "ti", "tig", "tio", "tk", "tkg", "tkt", "tli",
    "tlp", "tn", "tok", "tpl", "tpz", "tqp", "tr", "trp", "trq",
    "trv", "trw", "tt", "ttj", "ttr", "ttu", "tui", "tul", "tuq",
    "tuv", "tuy", "tvo", "tvu", "tw", "twu", "txs", "txy", "udl",
    "ug", "uk", "uki", "umb", "ur", "ush", "uz", "uzn", "vai",
    "var", "ver", "vi", "vmc", "vmj", "vmm", "vmp", "vmz", "vot",
    "vro", "wbl", "wci", "weo", "wes", "wja", "wji", "wo", "wof",
    "xh", "xhe", "xka", "xmf", "xmv", "xmw", "xpe", "xti", "xtu",
    "yaq", "yav", "yay", "ydd", "ydg", "yer", "yes", "yi", "yo",
    "yue", "zga", "zgh", "zh", "zoc", "zoh", "zor", "zpv", "zpy",
    "ztg", "ztn", "ztp", "zts", "ztu", "zu", "zza",
]

# Language code to name mapping for common languages
LANGUAGE_NAMES = {
    "en": "English", "ru": "Russian", "zh": "Chinese", "ja": "Japanese",
    "ko": "Korean", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "tr": "Turkish", "az": "Azerbaijani",
    "uk": "Ukrainian", "ar": "Arabic", "hi": "Hindi", "fa": "Persian",
    "ur": "Urdu", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "ml": "Malayalam", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
    "pa": "Punjabi", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian",
    "ms": "Malay", "jv": "Javanese", "su": "Sundanese", "tl": "Filipino",
    "my": "Burmese", "km": "Khmer", "lo": "Lao", "ne": "Nepali",
    "si": "Sinhala", "am": "Amharic", "hy": "Armenian", "ka": "Georgian",
    "he": "Hebrew", "yi": "Yiddish", "gd": "Scottish Gaelic", "cy": "Welsh",
    "br": "Breton", "eu": "Basque", "ca": "Catalan", "gl": "Galician",
    "oc": "Occitan", "co": "Corsican", "bs": "Bosnian", "bg": "Bulgarian",
    "hr": "Croatian", "cs": "Czech", "da": "Danish", "et": "Estonian",
    "fi": "Finnish", "el": "Greek", "hu": "Hungarian", "lv": "Latvian",
    "lt": "Lithuanian", "mk": "Macedonian", "no": "Norwegian", "pl": "Polish",
    "ro": "Romanian", "sk": "Slovak", "sl": "Slovenian", "sq": "Albanian",
    "sr": "Serbian", "sv": "Swedish", "af": "Afrikaans", "zu": "Zulu",
    "xh": "Xhosa", "sw": "Swahili", "yo": "Yoruba", "ig": "Igbo",
    "ha": "Hausa", "om": "Oromo", "so": "Somali", "rw": "Kinyarwanda",
    "ln": "Lingala", "lg": "Luganda", "ny": "Chichewa", "mg": "Malagasy",
    "mt": "Maltese", "is": "Icelandic", "fo": "Faroese", "tt": "Tatar",
    "ba": "Bashkir", "cv": "Chuvash", "ky": "Kyrgyz", "kk": "Kazakh",
    "uz": "Uzbek", "tk": "Turkmen", "tg": "Tajik", "mn": "Mongolian",
    "yue": "Cantonese", "wuu": "Wu Chinese", "hak": "Hakka", "nan": "Min Nan",
    "tok": "Toki Pona",
}


def load_model():
    global MODEL
    if MODEL is None:
        logger.info(f"Loading OmniVoice model from {MODEL_PATH}")
        from omnivoice import OmniVoice
        MODEL = OmniVoice.from_pretrained(
            MODEL_PATH,
            device_map=DEVICE,
            dtype=torch.float16,
        )
        logger.info(f"Model loaded on device: {DEVICE}")
    return MODEL


@app.on_event("startup")
async def startup_event():
    load_model()


@app.get("/health")
async def health():
    return {"status": "ok", "model": "OmniVoice", "mode": "voice_design", "languages": len(SUPPORTED_LANGUAGES)}


@app.get("/languages")
async def get_languages():
    """Return all 600+ supported languages."""
    return {
        "count": len(SUPPORTED_LANGUAGES),
        "languages": SUPPORTED_LANGUAGES,
        "common_names": LANGUAGE_NAMES,
    }


@app.get("/voices")
async def get_voices():
    """Return predefined voice presets."""
    return {
        "voices": [
            {"id": "male", "instruct": "male"},
            {"id": "female", "instruct": "female"},
            {"id": "male_young", "instruct": "male, young adult"},
            {"id": "female_young", "instruct": "female, young adult"},
            {"id": "male_elderly", "instruct": "male, elderly"},
            {"id": "female_elderly", "instruct": "female, elderly"},
            {"id": "male_child", "instruct": "male, child"},
            {"id": "female_child", "instruct": "female, child"},
            {"id": "male_low", "instruct": "male, low pitch"},
            {"id": "female_high", "instruct": "female, high pitch"},
            {"id": "whisper_male", "instruct": "male, whisper"},
            {"id": "whisper_female", "instruct": "female, whisper"},
            {"id": "british_male", "instruct": "male, british accent"},
            {"id": "british_female", "instruct": "female, british accent"},
            {"id": "american_male", "instruct": "male, american accent"},
            {"id": "american_female", "instruct": "female, american accent"},
            {"id": "russian_male", "instruct": "male, russian accent"},
            {"id": "russian_female", "instruct": "female, russian accent"},
        ],
        "attributes": {
            "gender": ["male", "female"],
            "age": ["child", "teenager", "young adult", "middle-aged", "elderly"],
            "pitch": ["very low pitch", "low pitch", "moderate pitch", "high pitch", "very high pitch"],
            "style": ["whisper"],
            "english_accents": ["american accent", "british accent", "australian accent", "canadian accent", "indian accent", "chinese accent", "korean accent", "japanese accent", "portuguese accent", "russian accent"],
        },
    }


class SynthesizeRequest(BaseModel):
    """Request for voice synthesis using Voice Design mode."""
    text: str
    voice: str = "female"  # Can be: "male", "female", or custom instruct like "female, young adult, high pitch"
    language: Optional[str] = None  # ISO 639 code, auto-detected if not provided


class SynthesizeAdvancedRequest(BaseModel):
    """Advanced request with full control over voice attributes."""
    text: str
    gender: Optional[Gender] = None
    age: Optional[Age] = None
    pitch: Optional[Pitch] = None
    style: Optional[Style] = None
    accent: Optional[EnglishAccent] = None
    custom_instruct: Optional[str] = None  # Custom instruct string (overrides other attributes)
    language: Optional[str] = None


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Synthesize speech using Voice Design mode.
    
    No reference audio needed - describe voice with text attributes.
    
    Examples:
    - voice="male" → male voice
    - voice="female" → female voice  
    - voice="female, young adult, high pitch" → custom voice design
    - voice="male, elderly, low pitch, whisper" → whispering old man
    """
    model = load_model()

    # Build instruct from voice parameter
    instruct = request.voice
    
    # Log synthesis
    lang_info = f", language: {request.language}" if request.language else ""
    logger.info(f"Synthesizing: {len(request.text)} chars, voice: {request.voice}{lang_info}")

    try:
        # Voice Design mode - generate with instruct parameter
        audio = model.generate(
            text=request.text,
            instruct=instruct,
        )

        # audio is a list of np.ndarray at 24 kHz
        audio_data = audio[0] if isinstance(audio, list) else audio
        sample_rate = 24000

        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        buffer.seek(0)

        return Response(content=buffer.read(), media_type="audio/wav")

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SynthesizeCloneRequest(BaseModel):
    """Request for voice cloning synthesis."""
    text: str
    ref_text: str  # Transcription of reference audio


@app.post("/synthesize_clone")
async def synthesize_clone(request: SynthesizeCloneRequest, ref_audio: bytes = None):
    """
    Synthesize speech using Voice Cloning mode.
    
    Requires reference audio file and its transcription.
    The generated voice will match the reference speaker.
    
    Args:
        request: JSON with text to synthesize and ref_text (transcription of reference)
        ref_audio: WAV audio file for voice cloning (uploaded as multipart)
    
    Returns:
        WAV audio file with cloned voice
    """
    model = load_model()

    if ref_audio is None:
        raise HTTPException(status_code=400, detail="ref_audio is required for voice cloning")

    logger.info(f"Voice cloning: {len(request.text)} chars, ref_text: {len(request.ref_text)} chars")

    try:
        # Save reference audio to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(ref_audio)
            tmp_path = tmp.name

        # Voice Cloning mode - generate with reference audio
        audio = model.generate(
            text=request.text,
            ref_audio=tmp_path,
            ref_text=request.ref_text,
        )

        # Cleanup temp file
        os.unlink(tmp_path)

        # audio is a list of np.ndarray at 24 kHz
        audio_data = audio[0] if isinstance(audio, list) else audio
        sample_rate = 24000

        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        buffer.seek(0)

        return Response(content=buffer.read(), media_type="audio/wav")

    except Exception as e:
        logger.error(f"Voice cloning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize_clone_json")
async def synthesize_clone_json(request: dict):
    """
    Voice cloning with JSON request (ref_audio as base64).

    Request body:
    {
        "text": "Text to synthesize",
        "ref_text": "Transcription of reference audio",
        "ref_audio_base64": "base64-encoded WAV audio",
        "language": "en"  (optional, for correct pronunciation)
    }
    """
    model = load_model()

    import base64

    text = request.get("text")
    ref_text = request.get("ref_text")
    ref_audio_base64 = request.get("ref_audio_base64")
    language = request.get("language")

    if not all([text, ref_text, ref_audio_base64]):
        raise HTTPException(status_code=400, detail="text, ref_text, and ref_audio_base64 are required")

    logger.info(f"Voice cloning (JSON): {len(text)} chars, language: {language or 'auto'}")

    try:
        # Decode base64 audio
        ref_audio_bytes = base64.b64decode(ref_audio_base64)

        # Save to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(ref_audio_bytes)
            tmp_path = tmp.name

        # Voice Cloning mode
        audio = model.generate(
            text=text,
            ref_audio=tmp_path,
            ref_text=ref_text,
            language=language,
        )

        # Cleanup
        os.unlink(tmp_path)

        audio_data = audio[0] if isinstance(audio, list) else audio
        sample_rate = 24000

        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        buffer.seek(0)

        return Response(content=buffer.read(), media_type="audio/wav")

    except Exception as e:
        logger.error(f"Voice cloning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize_advanced")
async def synthesize_advanced(request: SynthesizeAdvancedRequest):
    """
    Advanced synthesis with structured voice attributes.
    
    Build voice by specifying individual attributes:
    - gender: male or female
    - age: child, teenager, young adult, middle-aged, elderly
    - pitch: very low to very high
    - style: whisper
    - accent: English accents (only for English text)
    - custom_instruct: Override all with custom string
    """
    model = load_model()

    # Build instruct string from attributes
    if request.custom_instruct:
        instruct = request.custom_instruct
    else:
        parts = []
        if request.gender:
            parts.append(request.gender.value)
        if request.age:
            parts.append(request.age.value)
        if request.pitch:
            parts.append(request.pitch.value)
        if request.style:
            parts.append(request.style.value)
        if request.accent:
            parts.append(request.accent.value)
        
        instruct = ", ".join(parts) if parts else "female"

    logger.info(f"Advanced synthesis: {len(request.text)} chars, instruct: {instruct}")

    try:
        audio = model.generate(
            text=request.text,
            instruct=instruct,
        )

        audio_data = audio[0] if isinstance(audio, list) else audio
        sample_rate = 24000

        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV')
        buffer.seek(0)

        return Response(content=buffer.read(), media_type="audio/wav")

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)
