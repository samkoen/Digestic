"""
Import de clients (pharmacies) depuis un export Sage (CSV) vers la table `pharmacies`.

Exécution (depuis le dossier `backend/`) : le chemin par défaut du CSV est la constante
`DEFAULT_CSV_PATH` en tête de ce fichier (modifiez-la pour votre machine). En option,
`--csv` surcharge ce chemin.

  .\\.venv\\Scripts\\python.exe scripts/migrate_pharmacies_from_sage_csv.py --commercial-id <UUID>
  .\\.venv\\Scripts\\python.exe scripts/migrate_pharmacies_from_sage_csv.py --csv "D:\\autre\\fichier.csv"

  # Si --commercial-id est omis : premier utilisateur avec rôle commercial ou admin.

  # Simulation sans écrire en base :
  --dry-run

Encodage : le script tente utf-8 (avec BOM), utf-8, Windows-1252, puis Latin-1
(exports Sage / Excel France souvent en cp1252). Forcer avec --encoding si besoin.

Délimiteur : en France le CSV Sage / Excel est souvent en point-virgule « ; » (détecté
automatiquement sur la 1ʳᵉ ligne). Avec des virgules **dans** les chiffres (ex. ,000000),
un fichier en « , » est mal parsé. Forcer avec --delimiter ; si besoin.

--- Correspondance principale CSV -> colonnes PostgreSQL ---

  CT_Intitule          -> name
  CT_Adresse           -> address_line (CT_Complement ajouté sur la même ligne si présent)
  CT_CodePostal        -> postal_code
  CT_Ville             -> city
  CT_Pays              -> country (normalisé en code ISO2, ex. France -> FR)
  CT_Telephone         -> phone
  CT_EMail             -> email
  CT_Contact           -> owner_name (optionnel)
  RIB                  -> rib + has_rib (True si RIB non vide et différent de zéros)
  TYPE                 -> status / pharmacy_status (Sage: actif, standby, desactive, …)
                          — pas le mode de paiement ; import : payment_mode = virement_30
  ID GOCARLES          -> gocardless_customer_id
  IDSEPA               -> gocardless_mandate_id
  CT_Num               -> sert à générer un UUID déterministe (réimport = même clé = upsert)

Les autres colonnes Sage ne sont pas stockées (SIRET, statistiques, etc.) sauf évolution
future du modèle. CT_Num n’est pas une colonne SQL : l’id interne est un UUID v5
basé sur CT_Num pour pouvoir relancer l’import sans dupliquer.

Champs requis côté app non fournis par le CSV :
  warehouse_id  -> entrepôt par défaut (bootstrap) ou --warehouse-id
  commercial_id -> --commercial-id ou premier commercial/admin en base
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import uuid
from pathlib import Path

# racine backend/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# --- À modifier : emplacement de votre export Sage (CSV) sur le disque ---
DEFAULT_CSV_PATH: Path = Path(r"C:\Users\USER\Downloads\export_pharmas_1.txt")

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

load_dotenv(_ROOT / ".env")

import app.db.models as orm
from app.db.bootstrap import DEFAULT_WAREHOUSE_NAME, get_or_create_default_warehouse_id
import app.db.session as session_mod

# UUID v5 déterministe par numéro client Sage (même numéro => même id)
_NS_IMPORT = uuid.uuid5(uuid.NAMESPACE_DNS, "digestic.sage.pharmacy")

# Ordre d’essai pour les exports Windows / Sage (souvent cp1252, pas utf-8)
_DEFAULT_CSV_ENCODINGS: tuple[str, ...] = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "iso-8859-1",
)


def _decode_csv_bytes(raw: bytes, forced_encoding: str | None) -> tuple[str, str]:
    if forced_encoding:
        return raw.decode(forced_encoding), forced_encoding
    for enc in _DEFAULT_CSV_ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    text = raw.decode("utf-8", errors="replace")
    return text, "utf-8 (caractères incertains, erreurs remplacées)"


def _s(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _norm_header_key(k: str | None) -> str:
    if k is None:
        return ""
    t = k.replace("\ufeff", "").replace("\u200b", "").replace("\u200c", "")
    return re.sub(r"\s+", "", t).strip().lower()


def _get(row: dict, *keys: str) -> str:
    for k in keys:
        for cand in (k, k.strip(), k.replace(" ", "")):
            if cand in row and _s(row[cand]) != "":
                return _s(row[cand])
    return ""


def _get_ci(row: dict, *keys: str) -> str:
    """Comme _get, mais clés d’en-tête insensibles à la casse (exports Sage/Excel)."""
    index = { _norm_header_key(k): k for k in row if k is not None }
    for k in keys:
        for cand in (k, k.strip(), k.replace(" ", "")):
            alt = re.sub(r"\s+", "", cand).lower()
            orig = index.get(alt)
            if orig is not None and _s(row[orig]) != "":
                return _s(row[orig])
    return ""


_EMAIL_RE = re.compile(
    r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)


def _clean_email_raw(s: str) -> str:
    t = _s(s)
    t = t.replace("\xa0", " ").strip(' "\'')
    if t.lower().startswith("mailto:"):
        t = t[7:].strip()
    return t


def _extract_likely_email_in_cell(s: str) -> str:
    """Excel peut exporter ="adresse@domaine.tld" : on extrait l’e-mail par regex."""
    t = _clean_email_raw(s)
    if not t:
        return ""
    m = _EMAIL_RE.search(t)
    return m.group(0) if m else t


def _sage_row_email(row: dict) -> str:
    """
    Récupère l’e-mail Sage. Souvent, le nombre de champs d’une ligne de données
    ne coïncide pas avec l’en-tête (ligne plus longue ou plus courte) : les
    colonnes se décalent, CT_EMail ne reçoit plus l’e-mail, voire reçoit « 0 »/« 2 ».
    On tente d’abord la colonne nommée, puis toute cellule (ordre d’en-tête + reste
    `row[None]`) avec une regex, ce qui gère l’export `154` colonnes / `162` valeurs
    (Sage).
    """

    def _pick(s: str) -> str | None:
        m = _EMAIL_RE.search(_clean_email_raw(s) if s else "")
        return m.group(0) if m else None

    # 1) Colonne d’e-mail théorique (export aligné)
    direct = _get_ci(
        row,
        "CT_EMail",
        "CT_Email",
        "CT_Mail",
        "Email",
        "E_Mail",
        "E-mail",
    )
    if direct and (e0 := _pick(direct)):
        return e0

    # 2) Ligne désalignée : toutes les cellules, y compris champs en trop (dict None)
    for k, v in row.items():
        if v is None:
            continue
        if k is None and isinstance(v, list):
            for part in v:
                if (e1 := _pick(_s(part))):
                    return e1
            continue
        if k is not None and "numpayeur" in _norm_header_key(k):
            continue
        if (e2 := _pick(_s(v) if v is not None else "")):
            return e2
    return ""


def _detect_csv_delimiter(text: str) -> str:
    """Sage/Excel FR : souvent `;` ; RU/US : `,` . Les montants `,000000` comptent comme virgules :
    on n’utilise le `,` commme séparateur que s’il domine vraiment sur `;` et TAB."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ","
    first = lines[0]
    n_semi, n_comma, n_tab = first.count(";"), first.count(","), first.count("\t")
    if n_semi >= 2 and n_semi > n_comma and n_semi >= n_tab:
        return ";"
    if n_tab >= 2 and n_tab > max(n_semi, n_comma):
        return "\t"
    return ","


def _normalize_country(pays: str) -> str:
    p = _s(pays)
    if not p:
        return "FR"
    if len(p) == 2 and p.isalpha():
        return p.upper()
    m = {
        "france": "FR",
        "fr": "FR",
        "unitedkingdom": "GB",
        "royaume-uni": "GB",
        "r.u.": "GB",
        "germany": "DE",
        "deutschland": "DE",
        "belgium": "BE",
        "belgique": "BE",
    }
    key = re.sub(r"[^a-z]", "", p.lower())
    if key in m:
        return m[key]
    return p[:2].upper() if len(p) >= 2 else "FR"


def _pharmacy_status_from_sage_type_column(val: str) -> str:
    """
    Colonne CSV `TYPE` (entre RIB et REGION) : valeurs normalisées pour `pharmacy_status`.
    """
    t = re.sub(r"\s+", " ", _s(val)).strip().upper()
    if not t:
        return "actif"
    if t in (
        "DESACTIVE",
        "DÉSACTIVÉ",
        "DESACTIVÉ",
        "INACTIF",
        "INACTIVE",
    ) or "DESACT" in t:
        return "desactive"
    if "STAND" in t and "BY" in t:
        return "standby"
    if t in ("ACTIF", "ACTIVE", "A"):
        return "actif"
    return re.sub(r"\s+", " ", t.lower())[:32] or "autre"


def _is_meaningful_rib(rib: str) -> bool:
    r = re.sub(r"\s", "", _s(rib))
    if not r:
        return False
    if set(r) <= {"0", "."}:
        return False
    return True


def _pharmacy_uuid(ct_num: str) -> uuid.UUID:
    s = re.sub(r"\s", "", _s(ct_num))
    if not s:
        return uuid.uuid4()
    return uuid.uuid5(_NS_IMPORT, f"ct:{s}")


def _row_to_orm(
    row: dict,
    *,
    wid: uuid.UUID,
    cid: uuid.UUID,
) -> orm.Pharmacy:
    ct_num = _get(row, "CT_Num", "NUM CLIENT")
    name = _get(row, "CT_Intitule")
    if not name:
        raise ValueError("CT_Intitule vide")

    addr = _get(row, "CT_Adresse")
    comp = _get(row, "CT_Complement")
    address_line = " ".join(x for x in (addr, comp) if x).strip() or "—"
    city = _get(row, "CT_Ville") or "—"
    cp = _get(row, "CT_CodePostal") or "00000"
    country = _normalize_country(_get(row, "CT_Pays", "Pays"))
    phone = _get(row, "CT_Telephone") or "0000000000"
    # CT_EMail, CT_Mail, etc. (voir _sage_row_email) + délimiteur CSV `;` géré ailleurs
    email = _sage_row_email(row)
    if not email:
        site = _get_ci(row, "CT_Site", "ct_site")
        m = _EMAIL_RE.search(_clean_email_raw(site) if site else "")
        if m and "://" not in (site or "").lower():
            email = m.group(0)
    if not email:
        base = re.sub(r"\W", "", ct_num) or "client"
        email = f"import+{base}@placeholder.local"

    owner_name = _get(row, "CT_Contact") or None
    rib_raw = _get(row, "RIB")
    has_rib = _is_meaningful_rib(rib_raw)
    rib = (rib_raw[:100] if has_rib else None) if _s(rib_raw) else None

    gc = _get(row, "ID GOCARLES", "IDGOCARLES")
    sm = _get(row, "IDSEPA")

    return orm.Pharmacy(
        id=_pharmacy_uuid(ct_num or name + cp),
        name=name[:255],
        address_line=address_line[:500],
        city=city[:120],
        postal_code=cp[:20],
        country=country[:2],
        phone=phone[:50],
        email=email[:255],
        email_secondary=None,
        owner_name=owner_name[:255] if owner_name else None,
        owner_phone=None,
        owner_email=None,
        warehouse_id=wid,
        commercial_id=cid,
        has_rib=has_rib,
        rib=rib,
        payment_mode="virement 30 jours",
        gocardless_customer_id=gc[:255] if gc else None,
        gocardless_mandate_id=sm[:255] if sm else None,
        pharmacy_status=_pharmacy_status_from_sage_type_column(_get(row, "TYPE")),
        last_visit_at=None,
        next_visit_date=None,
        photo_url=None,
        latitude=None,
        longitude=None,
    )


def _session() -> Session:
    session_mod.get_engine()
    if session_mod.SessionLocal is None:
        raise RuntimeError("Session non initialisée (DATABASE_URL manquant ?)")
    return session_mod.SessionLocal()


def _resolve_commercial_id(db: Session, arg: str | None) -> uuid.UUID:
    if _s(arg):
        return uuid.UUID(_s(arg))
    u = db.execute(
        select(orm.User)
        .where(orm.User.role.in_(("commercial", "admin")))
        .order_by(orm.User.created_at)
        .limit(1)
    ).scalar_one_or_none()
    if u is None:
        raise SystemExit(
            "Aucun utilisateur role commercial/admin. Créez-en un ou utilisez --commercial-id UUUID"
        )
    return u.id


def _resolve_warehouse_id(
    db: Session, arg: str | None, *, create_default: bool
) -> uuid.UUID:
    if _s(arg):
        return uuid.UUID(_s(arg))
    w = db.execute(
        select(orm.Warehouse).where(orm.Warehouse.name == DEFAULT_WAREHOUSE_NAME)
    ).scalar_one_or_none()
    if w is not None:
        return w.id
    if create_default:
        return get_or_create_default_warehouse_id(db)
    raise SystemExit(
        "Aucun entrepôt par défaut en base. Lancez d’abord l’import sans --dry-run, "
        "ou indiquez --warehouse-id=UUID (entrepôt existant)."
    )


def run(
    csv_path: Path,
    commercial_id: str | None,
    warehouse_id: str | None,
    dry_run: bool,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> int:
    if not csv_path.is_file():
        print(f"Fichier introuvable : {csv_path}", file=sys.stderr)
        return 1

    if dry_run:
        print("[dry-run] Aucun écriture en base.\n")

    raw = csv_path.read_bytes()
    try:
        text, enc_used = _decode_csv_bytes(raw, _s(encoding) or None)
    except UnicodeDecodeError as e:
        print(
            f"Décodage impossible (--encoding=cp1252 ou utf-8-sig) : {e}",
            file=sys.stderr,
        )
        return 1
    print(f"Fichier lu — encodage : {enc_used}", file=sys.stderr)

    dopt = _s(delimiter) if delimiter else ""
    if len(dopt) == 1 and dopt in ";\t,":
        delim = dopt
        print(
            f"Délimiteur CSV : {delim!r} (imposé par --delimiter)",
            file=sys.stderr,
        )
    else:
        delim = _detect_csv_delimiter(text)
        print(
            f"Délimiteur CSV : {delim!r} (auto : Sage/Excel FR = souvent « ; » )",
            file=sys.stderr,
        )

    db = _session()
    n_ok, n_err = 0, 0
    try:
        wid = _resolve_warehouse_id(db, warehouse_id, create_default=not dry_run)
        cid = _resolve_commercial_id(db, commercial_id)

        f = io.StringIO(text, newline="")
        reader = csv.DictReader(f, delimiter=delim)
        if not reader.fieldnames:
            print("CSV sans en-têtes", file=sys.stderr)
            return 1
        for i, row in enumerate(reader, start=2):
            try:
                ph = _row_to_orm(row, wid=wid, cid=cid)
                if dry_run:
                    if n_ok < 3:
                        print(
                            f"Ligne {i}: {ph.name!r} | {ph.postal_code} {ph.city!r} | "
                            f"mode={ph.payment_mode} | id={ph.id}"
                        )
                    n_ok += 1
                    continue
                # upsert
                ex = db.get(orm.Pharmacy, ph.id)
                if ex is None:
                    db.add(ph)
                else:
                    for attr in (
                        "name",
                        "address_line",
                        "city",
                        "postal_code",
                        "country",
                        "phone",
                        "email",
                        "owner_name",
                        "has_rib",
                        "rib",
                        "payment_mode",
                        "gocardless_customer_id",
                        "gocardless_mandate_id",
                        "pharmacy_status",
                        "warehouse_id",
                        "commercial_id",
                    ):
                        setattr(ex, attr, getattr(ph, attr))
                n_ok += 1
                if n_ok % 200 == 0:
                    db.commit()
            except Exception as e:
                n_err += 1
                print(f"Ligne {i} ignorée: {e}", file=sys.stderr)
        if not dry_run:
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erreur : {e}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(
        f"Terminé : {n_ok} ligne(s) traitée(s), {n_err} erreur(s)."
        + ("" if not dry_run else " (simulation)")
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"Fichier CSV (défaut : {DEFAULT_CSV_PATH})",
    )
    p.add_argument("--commercial-id", default="", help="UUID du commercial (sinon 1er commercial/admin)")
    p.add_argument("--warehouse-id", default="", help="UUID de l'entrepôt (sinon entrepôt par défaut)")
    p.add_argument("--dry-run", action="store_true", help="Affiche des exemples sans insérer")
    p.add_argument(
        "--encoding",
        default="",
        help="Forcer l’encodage du fichier (ex. cp1252, utf-8-sig) ; sinon détection auto",
    )
    p.add_argument(
        "--delimiter",
        default="",
        metavar="C",
        help="Séparateur de colonne : un seul caractère ; , ou tab (\\t). Vide = auto",
    )
    a = p.parse_args()
    tab = "\t" if a.delimiter in ("\\t", "tab", "TAB") else a.delimiter
    return run(
        a.csv,
        a.commercial_id or None,
        a.warehouse_id or None,
        a.dry_run,
        a.encoding or None,
        tab,
    )


if __name__ == "__main__":
    raise SystemExit(main())
