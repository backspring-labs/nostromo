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
        taken = (store.db.execute("SELECT 1 FROM definitions WHERE name=?", (name,)).fetchone() or
                 store.db.execute("SELECT 1 FROM review_budgets WHERE name=?", (name,)).fetchone())
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
        if not isinstance(goal[field], str) or not goal[field].strip():
            raise Refused(f"the goal needs a {field}")
    items = goal.get("items") or []
    if not isinstance(items, list) or not all(isinstance(i, str) and i.strip() for i in items):
        raise Refused("the goal's items are a list of backlog items, in order")
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
    lines = [f"**{registered.get('display_name', registered['project_id'])} campaign {number}: {title.rstrip('.')}**",
             "",
             objective["statement"] + ".",
             "",
             f"- **Increments:** up to {increments}.",
             f"- **Accepted when:** {objective['measurement'].rstrip('.')}.",
             f"- **Time:** runs for up to {hours:g} hours once started. Approve it by {et(cutoff - hours * 3600)}.",
             f"- **Reviews:** Ripley rules each gate and Dallas checks each ruling; at most "
             f"{allowance['max_dispatches']} reviews, from a ${allowance['cap_microusd'] / 1e6:.2f} allowance.",
             f"- **Scope:** {', '.join(objective['allowed_scope'])}."]
    if left_out:
        lines.append(f"- **Left for a later campaign:** {'; '.join(left_out)}.")
    lines += ["", "Reply **approve** to launch, or tell me what to change."]
    return "\n".join(lines)
