"""DTP-Spec-Fassade: Layout, Typo, Farbe, Prepress, I/O — 2.6.54.

Select-then-tool bleibt im Canvas; hier die dokumentierten APIs ohne
Kind-Koersion (Text/Bild/Render getrennt).
"""

from instantlensdoc.dtp.assets import (
    AssetLibrary,
    DtpSymbol,
    place_symbol,
    register_symbol,
    sync_linked_clones,
)
from instantlensdoc.dtp.boolean import weld_frames
from instantlensdoc.dtp.color import (
    BLEND_MODES,
    ColorSpec,
    convert,
    from_cmyk,
    from_lab,
    from_rgb,
    from_spot,
    icc_convert_rgb,
)
from instantlensdoc.dtp.export import (
    export_interactive_pdf,
    export_pdf_versions,
    export_pdfx3,
)
from instantlensdoc.dtp.geometry import (
    align_frames,
    distribute_frames,
    snap_mm,
    snap_to_guide_mm,
)
from instantlensdoc.dtp.import_graphics import import_graphic
from instantlensdoc.dtp.interactive import DtpWidget, attach_widgets_to_pdf
from instantlensdoc.dtp.model import DtpDocument, DtpFrame, DtpLayer, DtpMaster
from instantlensdoc.dtp.preflight import run_dtp_preflight
from instantlensdoc.dtp.sla import export_sla, import_sla
from instantlensdoc.dtp.type_extras import (
    DIGITS,
    FONT_FALLBACKS,
    apply_pair_kerning,
    expand_variables,
    format_number,
    keep_orphans_widows,
    list_script_fonts,
    resolve_cross_ref,
)

__all__ = [
    "AssetLibrary",
    "BLEND_MODES",
    "ColorSpec",
    "DIGITS",
    "DtpDocument",
    "DtpFrame",
    "DtpLayer",
    "DtpMaster",
    "DtpSymbol",
    "DtpWidget",
    "FONT_FALLBACKS",
    "align_frames",
    "apply_pair_kerning",
    "attach_widgets_to_pdf",
    "convert",
    "distribute_frames",
    "expand_variables",
    "export_interactive_pdf",
    "export_pdf_versions",
    "export_pdfx3",
    "export_sla",
    "format_number",
    "from_cmyk",
    "from_lab",
    "from_rgb",
    "from_spot",
    "icc_convert_rgb",
    "import_graphic",
    "import_sla",
    "keep_orphans_widows",
    "list_script_fonts",
    "place_symbol",
    "register_symbol",
    "resolve_cross_ref",
    "run_dtp_preflight",
    "snap_mm",
    "snap_to_guide_mm",
    "sync_linked_clones",
    "weld_frames",
]
