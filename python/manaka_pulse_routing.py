"""Route canonical heart/action signals to physical Pulse A/B channels."""
from dataclasses import replace

DEFAULT_SOURCES = {"A":"heart", "B":"action"}


def sanitize_sources(raw):
    raw = raw if isinstance(raw, dict) else {}
    return {ch:raw.get(ch) if isinstance(raw.get(ch),str) and raw.get(ch) in {"heart","action"} else source for ch,source in DEFAULT_SOURCES.items()}


def route_frame(frame, sources):
    sources = sanitize_sources(sources)
    if frame.safe_cut:
        return replace(frame,strength_a=0,strength_b=0,pattern_a="idle",pattern_b="idle")
    signals = {"heart":(frame.strength_a,frame.pattern_a), "action":(frame.strength_b,frame.pattern_b)}
    a,b = signals[sources["A"]],signals[sources["B"]]
    return replace(frame,strength_a=a[0],pattern_a=a[1],strength_b=b[0],pattern_b=b[1])


def heart_rate_bands(start, full):
    width = full-start
    return {"start":start,"lowEnd":round(start+width*.30,1),"highStart":round(start+width*.70,1),"full":full}
