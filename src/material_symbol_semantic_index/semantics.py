from __future__ import annotations

from dataclasses import dataclass
import re

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9]*|[0-9]+")


@dataclass(frozen=True)
class IconSemantics:
    tokens: list[str]
    aliases: list[str]
    domains: list[str]
    roles: list[str]
    visual_family: str
    abstraction: str
    tone: list[str]
    best_for: list[str]
    avoid_for: list[str]


STOP_TOKENS = {
    "a",
    "alt",
    "an",
    "and",
    "before",
    "can",
    "for",
    "in",
    "of",
    "on",
    "outline",
    "outlined",
    "rounded",
    "sharp",
    "so",
    "the",
    "to",
    "with",
    "new",
    "old",
    "ios",
    "android",
}

TOKEN_ALIASES: dict[str, tuple[str, ...]] = {
    "account": ("user", "profile", "identity", "person", "customer"),
    "add": ("create", "new", "increase", "include", "plus"),
    "analytics": ("insight", "analysis", "metrics", "measurement", "intelligence"),
    "api": ("integration", "interface", "service", "connection"),
    "app": ("application", "software", "product", "interface"),
    "approval": ("review", "validation", "acceptance", "governance"),
    "arrow": ("direction", "move", "flow", "navigation"),
    "article": ("document", "content", "story", "knowledge"),
    "assistant": ("ai", "help", "agent", "copilot", "support"),
    "attach": ("link", "include", "connect", "append"),
    "automate": ("automation", "workflow", "process", "orchestration"),
    "automation": ("workflow", "process", "orchestration", "autopilot"),
    "badge": ("status", "label", "credential", "marker"),
    "bar": ("chart", "metric", "signal", "progress"),
    "bolt": ("energy", "fast", "speed", "power", "instant"),
    "book": ("knowledge", "documentation", "learning", "reference"),
    "bookmark": ("save", "remember", "reference", "curate"),
    "bug": ("defect", "issue", "error", "debug"),
    "build": ("create", "construct", "develop", "compile"),
    "business": ("company", "organization", "enterprise", "work"),
    "calendar": ("schedule", "date", "planning", "time"),
    "call": ("phone", "conversation", "contact", "support"),
    "cancel": ("remove", "close", "reject", "stop"),
    "category": ("classification", "taxonomy", "grouping", "organization"),
    "chat": ("conversation", "message", "dialog", "support"),
    "check": ("done", "valid", "success", "approval", "complete"),
    "checklist": ("tasks", "requirements", "criteria", "quality"),
    "circle": ("status", "state", "marker", "indicator"),
    "cloud": ("online", "saas", "remote", "storage", "platform"),
    "code": ("developer", "software", "programming", "implementation"),
    "comment": ("feedback", "annotation", "conversation", "review"),
    "compare": ("difference", "benchmark", "evaluate", "contrast"),
    "computer": ("device", "desktop", "machine", "workstation"),
    "context": ("meaning", "knowledge", "memory", "reference"),
    "conversion": ("transform", "change", "journey", "pipeline"),
    "copy": ("duplicate", "replicate", "reuse", "clone"),
    "crisis": ("emergency", "risk", "incident", "urgent"),
    "dashboard": ("overview", "metrics", "control", "monitoring"),
    "data": ("information", "dataset", "records", "facts"),
    "database": ("data", "storage", "repository", "warehouse"),
    "delete": ("remove", "trash", "discard", "erase"),
    "description": ("document", "text", "specification", "summary"),
    "device": ("hardware", "endpoint", "screen", "terminal"),
    "diamond": ("premium", "value", "quality", "distinctive"),
    "dictionary": ("terms", "glossary", "language", "meaning"),
    "done": ("complete", "success", "validated", "accepted"),
    "download": ("receive", "import", "save", "pull"),
    "draft": ("compose", "write", "document", "early"),
    "edit": ("modify", "write", "author", "change"),
    "error": ("problem", "failure", "warning", "broken"),
    "event": ("moment", "meeting", "schedule", "milestone"),
    "explore": ("discover", "search", "investigate", "navigate"),
    "extension": ("plugin", "add-on", "integration", "module"),
    "fact": ("truth", "evidence", "knowledge", "verified"),
    "favorite": ("prefer", "important", "like", "priority"),
    "feed": ("stream", "updates", "activity", "content"),
    "file": ("document", "asset", "record", "artifact"),
    "filter": ("refine", "narrow", "segment", "select"),
    "flag": ("mark", "priority", "warning", "milestone"),
    "flow": ("process", "movement", "pipeline", "sequence"),
    "folder": ("collection", "archive", "storage", "group"),
    "forum": ("community", "discussion", "support", "conversation"),
    "functions": ("logic", "automation", "formula", "capability"),
    "govern": ("policy", "rule", "compliance", "manage", "stewardship"),
    "governed": ("policy", "rule", "compliance", "verified", "stewardship"),
    "group": ("team", "people", "collaboration", "audience"),
    "handshake": ("agreement", "partnership", "trust", "deal"),
    "help": ("support", "guidance", "question", "assistance"),
    "history": ("past", "timeline", "audit", "memory"),
    "home": ("place", "base", "origin", "workspace"),
    "hub": ("network", "center", "connection", "ecosystem"),
    "identity": ("profile", "person", "access", "authentication"),
    "image": ("visual", "picture", "media", "asset"),
    "info": ("information", "detail", "context", "notice"),
    "insights": ("analysis", "intelligence", "understanding", "findings"),
    "integration": ("connect", "combine", "join", "interoperate"),
    "inventory": ("assets", "stock", "catalog", "resources"),
    "issue": ("problem", "risk", "friction", "warning"),
    "issues": ("problem", "risk", "friction", "warning"),
    "key": ("access", "security", "credential", "unlock"),
    "label": ("tag", "classification", "metadata", "category"),
    "language": ("translation", "meaning", "localization", "text"),
    "layers": ("stack", "levels", "composition", "structure"),
    "lightbulb": ("idea", "innovation", "concept", "inspiration"),
    "link": ("connection", "relationship", "reference", "chain"),
    "list": ("items", "sequence", "tasks", "inventory"),
    "location": ("place", "map", "position", "where"),
    "lock": ("security", "privacy", "restricted", "protected"),
    "login": ("sign in", "access", "authentication", "entry"),
    "logout": ("sign out", "exit", "leave", "access"),
    "mail": ("email", "message", "communication", "inbox"),
    "manage": ("control", "operate", "administer", "govern"),
    "map": ("location", "territory", "navigation", "journey"),
    "mediation": ("resolve", "balance", "moderate", "negotiate"),
    "memory": ("storage", "recall", "compute", "context"),
    "menu": ("navigation", "options", "structure", "controls"),
    "model": ("representation", "framework", "abstraction", "machine learning"),
    "monitoring": ("watch", "observe", "track", "control"),
    "move": ("transfer", "change", "relocate", "motion"),
    "network": ("connections", "system", "graph", "infrastructure"),
    "notifications": ("alert", "signal", "update", "message"),
    "open": ("launch", "access", "expand", "available"),
    "palette": ("design", "color", "style", "brand"),
    "payments": ("money", "transaction", "commerce", "billing"),
    "pending": ("waiting", "queued", "incomplete", "review"),
    "person": ("user", "human", "individual", "customer"),
    "phone": ("mobile", "call", "device", "contact"),
    "photo": ("image", "picture", "visual", "media"),
    "policy": ("rules", "governance", "compliance", "standard"),
    "preview": ("inspect", "look", "sample", "before"),
    "privacy": ("security", "confidentiality", "protected", "data protection"),
    "process": ("workflow", "procedure", "operation", "sequence"),
    "psychology": ("mind", "intelligence", "reasoning", "ai"),
    "publish": ("release", "share", "make public", "ship"),
    "query": ("search", "question", "request", "lookup"),
    "queue": ("pipeline", "waiting", "sequence", "backlog"),
    "receipt": ("record", "transaction", "proof", "invoice"),
    "refresh": ("update", "renew", "sync", "repeat"),
    "remove": ("delete", "subtract", "exclude", "minus"),
    "report": ("summary", "analysis", "document", "status"),
    "reuse": ("copy", "repeat", "repurpose", "share", "recycle"),
    "rocket": ("launch", "growth", "speed", "ambition"),
    "route": ("journey", "path", "navigation", "flow"),
    "rule": ("policy", "logic", "condition", "governance"),
    "save": ("store", "preserve", "keep", "archive"),
    "scale": ("balance", "measure", "growth", "justice"),
    "schema": ("structure", "model", "taxonomy", "data model"),
    "school": ("education", "learning", "training", "knowledge"),
    "science": ("experiment", "research", "evidence", "lab"),
    "search": ("find", "discover", "lookup", "explore"),
    "security": ("protection", "safe", "risk", "trust"),
    "segment": ("group", "audience", "section", "partition"),
    "send": ("share", "deliver", "message", "publish"),
    "settings": ("configuration", "control", "preferences", "tuning"),
    "shield": ("protection", "security", "trust", "safety"),
    "shopping": ("commerce", "purchase", "retail", "cart"),
    "signpost": ("direction", "guidance", "navigation", "choice"),
    "smart": ("intelligent", "ai", "automated", "adaptive"),
    "sort": ("order", "rank", "organize", "sequence"),
    "source": ("origin", "reference", "truth", "input"),
    "speed": ("performance", "fast", "acceleration", "efficiency"),
    "star": ("favorite", "quality", "rating", "important"),
    "stream": ("flow", "continuous", "live", "updates"),
    "surface": ("reveal", "visibility", "discover", "show", "insight"),
    "sync": ("align", "refresh", "coordinate", "synchronize"),
    "table": ("grid", "data", "spreadsheet", "structured"),
    "tag": ("label", "metadata", "classification", "mark"),
    "task": ("todo", "work", "action", "assignment"),
    "timeline": ("history", "sequence", "roadmap", "time"),
    "token": ("credential", "unit", "symbol", "access"),
    "topic": ("subject", "theme", "category", "idea"),
    "touch": ("interaction", "input", "gesture", "contact"),
    "track": ("monitor", "follow", "measure", "observe"),
    "translate": ("language", "localization", "meaning", "conversion"),
    "trending": ("growth", "popular", "momentum", "up"),
    "trust": ("verified", "shield", "security", "confidence", "safe"),
    "trusted": ("verified", "shield", "security", "confidence", "safe"),
    "tune": ("adjust", "configure", "control", "filter"),
    "upload": ("send", "publish", "import", "push"),
    "verified": ("trusted", "approved", "validated", "certified"),
    "visibility": ("see", "observe", "transparent", "view"),
    "warning": ("risk", "caution", "alert", "problem"),
    "web": ("internet", "browser", "site", "online"),
    "work": ("job", "business", "productivity", "professional"),
    "workflow": ("process", "orchestration", "sequence", "operation"),
    "workspace": ("team space", "environment", "collaboration", "office"),
}

PHRASE_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "ai agent": ("assistant", "psychology", "smart", "automation", "reasoning"),
    "artificial intelligence": ("assistant", "psychology", "smart", "model"),
    "customer trust": ("verified", "shield", "handshake", "security"),
    "data catalog": ("database", "inventory", "category", "schema"),
    "data governance": ("policy", "rule", "verified", "database", "shield"),
    "data model": ("schema", "account_tree", "hub", "table"),
    "data quality": ("fact_check", "verified", "rule", "checklist"),
    "knowledge graph": ("hub", "schema", "account_tree", "graph"),
    "machine learning": ("model", "psychology", "memory", "smart"),
    "operational friction": ("sync_problem", "settings_suggest", "workflow", "conversion_path"),
    "single source of truth": ("source", "fact_check", "database", "verified"),
    "team collaboration": ("groups", "hub", "forum", "handshake"),
    "workflow automation": ("workflow", "automation", "settings_suggest", "conversion_path"),
}

DOMAIN_BY_TOKEN: dict[str, tuple[str, ...]] = {
    "account": ("identity", "people"),
    "analytics": ("data", "insight"),
    "api": ("technology", "integration"),
    "approval": ("governance", "quality"),
    "assistant": ("ai", "support"),
    "automation": ("process", "technology"),
    "badge": ("status", "identity"),
    "book": ("knowledge",),
    "business": ("work", "organization"),
    "calendar": ("time", "planning"),
    "category": ("taxonomy", "organization"),
    "chat": ("communication",),
    "check": ("quality", "status"),
    "checklist": ("quality", "process"),
    "cloud": ("technology", "platform"),
    "code": ("technology", "development"),
    "comment": ("communication", "feedback"),
    "computer": ("technology", "device"),
    "conversion": ("process", "transformation"),
    "crisis": ("risk",),
    "dashboard": ("data", "monitoring"),
    "data": ("data",),
    "database": ("data", "storage"),
    "description": ("content", "knowledge"),
    "device": ("technology", "device"),
    "dictionary": ("knowledge", "language"),
    "done": ("status", "quality"),
    "edit": ("content", "action"),
    "error": ("risk", "status"),
    "event": ("time", "planning"),
    "explore": ("discovery",),
    "extension": ("technology", "integration"),
    "fact": ("knowledge", "quality"),
    "feed": ("communication", "content"),
    "file": ("content", "storage"),
    "filter": ("search", "control"),
    "flow": ("process",),
    "folder": ("storage", "organization"),
    "forum": ("communication", "community"),
    "functions": ("technology", "automation"),
    "group": ("people", "collaboration"),
    "handshake": ("trust", "relationship"),
    "help": ("support",),
    "history": ("time", "audit"),
    "hub": ("network", "system"),
    "identity": ("identity", "security"),
    "image": ("visual", "media"),
    "info": ("knowledge", "status"),
    "insights": ("data", "insight"),
    "integration": ("integration", "system"),
    "inventory": ("assets", "organization"),
    "key": ("security", "access"),
    "label": ("metadata", "taxonomy"),
    "language": ("language", "content"),
    "layers": ("structure", "system"),
    "link": ("network", "relationship"),
    "list": ("organization", "process"),
    "location": ("place", "navigation"),
    "lock": ("security",),
    "mail": ("communication",),
    "manage": ("control", "operations"),
    "map": ("navigation", "place"),
    "memory": ("ai", "technology"),
    "model": ("ai", "structure"),
    "monitoring": ("monitoring", "control"),
    "network": ("network", "technology"),
    "notifications": ("communication", "status"),
    "palette": ("design",),
    "payments": ("commerce", "finance"),
    "pending": ("status", "process"),
    "person": ("people", "identity"),
    "policy": ("governance", "compliance"),
    "privacy": ("security", "compliance"),
    "process": ("process", "operations"),
    "psychology": ("ai", "reasoning"),
    "query": ("search", "knowledge"),
    "queue": ("process", "operations"),
    "report": ("data", "content"),
    "route": ("navigation", "process"),
    "rule": ("governance", "logic"),
    "save": ("storage", "action"),
    "schema": ("data", "structure"),
    "school": ("education", "knowledge"),
    "science": ("research", "evidence"),
    "search": ("search", "discovery"),
    "security": ("security", "risk"),
    "segment": ("taxonomy", "organization"),
    "settings": ("control", "configuration"),
    "shield": ("security", "trust"),
    "shopping": ("commerce",),
    "smart": ("ai", "automation"),
    "source": ("knowledge", "origin"),
    "speed": ("performance",),
    "stream": ("process", "communication"),
    "sync": ("integration", "coordination"),
    "table": ("data", "structure"),
    "tag": ("metadata", "taxonomy"),
    "task": ("work", "process"),
    "timeline": ("time", "process"),
    "token": ("security", "language"),
    "topic": ("knowledge", "taxonomy"),
    "track": ("monitoring",),
    "translate": ("language", "transformation"),
    "trending": ("growth", "performance"),
    "tune": ("control", "configuration"),
    "verified": ("trust", "quality"),
    "visibility": ("monitoring", "transparency"),
    "warning": ("risk", "status"),
    "web": ("technology", "online"),
    "work": ("work", "business"),
    "workflow": ("process", "operations"),
    "workspace": ("collaboration", "work"),
}

ROLE_BY_TOKEN: dict[str, tuple[str, ...]] = {
    "add": ("action",),
    "analytics": ("insight",),
    "approval": ("validation",),
    "arrow": ("direction",),
    "assistant": ("actor", "support"),
    "automation": ("process", "action"),
    "badge": ("state",),
    "bolt": ("outcome",),
    "bug": ("problem",),
    "calendar": ("time",),
    "cancel": ("problem", "action"),
    "category": ("object",),
    "chat": ("interaction",),
    "check": ("outcome", "validation"),
    "checklist": ("process", "validation"),
    "cloud": ("place", "object"),
    "code": ("object", "process"),
    "comment": ("interaction",),
    "compare": ("evaluation",),
    "conversion": ("process",),
    "crisis": ("problem",),
    "dashboard": ("insight",),
    "data": ("object",),
    "database": ("object",),
    "delete": ("action",),
    "done": ("outcome",),
    "edit": ("action",),
    "error": ("problem",),
    "event": ("time",),
    "explore": ("discovery",),
    "fact": ("validation", "knowledge"),
    "filter": ("action", "control"),
    "flow": ("process",),
    "group": ("actor",),
    "handshake": ("relationship", "outcome"),
    "help": ("support",),
    "history": ("time",),
    "hub": ("system",),
    "info": ("knowledge",),
    "insights": ("insight",),
    "integration": ("process",),
    "key": ("access",),
    "label": ("classification",),
    "layers": ("structure",),
    "link": ("relationship",),
    "list": ("structure",),
    "lock": ("state", "access"),
    "manage": ("control",),
    "model": ("abstraction",),
    "monitoring": ("observation",),
    "notifications": ("signal",),
    "pending": ("state",),
    "person": ("actor",),
    "policy": ("constraint",),
    "privacy": ("constraint",),
    "process": ("process",),
    "psychology": ("insight", "actor"),
    "query": ("discovery",),
    "queue": ("process",),
    "report": ("knowledge", "insight"),
    "route": ("direction", "process"),
    "rule": ("constraint",),
    "save": ("action",),
    "schema": ("structure",),
    "search": ("discovery",),
    "security": ("constraint",),
    "settings": ("control",),
    "shield": ("constraint", "protection"),
    "source": ("origin",),
    "speed": ("outcome",),
    "sync": ("coordination", "process"),
    "table": ("structure",),
    "tag": ("classification",),
    "task": ("process",),
    "timeline": ("time", "process"),
    "track": ("observation",),
    "verified": ("validation", "outcome"),
    "visibility": ("observation",),
    "warning": ("problem", "signal"),
    "workflow": ("process",),
}

GENERIC_ICONS = {
    "add",
    "arrow",
    "cancel",
    "check",
    "circle",
    "close",
    "done",
    "home",
    "info",
    "menu",
    "star",
}


def token_variants(token: str) -> list[str]:
    variants = [token]
    if len(token) > 4 and token.endswith("ies"):
        variants.append(token[:-3] + "y")
    elif len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        variants.append(token[:-2])
    elif len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "ics")):
        variants.append(token[:-1])
    if len(token) > 5 and token.endswith("ied"):
        variants.append(token[:-3] + "y")
    elif len(token) > 5 and token.endswith("ed"):
        variants.append(token[:-2])
    if len(token) > 6 and token.endswith("ing"):
        variants.append(token[:-3])
    return unique(variants)


def tokenize_text(text: str) -> list[str]:
    tokens: list[str] = []
    for match in WORD_RE.finditer(text):
        tokens.extend(token_variants(match.group(0).lower()))
    return unique(tokens)


def icon_name_tokens(name: str) -> list[str]:
    tokens = tokenize_text(name.replace("_", " "))
    return [token for token in tokens if token not in STOP_TOKENS]


def unique(items: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = item.strip().lower()
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def expand_query_terms(text: str) -> list[str]:
    normalized = " ".join(tokenize_text(text))
    expanded: list[str] = [
        token for token in tokenize_text(text) if token not in STOP_TOKENS
    ]
    for phrase, terms in PHRASE_EXPANSIONS.items():
        if phrase in normalized:
            expanded.extend(terms)
    for token in list(expanded):
        expanded.extend(TOKEN_ALIASES.get(token, ()))
    return unique(expanded)


def infer_domains(tokens: list[str]) -> list[str]:
    domains: list[str] = []
    for token in tokens:
        domains.extend(DOMAIN_BY_TOKEN.get(token, ()))
    return unique(domains)


def infer_roles(tokens: list[str]) -> list[str]:
    roles: list[str] = []
    for token in tokens:
        roles.extend(ROLE_BY_TOKEN.get(token, ()))
    return unique(roles)


def infer_visual_family(tokens: list[str], roles: list[str]) -> str:
    if any(role in roles for role in ("actor", "support")):
        return "actor"
    if any(role in roles for role in ("process", "direction", "coordination")):
        return "process"
    if any(role in roles for role in ("constraint", "problem", "signal", "state")):
        return "state"
    if any(role in roles for role in ("insight", "knowledge", "discovery", "validation")):
        return "concept"
    if any(token in tokens for token in ("database", "file", "folder", "cloud", "table", "calendar")):
        return "object"
    return "symbol"


def infer_abstraction(tokens: list[str], roles: list[str], domains: list[str]) -> str:
    if any(domain in domains for domain in ("ai", "structure", "governance", "trust")):
        return "conceptual"
    if any(role in roles for role in ("process", "constraint", "abstraction", "insight")):
        return "conceptual"
    if any(role in roles for role in ("action", "direction", "interaction")):
        return "action"
    if any(role in roles for role in ("actor", "object", "place", "time")):
        return "concrete"
    if len(tokens) >= 3:
        return "specific"
    return "generic"


def infer_tone(tokens: list[str], domains: list[str], roles: list[str]) -> list[str]:
    tone: list[str] = []
    if any(domain in domains for domain in ("technology", "data", "ai", "integration")):
        tone.append("technical")
    if any(domain in domains for domain in ("people", "collaboration", "support")):
        tone.append("human")
    if any(domain in domains for domain in ("risk", "security", "compliance")):
        tone.append("serious")
    if any(role in roles for role in ("outcome", "validation")):
        tone.append("positive")
    if any(role in roles for role in ("problem", "signal")):
        tone.append("cautionary")
    return unique(tone or ["neutral"])


def infer_best_for(tokens: list[str], domains: list[str], roles: list[str]) -> list[str]:
    best: list[str] = []
    if domains:
        best.append(" / ".join(domains[:3]))
    if roles:
        best.append(" / ".join(roles[:3]))
    if tokens:
        best.append("literal " + " ".join(tokens[:3]))
    return unique(best)


def infer_avoid_for(name: str, tokens: list[str], visual_family: str) -> list[str]:
    avoid: list[str] = []
    if name in GENERIC_ICONS or any(token in GENERIC_ICONS for token in tokens):
        avoid.append("specific domain concepts unless the text explicitly says this")
    if visual_family == "state":
        avoid.append("neutral benefits if the state may read as warning or completion")
    if visual_family == "actor":
        avoid.append("non-human systems unless a user, customer, or team is central")
    return unique(avoid)


def enrich_icon_name(name: str) -> IconSemantics:
    tokens = icon_name_tokens(name)
    aliases: list[str] = []
    for token in tokens:
        aliases.extend(TOKEN_ALIASES.get(token, ()))
    domains = infer_domains(tokens)
    roles = infer_roles(tokens)
    visual_family = infer_visual_family(tokens, roles)
    abstraction = infer_abstraction(tokens, roles, domains)
    tone = infer_tone(tokens, domains, roles)
    return IconSemantics(
        tokens=unique(tokens),
        aliases=unique(aliases),
        domains=domains,
        roles=roles,
        visual_family=visual_family,
        abstraction=abstraction,
        tone=tone,
        best_for=infer_best_for(tokens, domains, roles),
        avoid_for=infer_avoid_for(name, tokens, visual_family),
    )
