"""Draft a campaign from a plain-language goal (docs/specs/plain-language-campaigns.md, phase 1).

Deterministic, no model, stores nothing. Ripley supplies the goal: a title, a statement, the backlog
items in order, and optionally how success is measured. The product's registry entry
(campaigns/projects/<project>.yaml) supplies everything else. A size preset sets the increments, the
hours and the review allowance. The result is validated exactly as an approval would validate it,
then returned with the readable card the owner will see.
"""
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .core import Refused, exact, identifier

ROOT = Path(__file__).resolve().parents[2]
ET = ZoneInfo("America/New_York")
# Increments and hours. Each fits the $25 / 60-call allowance ceiling at the largest reservation.
PRESETS = {"small": (3, 3), "medium": (6, 6), "large": (8, 8)}
# Two reviewers at each of two gates, plus one revision; one more for the closing analysis.
REVIEWS_PER_INCREMENT = 5
# How long the owner has to approve a card before its cutoff starts to bite.
APPROVAL_WINDOW_S = 24 * 3600
DEFAULT_MEASUREMENT = ("its own tests pass on the product's runner, and everything accepted before it "
                       "still passes")


# What the card shows must be what the owner approves (review B2, 2026-11-01): the goal's fields
# are single lines of visible text, bounded, and the card escapes Markdown so none can hide or forge
# a line.
LIMITS = {"title": 80, "statement": 600, "item": 120, "measurement": 300}
# Inline markers only: no goal text starts a card line, so block markers (#, -, 1.) can't take effect.
MARKDOWN = re.compile(r"([\\`*_\[\]<>~|])")


def plain(value, what, limit):
    import unicodedata
    if not isinstance(value, str) or not value.strip():
        raise Refused(f"{what} is required text")
    if len(value) > limit:
        raise Refused(f"{what} is at most {limit} characters")
    # Combining marks could strike through or hide words; precomposed accents (NFC) are fine.
    if unicodedata.normalize("NFC", value) != value or any(
            unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp", "Mn", "Me"} for ch in value):
        raise Refused(f"{what} must be one line of plain visible text")


def shown(text):
    """Text as the owner reads it on the card: Markdown escaped, so it renders as written."""
    return MARKDOWN.sub(r"\\\1", text)


def entry(project):
    """A product's registry entry, by its short name ('shelfnote')."""
    if not isinstance(project, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", project):
        raise Refused("name the product by its registry name, for example shelfnote")
    path = ROOT / "campaigns" / "projects" / (project + ".yaml")
    if not path.is_file():
        raise Refused(f"{project} is not in the project registry yet; add campaigns/projects/{project}.yaml")
    import yaml  # the registry is written for people; only the draft step reads it
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict) or not value.get("project_id") or not value.get("allowed_scope"):
        raise Refused(f"{project}'s registry entry needs at least project_id and allowed_scope")
    return value


def campaigns_channel():
    import yaml
    for channel in yaml.safe_load((ROOT / "crew" / "channels.yaml").read_text())["channels"]:
        if channel["name"] == "squadops-campaigns":
            return channel["id"]
    raise Refused("crew/channels.yaml has no #squadops-campaigns")


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def et(epoch):
    return datetime.fromtimestamp(epoch, ET).strftime("%-I:%M %p ET, %a %b %-d").replace("AM", "am").replace("PM", "pm")


def free_name(store, project, now):
    """crew-<project>-<date>-<n>: the first n no definition or allowance has used."""
    day = datetime.fromtimestamp(now, ET).strftime("%Y%m%d")
    for number in range(1, 100):
        name = f"crew-{project}-{day}-{number}"
        taken = any(store.db.execute(f"SELECT 1 FROM {table} WHERE {column}=?", (name,)).fetchone()
                    for table, column in (("definitions", "name"), ("review_budgets", "name"), ("proposals", "id")))
        if not taken:
            return name
    raise Refused("no free campaign name today")


def campaign_number(store, project_id):
    """This product's next campaign number, counting the campaigns already created for it."""
    import json
    count = 0
    for (body,) in store.db.execute("SELECT d.body FROM campaigns c JOIN definitions d ON d.name=c.definition"):
        if json.loads(body)["definition"].get("project_id") == project_id:
            count += 1
    return count + 1


def draft(broker, args, now=None):
    from .review import reservation_microusd
    now = time.time() if now is None else now
    exact(args, {"project", "goal", "thread"}, {"size", "hours"})
    identifier(args["thread"])
    registered = entry(args["project"])
    goal = args["goal"]
    exact(goal, {"title", "statement"}, {"items", "measurement"})
    for field in ("title", "statement"):
        plain(goal[field], f"the goal's {field}", LIMITS[field])
    items = goal.get("items") or []
    if not isinstance(items, list) or len(items) > 20:
        raise Refused("the goal's items are a list of at most 20 backlog items, in order")
    for item in items:
        plain(item, "each backlog item", LIMITS["item"])
    if goal.get("measurement") is not None:
        plain(goal["measurement"], "the goal's measurement", LIMITS["measurement"])
    size = args.get("size", "medium")
    if size not in PRESETS:
        raise Refused("size is small, medium or large")
    preset_increments, preset_hours = PRESETS[size]
    # The size follows the goal: three items need three increments, whatever was asked.
    increments = min(len(items), preset_increments) if items else preset_increments
    hours = args.get("hours", preset_hours)
    if type(hours) not in (int, float) or not 1 <= hours <= PRESETS["large"][1]:
        raise Refused(f"hours is between 1 and {PRESETS['large'][1]}")
    reviews = REVIEWS_PER_INCREMENT * increments + 1
    cap = math.ceil(reviews * reservation_microusd(now))
    not_after = now + APPROVAL_WINDOW_S + hours * 3600
    name = free_name(broker.store, args["project"], now)
    allowance = {"name": name, "cap_microusd": cap, "max_dispatches": reviews, "expires_at": iso(not_after + 3600)}
    statement = goal["statement"].strip().rstrip(".")
    if items:
        statement += ". In order: " + "; ".join(i.strip() for i in items[:increments])
    definition = {
        "project_id": registered["project_id"],
        "objective": {"allowed_scope": list(registered["allowed_scope"]), "statement": statement,
                      "measurement": (goal.get("measurement") or DEFAULT_MEASUREMENT).strip(),
                      "target_accepted_increments": increments,
                      **({"requirements": registered["requirements"]} if registered.get("requirements") else {}),
                      **({"work_class": registered["work_class"]} if registered.get("work_class") else {})},
        "policy": {**(registered.get("policy") or {}), "max_cycles": 2 * increments + 2,
                   "max_elapsed_s": int(hours * 3600), "budget_tokens": 2000000 * increments},
        "crew": {**(registered.get("crew") or {}), "paid_dispatches": reviews,
                 "automation": {"budget": name, "not_after": iso(not_after)}},
    }
    approval = {"name": name, "definition": definition, "channel": campaigns_channel(), "thread": args["thread"]}
    from .automation import Automation
    Automation(broker, now=now).validate_allowance(allowance)
    broker.check_definition(approval, allowance=allowance)
    card = render_card(registered, approval, allowance, campaign_number(broker.store, registered["project_id"]),
                       goal["title"].strip(), hours, items[increments:])
    return {"card": card, "approval": approval, "allowance": allowance}


def render_card(registered, approval, allowance, number, title, hours, left_out):
    """The proposal the owner reads and approves. A pure function of what it describes, so that
    approval-by-reply can re-render it and check the signed card says exactly this."""
    objective = approval["definition"]["objective"]
    cutoff = datetime.strptime(approval["definition"]["crew"]["automation"]["not_after"],
                               "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    increments = objective["target_accepted_increments"]
    # The terms first, before any text the crew wrote, and that text escaped.
    lines = [f"**{registered.get('display_name', registered['project_id'])} campaign {number}: {shown(title.rstrip('.'))}**",
             "",
             f"- **Reviews:** at most {allowance['max_dispatches']} reviews, from a "
             f"${allowance['cap_microusd'] / 1e6:.2f} allowance. Ripley rules each gate and Dallas checks each ruling.",
             f"- **Scope:** {shown(', '.join(objective['allowed_scope']))}.",
             f"- **Time:** runs for up to {hours:g} hours once started. Approve it by {et(cutoff - hours * 3600)}.",
             f"- **Increments:** up to {increments}.",
             f"- **Accepted when:** {shown(objective['measurement'].rstrip('.'))}.",
             "",
             f"**Goal:** {shown(objective['statement'])}."]
    if left_out:
        lines.append(f"- **Left for a later campaign:** {shown('; '.join(left_out))}.")
    lines += ["", "Reply **approve** to this card to launch, or tell me what to change."]
    return "\n".join(lines)
