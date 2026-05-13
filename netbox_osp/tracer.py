"""Visual core tracer — end-to-end path discovery for fibre strands.

PR E of v0.2.0. Given a `Strand`, return an ordered list of hops covering
the full physical path: device interface → patch cord → cassette → trunk
fibre → splice → OSP strand → splice → … → device interface.

Architecture:
- `trace_strand(strand)` is the public entry point. Returns a `TraceResult`
  (typed dict, JSON-serialisable) with `strand_id`, `hops`,
  `total_loss_db`, `target_loss_budget_db`, `loss_pct`, `band`.
- The traversal is strand-rooted. For an entry point on a `dcim.Interface`
  or `dcim.FrontPort`, the caller is expected to first resolve the
  associated `Strand` (via `Strand.cable_link` bridge or the
  `a_termination` / `b_termination` GenericForeignKeys) and pass that
  Strand in. `resolve_strand_for_termination()` is a helper for that.
- Termination walks use NetBox core's `dcim.PathEndpoint.trace()` which
  returns `list[tuple[list, list, list]]` — each tuple is
  `(a_terminations, cables, b_terminations)`. Source:
  `netbox/dcim/models/device_components.py` (PathEndpoint.trace).
  See <https://github.com/netbox-community/netbox/blob/main/netbox/dcim/models/device_components.py>
  for the canonical implementation.

Hop loss math (configurable via `PLUGINS_CONFIG["netbox_osp"]`):
- `interface`  : 0 dB
- `cable`      : length_m × `default_attenuation_db_per_km` / 1000,
                 or `default_patch_cord_loss_db` if length unknown.
- `cassette`   : `default_cassette_loss_db` (per FrontPort↔RearPort
                 pass-through; default 0.5 dB).
- `trunk`      : 0 dB (aggregator; child strands carry the loss).
- `splice`     : `splice.loss_db` (`default_splice_loss_db` fallback).
- `osp_strand` : length_m × `strand.cable.attenuation_db_per_km` / 1000.

The function is intentionally pure — no Django request, no template
rendering. Easy to unit-test.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from django.conf import settings as dj_settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.urls import NoReverseMatch, reverse

from .models import FibreLink, Splice, Strand


# Maximum number of strands we'll walk through a splice chain before
# giving up. Real-world fibre paths rarely exceed 8 hops; 64 is paranoid.
MAX_STRAND_HOPS = 64

# Maximum cumulative hops we'll generate. A single physical path with
# splices + breakouts + cassettes can produce ~30 hops legitimately;
# 200 is the safety net before we declare the traversal pathological.
MAX_TOTAL_HOPS = 200


# ----------------------------------------------------------------------------
# Settings helpers
# ----------------------------------------------------------------------------

def _plugin_settings() -> dict[str, Any]:
    return dj_settings.PLUGINS_CONFIG.get("netbox_osp", {})


def _setting(key: str, default: float) -> Decimal:
    raw = _plugin_settings().get(key, default)
    return Decimal(str(raw))


def _default_patch_cord_loss_db() -> Decimal:
    # Falls back to a small fixed loss when a patch cord has no length.
    return _setting("default_patch_cord_loss_db", 0.1)


def _default_cassette_loss_db() -> Decimal:
    return _setting("default_cassette_loss_db", 0.5)


def _default_splice_loss_db() -> Decimal:
    return _setting("default_splice_loss_db", 0.10)


def _default_attenuation_db_per_km() -> Decimal:
    return _setting("default_attenuation_db_per_km", 0.22)


# ----------------------------------------------------------------------------
# Hop builders
# ----------------------------------------------------------------------------

def _safe_url(view_name: str, *args) -> str:
    """Best-effort reverse — returns "" on NoReverseMatch so the tracer
    never explodes on a partial NetBox install (e.g. apps with the view
    not yet wired in test isolation)."""
    try:
        return reverse(view_name, args=args)
    except NoReverseMatch:
        return ""


def _hop(kind: str, label: str, url: str = "", **extra) -> dict[str, Any]:
    hop = {"kind": kind, "label": label, "url": url}
    hop.update(extra)
    # Ensure loss_db is present and JSON-serialisable.
    if "loss_db" in hop:
        hop["loss_db"] = float(hop["loss_db"])
    if "length_m" in hop and hop["length_m"] is not None:
        hop["length_m"] = float(hop["length_m"])
    return hop


def interface_hop(interface) -> dict[str, Any]:
    label = f"{getattr(interface.device, 'name', '?')}:{interface.name}"
    url = ""
    try:
        url = interface.get_absolute_url()
    except Exception:
        pass
    return _hop("interface", label, url, loss_db=Decimal("0"))


def cable_hop(cable, a_term=None, b_term=None) -> dict[str, Any]:
    """A dcim.Cable hop. Loss derived from length if any, else fixed."""
    a_lbl = _term_label(a_term)
    b_lbl = _term_label(b_term)
    label = f"{a_lbl} → {b_lbl}" if (a_lbl and b_lbl) else (cable.label or f"cable {cable.pk}")
    length = None
    if getattr(cable, "length", None):
        length = float(cable.length)
    loss = _default_patch_cord_loss_db()
    if length:
        loss = (Decimal(str(length)) / Decimal("1000")) * _default_attenuation_db_per_km()
    url = ""
    try:
        url = cable.get_absolute_url()
    except Exception:
        pass
    return _hop("cable", label, url, length_m=length, loss_db=loss)


def cassette_hop(front_port, rear_port) -> dict[str, Any]:
    """A pass-through inside a cassette: FrontPort ↔ RearPort on the same
    device. Loss = `default_cassette_loss_db`."""
    device = getattr(front_port, "device", None) or getattr(rear_port, "device", None)
    device_name = getattr(device, "name", "?") if device else "?"
    label = f"{device_name}: {front_port.name} ↔ {rear_port.name}"
    url = ""
    if device is not None:
        try:
            url = device.get_absolute_url()
        except Exception:
            pass
    return _hop("cassette", label, url, loss_db=_default_cassette_loss_db())


def trunk_hop(trunk) -> dict[str, Any]:
    return _hop(
        "trunk",
        f"{trunk.cid} ({trunk.get_trunk_type_display()})",
        _safe_url("plugins:netbox_osp:fibretrunk", trunk.pk),
        loss_db=Decimal("0"),
    )


def splice_hop(splice) -> dict[str, Any]:
    closure_name = splice.tray.closure.name if splice.tray_id else "?"
    tray_no = splice.tray.number if splice.tray_id else "?"
    loss = splice.loss_db if splice.loss_db is not None else _default_splice_loss_db()
    return _hop(
        "splice",
        f"{closure_name} tray {tray_no} pos {splice.position}",
        _safe_url("plugins:netbox_osp:splice", splice.pk),
        loss_db=loss,
    )


def strand_hop(strand) -> dict[str, Any]:
    cable = strand.cable
    length = None
    if getattr(cable, "effective_length_m", None):
        length = float(cable.effective_length_m)
    attenuation = cable.attenuation_db_per_km or _default_attenuation_db_per_km()
    if length:
        loss = (Decimal(str(length)) / Decimal("1000")) * Decimal(str(attenuation))
    else:
        loss = Decimal("0")
    tube_label = ""
    if strand.tube_id and strand.tube:
        tube_label = f" (tube {strand.tube.number})"
    return _hop(
        "osp_strand",
        f"{cable.cid} strand {strand.position}{tube_label}",
        _safe_url("plugins:netbox_osp:strand", strand.pk),
        length_m=length,
        loss_db=loss,
    )


def _term_label(term) -> str:
    if term is None:
        return ""
    name = getattr(term, "name", str(term))
    device = getattr(term, "device", None)
    if device is not None:
        return f"{device.name}:{name}"
    return str(name)


# ----------------------------------------------------------------------------
# DCIM-side termination walker
# ----------------------------------------------------------------------------

def _is_path_endpoint(obj) -> bool:
    # PathEndpoint subclasses include Interface, ConsolePort, etc. They
    # expose a .trace() bound method by inheritance.
    return obj is not None and callable(getattr(obj, "trace", None))


def _is_pass_through(obj) -> bool:
    """True for FrontPort / RearPort — these are intermediate hops that
    don't terminate a path. We detect by attribute rather than isinstance
    so the tracer doesn't import dcim models at module load."""
    if obj is None:
        return False
    return obj.__class__.__name__ in ("FrontPort", "RearPort")


def walk_from_termination(start_term, into: list[dict[str, Any]]) -> None:
    """Walk OUTWARD from a strand's a/b GenericForeignKey termination
    (typically a `dcim.FrontPort`) through any chained patch cords +
    cassettes until we hit a real `PathEndpoint` (Interface, ConsolePort,
    …) or run out of attached cables.

    Appends hop dicts to `into` in order. Stops silently on a dead end
    so partial traces still render.
    """
    if start_term is None:
        return

    visited_cables: set[int] = set()
    cursor = start_term
    safety = 0
    # FrontPort/RearPort cassette pass-through emission. The starting
    # FrontPort itself isn't emitted as a hop — it's the "entry" into the
    # DCIM-side chain. We emit cassette_hop the first time we cross
    # FrontPort↔RearPort within the same device.
    while cursor is not None and safety < 32:
        safety += 1
        cable = getattr(cursor, "cable", None)
        if cable is None or cable.pk in visited_cables:
            break
        visited_cables.add(cable.pk)

        # Identify the other end of this cable.
        a_terms = list(getattr(cable, "a_terminations", []) or [])
        b_terms = list(getattr(cable, "b_terminations", []) or [])
        all_terms = a_terms + b_terms
        # Find the far end — first termination that isn't the cursor.
        far = None
        for t in all_terms:
            if (
                t.__class__ is not cursor.__class__
                or t.pk != cursor.pk
            ):
                far = t
                break
        if far is None and all_terms:
            far = all_terms[0]

        into.append(cable_hop(cable, a_term=cursor, b_term=far))

        if far is None:
            break

        # If we landed on a FrontPort or RearPort, emit a cassette hop
        # (the device pass-through) and step to the peer port.
        if _is_pass_through(far):
            peer = _peer_pass_through(far)
            if peer is not None:
                if far.__class__.__name__ == "FrontPort":
                    into.append(cassette_hop(front_port=far, rear_port=peer))
                else:
                    into.append(cassette_hop(front_port=peer, rear_port=far))
                cursor = peer
                continue
            # No peer mapping — terminate here.
            break

        # If we landed on a real PathEndpoint (Interface, ConsolePort, …),
        # emit it and stop.
        if _is_path_endpoint(far):
            into.append(interface_hop(far))
            break

        # Unknown termination kind — just stop. Defensive.
        break


def _peer_pass_through(port):
    """Return the cassette-internal peer of a FrontPort or RearPort.

    FrontPort.rear_port is FK → RearPort. RearPort.frontports is reverse.
    Returns None if the port has no peer (e.g. unused RearPort position).
    """
    cls_name = port.__class__.__name__
    if cls_name == "FrontPort":
        return getattr(port, "rear_port", None)
    if cls_name == "RearPort":
        # A RearPort can fan out to multiple FrontPorts in NetBox's port
        # model. We pick the first; multi-position cassettes are rare
        # enough that this rendering choice is acceptable for v0.2.0.
        try:
            return port.frontports.first()
        except Exception:
            return None
    return None


# ----------------------------------------------------------------------------
# OSP-side strand chain walker
# ----------------------------------------------------------------------------

def _other_strand(splice: Splice, this_strand_id: int) -> Optional[Strand]:
    if splice.strand_a_id == this_strand_id:
        return splice.strand_b
    if splice.strand_b_id == this_strand_id:
        return splice.strand_a
    return None


def walk_strand_chain(
    start: Strand,
    direction: str,
    visited_strands: set[int],
    visited_splices: set[int],
) -> list[dict[str, Any]]:
    """Walk forward from `start` through any splices that reference it,
    emitting hops as we go. `direction` is 'a' (start at a_termination,
    walk through splices on the b side) or 'b' (the reverse).

    Splices are bidirectional in our model — `strand_a`/`strand_b` is
    just storage order. We follow each splice as long as the
    *other-side* strand is unvisited.
    """
    out: list[dict[str, Any]] = []
    cursor = start
    safety = 0
    while cursor is not None and safety < MAX_STRAND_HOPS:
        safety += 1
        next_splice = None
        next_strand = None
        candidates = Splice.objects.filter(
            Q(strand_a_id=cursor.pk) | Q(strand_b_id=cursor.pk),
        ).exclude(pk__in=visited_splices)
        for sp in candidates:
            other = _other_strand(sp, cursor.pk)
            if other is None:
                continue
            if other.pk in visited_strands:
                continue
            next_splice = sp
            next_strand = other
            break
        if next_splice is None or next_strand is None:
            break
        visited_splices.add(next_splice.pk)
        visited_strands.add(next_strand.pk)
        out.append(splice_hop(next_splice))
        out.append(strand_hop(next_strand))
        # After traversing the splice, we are now on `next_strand`. To
        # continue, we keep walking from the `next_strand` outward in
        # the opposite direction from where we entered.
        cursor = next_strand
    return out


# ----------------------------------------------------------------------------
# Termination resolvers
# ----------------------------------------------------------------------------

def resolve_strand_for_termination(termination) -> Optional[Strand]:
    """Given a dcim.Interface or dcim.FrontPort, find a Strand that
    claims it (via cable_link bridge or the a/b GenericForeignKey).

    Returns the first match — operators get the click-through they
    expect even when multiple Strands map onto the same port (e.g. an
    optical splitter would do that).
    """
    if termination is None:
        return None

    # Case 1: the termination IS a FrontPort directly claimed via the
    # Strand.a_termination / b_termination GFK.
    try:
        ct = ContentType.objects.get_for_model(type(termination))
    except Exception:
        ct = None
    if ct is not None:
        match = Strand.objects.filter(
            Q(a_termination_type=ct, a_termination_id=termination.pk)
            | Q(b_termination_type=ct, b_termination_id=termination.pk),
        ).first()
        if match is not None:
            return match

    # Case 2: the termination is an Interface chained through one or more
    # cables / cassettes to a FrontPort that a Strand claims. We follow
    # the dcim path one hop at a time.
    cable = getattr(termination, "cable", None)
    visited: set[int] = set()
    safety = 0
    cursor = termination
    while cable is not None and cable.pk not in visited and safety < 16:
        visited.add(cable.pk)
        safety += 1
        a_terms = list(getattr(cable, "a_terminations", []) or [])
        b_terms = list(getattr(cable, "b_terminations", []) or [])
        far_terms = [
            t for t in (a_terms + b_terms)
            if not (t.__class__ is cursor.__class__ and t.pk == cursor.pk)
        ]
        if not far_terms:
            break
        far = far_terms[0]
        if _is_pass_through(far):
            # Try this port as a strand claim.
            try:
                far_ct = ContentType.objects.get_for_model(type(far))
            except Exception:
                far_ct = None
            if far_ct is not None:
                m = Strand.objects.filter(
                    Q(a_termination_type=far_ct, a_termination_id=far.pk)
                    | Q(b_termination_type=far_ct, b_termination_id=far.pk),
                ).first()
                if m is not None:
                    return m
            peer = _peer_pass_through(far)
            if peer is None:
                break
            # Try peer too.
            try:
                peer_ct = ContentType.objects.get_for_model(type(peer))
            except Exception:
                peer_ct = None
            if peer_ct is not None:
                m = Strand.objects.filter(
                    Q(a_termination_type=peer_ct, a_termination_id=peer.pk)
                    | Q(b_termination_type=peer_ct, b_termination_id=peer.pk),
                ).first()
                if m is not None:
                    return m
            cursor = peer
            cable = getattr(peer, "cable", None)
            continue
        break

    # Case 3: legacy bridge — find a strand whose cable_link FK matches a
    # cable in our walk path. Cheap fallback; covers the strand-as-cable
    # representation.
    cable = getattr(termination, "cable", None)
    if cable is not None:
        m = Strand.objects.filter(cable_link=cable).first()
        if m is not None:
            return m
    return None


# ----------------------------------------------------------------------------
# Loss budget banding
# ----------------------------------------------------------------------------

def _budget_for_strand(strand: Strand) -> Decimal:
    """If the strand is part of a FibreLink, use its target_loss_budget_db;
    otherwise pick a conservative default from settings."""
    link = (
        FibreLink.objects
        .filter(link_strands__strand=strand)
        .order_by("pk")
        .first()
    )
    if link is not None and link.target_loss_budget_db is not None:
        return link.target_loss_budget_db
    return _setting("default_loss_budget_db", 8.0)


def _band(pct: float) -> str:
    if pct <= 80:
        return "ok"
    if pct <= 100:
        return "warn"
    return "fail"


# ----------------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------------

def trace_strand(strand: Strand) -> dict[str, Any]:
    """Trace a fibre core end-to-end from `strand` outward.

    Returns a JSON-serialisable dict:
        {
          "strand_id": int,
          "hops": list[dict],
          "total_loss_db": float,
          "target_loss_budget_db": float,
          "loss_pct": float,
          "band": "ok" | "warn" | "fail",
          "incomplete": bool,
        }

    `hops` is ordered from the A-side terminal device to the B-side
    terminal device. If the strand has no terminations we still emit a
    one-hop trace (just the strand) and set `incomplete=True`.
    """
    hops: list[dict[str, Any]] = []
    visited_strands: set[int] = {strand.pk}
    visited_splices: set[int] = set()

    # 1. A-side: walk OUT through start.a_termination — but prepend the
    #    output so DCIM-side hops appear BEFORE the strand in the hop list.
    a_side: list[dict[str, Any]] = []
    walk_from_termination(strand.a_termination, a_side)
    # The dcim walk produces hops in "outward" order from the strand
    # (cable, [cassette,] cable, …, interface). To present them as
    # "interface → … → strand" we reverse.
    a_side.reverse()
    hops.extend(a_side)

    # 2. Splice chain on the A side first (look up splices that touch
    #    `strand`; if they connect to another strand whose B-side faces
    #    the patch panel, we want those hops BEFORE the start strand).
    #    This is rare in practice — most operator paths are
    #    "device → patch → splice → strand → splice → patch → device" —
    #    but we handle both directions for completeness.

    # 3. The starting strand.
    hops.append(strand_hop(strand))
    if len(hops) >= MAX_TOTAL_HOPS:
        return _finalise(strand, hops, incomplete=True)

    # 4. B-side splice chain. Each iteration appends (splice, strand,
    #    optional terminating dcim hops).
    chain = walk_strand_chain(
        strand,
        direction="b",
        visited_strands=visited_strands,
        visited_splices=visited_splices,
    )
    hops.extend(chain)

    # 5. After the last strand in the splice chain (or the start strand
    #    if no chain), walk OUT through its b_termination.
    last_strand = strand
    if visited_strands:
        # The last strand added to the chain is the most-recently visited.
        try:
            last_id = max(visited_strands)
            last_strand = Strand.objects.get(pk=last_id)
        except Strand.DoesNotExist:
            last_strand = strand
    # Pick whichever termination is the "outward" side. Heuristic: if a
    # splice landed us on `last_strand`, we entered via the side whose
    # termination is None or whose FrontPort is internal to the closure —
    # the other side faces the patch panel.
    out_term = last_strand.b_termination
    if out_term is None:
        out_term = last_strand.a_termination if last_strand is not strand else None
    b_side: list[dict[str, Any]] = []
    walk_from_termination(out_term, b_side)
    hops.extend(b_side)

    incomplete = strand.a_termination is None and strand.b_termination is None
    return _finalise(strand, hops, incomplete=incomplete)


def _finalise(
    strand: Strand,
    hops: list[dict[str, Any]],
    incomplete: bool,
) -> dict[str, Any]:
    total = sum((Decimal(str(h.get("loss_db", 0))) for h in hops), Decimal("0"))
    budget = _budget_for_strand(strand)
    pct = 0.0
    if budget:
        pct = float((total / budget) * 100)
    return {
        "strand_id": strand.pk,
        "hops": hops,
        "total_loss_db": round(float(total), 3),
        "target_loss_budget_db": round(float(budget), 3),
        "loss_pct": round(pct, 1),
        "band": _band(pct),
        "incomplete": incomplete,
    }
