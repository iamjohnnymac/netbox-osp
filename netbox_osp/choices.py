from utilities.choices import ChoiceSet


class OspCableTypeChoices(ChoiceSet):
    key = "OspCable.type"

    TYPE_LOOSE_TUBE = "loose-tube-armoured"
    TYPE_TIGHT_BUFFERED = "tight-buffered"
    TYPE_RIBBON = "ribbon"
    TYPE_SLOTTED_CORE = "slotted-core"
    TYPE_DROP = "drop"
    TYPE_BREAKOUT = "breakout"
    TYPE_ADSS = "adss"
    TYPE_OPGW = "opgw"

    CHOICES = [
        (TYPE_LOOSE_TUBE, "Loose-tube (armoured)", "blue"),
        (TYPE_TIGHT_BUFFERED, "Tight-buffered", "cyan"),
        (TYPE_RIBBON, "Ribbon", "purple"),
        (TYPE_SLOTTED_CORE, "Slotted-core", "indigo"),
        (TYPE_DROP, "Drop", "green"),
        (TYPE_BREAKOUT, "Breakout", "teal"),
        (TYPE_ADSS, "ADSS (aerial)", "orange"),
        (TYPE_OPGW, "OPGW (aerial)", "yellow"),
    ]


class OspStatusChoices(ChoiceSet):
    key = "OspCable.status"

    STATUS_PLANNED = "planned"
    STATUS_ORDERED = "ordered"
    STATUS_INSTALLED = "installed"
    STATUS_ACTIVE = "active"
    STATUS_DECOMMISSIONING = "decommissioning"
    STATUS_RETIRED = "retired"
    STATUS_FAULTY = "faulty"

    CHOICES = [
        (STATUS_PLANNED, "Planned", "cyan"),
        (STATUS_ORDERED, "Ordered", "blue"),
        (STATUS_INSTALLED, "Installed", "purple"),
        (STATUS_ACTIVE, "Active", "green"),
        (STATUS_DECOMMISSIONING, "Decommissioning", "yellow"),
        (STATUS_RETIRED, "Retired", "gray"),
        (STATUS_FAULTY, "Faulty", "red"),
    ]


class InstallMethodChoices(ChoiceSet):
    key = "OspCable.install_method"

    METHOD_DIRECT_BURIED = "direct-buried"
    METHOD_DUCT = "duct"
    METHOD_AERIAL = "aerial"
    METHOD_TROUGH = "trough"
    METHOD_SUBMARINE = "submarine"
    METHOD_INDOOR = "indoor"

    CHOICES = [
        (METHOD_DIRECT_BURIED, "Direct buried", "brown"),
        (METHOD_DUCT, "Duct", "gray"),
        (METHOD_AERIAL, "Aerial", "cyan"),
        (METHOD_TROUGH, "Trough/tray", "yellow"),
        (METHOD_SUBMARINE, "Submarine", "blue"),
        (METHOD_INDOOR, "Indoor riser", "purple"),
    ]


class TIA598ColorChoices(ChoiceSet):
    """TIA-598-C standard fibre colour code, positions 1..12."""

    key = "OspFibre.color"

    BLUE = "blue"
    ORANGE = "orange"
    GREEN = "green"
    BROWN = "brown"
    SLATE = "slate"
    WHITE = "white"
    RED = "red"
    BLACK = "black"
    YELLOW = "yellow"
    VIOLET = "violet"
    ROSE = "rose"
    AQUA = "aqua"

    CHOICES = [
        (BLUE, "Blue", "blue"),
        (ORANGE, "Orange", "orange"),
        (GREEN, "Green", "green"),
        (BROWN, "Brown", "brown"),
        (SLATE, "Slate", "gray"),
        (WHITE, "White", "white"),
        (RED, "Red", "red"),
        (BLACK, "Black", "black"),
        (YELLOW, "Yellow", "yellow"),
        (VIOLET, "Violet", "purple"),
        (ROSE, "Rose", "pink"),
        (AQUA, "Aqua", "cyan"),
    ]

    @classmethod
    def for_position(cls, position):
        """Return TIA-598 colour for a 1-indexed position. Wraps every 12."""
        order = [
            cls.BLUE, cls.ORANGE, cls.GREEN, cls.BROWN, cls.SLATE, cls.WHITE,
            cls.RED, cls.BLACK, cls.YELLOW, cls.VIOLET, cls.ROSE, cls.AQUA,
        ]
        return order[(position - 1) % 12]


class StrandStatusChoices(ChoiceSet):
    key = "Strand.status"

    STATUS_SPARE = "spare"
    STATUS_IN_USE = "in-use"
    STATUS_RESERVED = "reserved"
    STATUS_BROKEN = "broken"
    STATUS_DARK = "dark"

    CHOICES = [
        (STATUS_SPARE, "Spare", "green"),
        (STATUS_IN_USE, "In use", "blue"),
        (STATUS_RESERVED, "Reserved", "yellow"),
        (STATUS_BROKEN, "Broken", "red"),
        (STATUS_DARK, "Dark (unused)", "gray"),
    ]


class ClosureTypeChoices(ChoiceSet):
    key = "SpliceClosure.closure_type"

    DOME = "dome"
    INLINE = "inline"
    PEDESTAL = "pedestal"
    HANDHOLE = "handhole"
    WALL_MOUNT = "wall-mount"
    AERIAL = "aerial"

    CHOICES = [
        (DOME, "Dome", "blue"),
        (INLINE, "Inline", "cyan"),
        (PEDESTAL, "Pedestal", "purple"),
        (HANDHOLE, "Handhole", "gray"),
        (WALL_MOUNT, "Wall-mount", "green"),
        (AERIAL, "Aerial", "yellow"),
    ]


class SpliceTypeChoices(ChoiceSet):
    key = "Splice.splice_type"

    FUSION = "fusion"
    MECHANICAL = "mechanical"

    CHOICES = [
        (FUSION, "Fusion", "green"),
        (MECHANICAL, "Mechanical", "yellow"),
    ]


class FibreLinkStatusChoices(ChoiceSet):
    key = "FibreLink.status"

    STATUS_PLANNED = "planned"
    STATUS_ACTIVE = "active"
    STATUS_DEGRADED = "degraded"
    STATUS_DOWN = "down"
    STATUS_DECOMMISSIONED = "decommissioned"

    CHOICES = [
        (STATUS_PLANNED, "Planned", "cyan"),
        (STATUS_ACTIVE, "Active", "green"),
        (STATUS_DEGRADED, "Degraded", "yellow"),
        (STATUS_DOWN, "Down", "red"),
        (STATUS_DECOMMISSIONED, "Decommissioned", "gray"),
    ]
