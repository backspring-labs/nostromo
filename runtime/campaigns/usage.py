"""Normalize observed one-call usage for the existing monthly estimate command."""
from .core import Refused


def observed(record):
    model, u = record["model"], record["usage"]
    if model == "gpt-5.6-sol":
        result = {"model": model, "input": u.get("input_tokens", 0),
                  "cached": (u.get("input_tokens_details") or {}).get("cached_tokens", 0),
                  "write5": (u.get("input_tokens_details") or {}).get("cache_write_tokens", 0), "write1h": 0,
                  "output": u.get("output_tokens", 0),
                  "reasoning": (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)}
    elif model == "claude-opus-5-5":
        write = u.get("cache_creation_input_tokens", 0)
        long_write = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
        cached = u.get("cache_read_input_tokens", 0)
        result = {"model": model, "input": u.get("input_tokens", 0) + cached + write, "cached": cached,
                  "write5": write - long_write, "write1h": long_write, "output": u.get("output_tokens", 0),
                  "reasoning": (u.get("output_tokens_details") or {}).get("thinking_tokens", 0),
                  "geo": u.get("inference_geo"), "speed": u.get("speed")}
    else:
        raise Refused("unknown bounded-review usage model")
    for name in ("input", "cached", "write5", "write1h", "output", "reasoning"):
        if type(result[name]) is not int or result[name] < 0:
            raise Refused("invalid observed token count")
    return result
