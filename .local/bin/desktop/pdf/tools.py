"""Registre des 16 outils : source unique pour le CLI, le menu rofi (desk-pdf) et la fenêtre."""
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import ops
from .errors import OpError
from .i18n import bi, t


@dataclass
class Option:
    key: str
    kind: str                   # choice | text | password | bool | int
    label: str                  # « français ‖ english »
    choices: list = field(default_factory=list)   # [(valeur, « fr ‖ en »)]
    default: str = ""
    when: tuple = None          # (clé, valeur) : option posée seulement si l'autre vaut ça
    confirm: bool = False       # password : saisir deux fois
    required: bool = False      # text : vide refusé
    hint: str = ""              # aide affichée sous la question (« fr ‖ en »)


@dataclass
class Tool:
    id: str
    label: str
    icon: str
    kind: str                   # simple | organizer | editor | sign
    accepts: str                # pdf | pdfs | images | convertible | url
    options: list = field(default_factory=list)
    min_files: int = 1


RANGES_HINT = "ex. 1-3,5,8- (8- = jusqu'à la fin) ‖ e.g. 1-3,5,8- (8- = to the end)"

TOOLS = [
    Tool("merge", "Fusionner des PDF ‖ Merge PDF", "archive-insert", "organizer", "pdfs", min_files=2),
    Tool("split", "Découper un PDF ‖ Split PDF", "edit-cut", "simple", "pdf", [
        Option("mode", "choice", "Découpage ‖ Split mode", [
            ("each", "Une page par fichier ‖ One page per file"),
            ("every", "Toutes les N pages ‖ Every N pages"),
            ("ranges", "Par plages (1-3,4-7,8-) ‖ By ranges (1-3,4-7,8-)")], "each"),
        Option("n", "int", "Nombre de pages par fichier ‖ Pages per file", default="2", when=("mode", "every")),
        Option("ranges", "text", "Plages (un fichier par plage) ‖ Ranges (one file per range)",
               when=("mode", "ranges"), required=True, hint=RANGES_HINT)]),
    Tool("compress", "Compresser un PDF ‖ Compress PDF", "package", "simple", "pdf", [
        Option("level", "choice", "Niveau ‖ Level", [
            ("recommended", "Recommandé (150 dpi) ‖ Recommended (150 dpi)"),
            ("light", "Léger (300 dpi, qualité impression) ‖ Light (300 dpi, print quality)"),
            ("strong", "Fort (72 dpi, écran) ‖ Strong (72 dpi, screen)")], "recommended")]),
    Tool("edit", "Modifier un PDF ‖ Edit PDF", "document-edit", "editor", "pdf"),
    Tool("sign", "Signer un PDF ‖ Sign PDF", "draw-calligraphic", "sign", "pdf"),
    Tool("convert", "Convertir (Office, html, md → PDF · PDF → texte) ‖ Convert (Office, html, md → PDF · PDF → text)",
         "x-office-document", "simple", "convertible"),
    Tool("img2pdf", "Images → PDF ‖ Images to PDF", "image-x-generic", "simple", "images", [
        Option("fit", "choice", "Mise en page ‖ Page layout", [
            ("a4", "Page A4, image ajustée ‖ A4 page, image fitted"),
            ("image", "Taille de l'image ‖ Image size")], "a4")]),
    Tool("pdf2img", "PDF → Images ‖ PDF to Images", "folder-pictures", "simple", "pdf", [
        Option("fmt", "choice", "Format ‖ Format", [("png", "PNG ‖ PNG"), ("jpg", "JPG ‖ JPG")], "png"),
        Option("dpi", "choice", "Résolution ‖ Resolution", [
            ("150", "150 dpi (écran) ‖ 150 dpi (screen)"), ("300", "300 dpi (impression) ‖ 300 dpi (print)"),
            ("72", "72 dpi (miniatures) ‖ 72 dpi (thumbnails)")], "150"),
        Option("ranges", "text", "Pages (vide = toutes) ‖ Pages (empty = all)", hint=RANGES_HINT)]),
    Tool("extract-images", "Extraire les images d'un PDF ‖ Extract PDF images", "insert-image", "simple", "pdf"),
    Tool("protect", "Protéger par mot de passe ‖ Protect PDF", "document-encrypt", "simple", "pdf", [
        Option("new_password", "password", "Nouveau mot de passe ‖ New password", confirm=True, required=True),
        Option("forbid", "bool", "Interdire l'impression et la copie ‖ Forbid printing and copying", default="no")]),
    Tool("unlock", "Déverrouiller un PDF ‖ Unlock PDF", "document-decrypt", "simple", "pdf"),
    Tool("rotate", "Pivoter des pages ‖ Rotate PDF pages", "object-rotate-right", "simple", "pdf", [
        Option("angle", "choice", "Rotation ‖ Rotation", [
            ("90", "90° horaire ‖ 90° clockwise"), ("180", "180° ‖ 180°"),
            ("270", "90° anti-horaire ‖ 90° counter-clockwise")], "90"),
        Option("ranges", "text", "Pages (vide = toutes) ‖ Pages (empty = all)", hint=RANGES_HINT)]),
    Tool("remove", "Supprimer des pages ‖ Remove PDF pages", "edit-delete", "simple", "pdf", [
        Option("ranges", "text", "Pages à supprimer ‖ Pages to remove", required=True, hint=RANGES_HINT)]),
    Tool("extract", "Extraire des pages ‖ Extract PDF pages", "extract-archive", "simple", "pdf", [
        Option("ranges", "text", "Pages à extraire (dans cet ordre) ‖ Pages to extract (in this order)",
               required=True, hint=RANGES_HINT)]),
    Tool("rearrange", "Réorganiser les pages ‖ Rearrange PDF pages", "view-sort-ascending", "organizer", "pdf"),
    Tool("webpage", "Page web → PDF ‖ Webpage to PDF", "web-browser", "simple", "url"),
]

_BY_ID = {tl.id: tl for tl in TOOLS}


def get(tool_id):
    try:
        return _BY_ID[tool_id]
    except KeyError:
        raise KeyError(tool_id) from None


def options_json(tool_id):
    return [asdict(o) for o in get(tool_id).options]


def active_options(tool, opts):
    """Options qui s'appliquent vu les autres valeurs (when), avec leurs valeurs par défaut."""
    vals = {o.key: opts.get(o.key, o.default) for o in tool.options}
    return {k: v for k, v in vals.items()
            if not (w := next(o.when for o in tool.options if o.key == k)) or vals.get(w[0]) == w[1]}


def _yes(v):
    return str(v).lower() in ("1", "yes", "true", "oui", "y", "o")


def run(tool_id, files, opts=None, password=None):
    """Lance un outil → chemins créés. merge / img2pdf prennent toutes les entrées ;
    les autres traitent chaque fichier."""
    tool = get(tool_id)
    o = active_options(tool, opts or {})
    for opt in tool.options:
        if opt.required and opt.key in o and not str(o[opt.key]).strip():
            raise OpError(t(f"{bi(opt.label)} : champ obligatoire", f"{bi(opt.label)}: required"))
    files = [f if tool.accepts == "url" else Path(f) for f in files]
    if len(files) < tool.min_files:
        raise OpError(t(f"Il faut au moins {tool.min_files} fichier(s)", f"At least {tool.min_files} file(s) needed"))
    ops.WARNINGS.clear()
    if tool_id == "merge":
        return ops.merge(files, password)
    if tool_id == "img2pdf":
        return ops.images_to_pdf(files, o["fit"])
    out = []
    for f in files:
        out += _one(tool_id, f, o, password)
    return out


def _one(tool_id, f, o, password):
    match tool_id:
        case "split":
            return ops.split(f, o["mode"], int(o.get("n") or 1), o.get("ranges", ""), password)
        case "compress":
            return ops.compress(f, o["level"], password)
        case "convert":
            return ops.convert(f, password)
        case "pdf2img":
            return ops.pdf_to_images(f, o["fmt"], int(o["dpi"]), o["ranges"], password)
        case "extract-images":
            return ops.extract_images(f, password)
        case "protect":
            return ops.protect(f, o["new_password"], _yes(o["forbid"]), password)
        case "unlock":
            return ops.unlock(f, password)
        case "rotate":
            return ops.rotate(f, int(o["angle"]), o["ranges"], password)
        case "remove":
            return ops.remove_pages(f, o["ranges"], password)
        case "extract":
            return ops.extract_pages(f, o["ranges"], password)
        case "rearrange":
            return ops.reverse(f, password)
        case "webpage":
            return ops.webpage(str(f))
        case "edit" | "sign":
            raise OpError("edit/sign : desk pdf gui --tool " + tool_id)
    raise KeyError(tool_id)
