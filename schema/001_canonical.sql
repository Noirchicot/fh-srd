-- fh-srd — canonical schema v1
--
-- Three invariants are enforced HERE, in the database, not in the importer's
-- good intentions:
--
--   1. Every record belongs to EXACTLY ONE layer. There is no merged record.
--   2. Every `srd` record carries a pinned source, the CC-BY licence and the
--      verbatim attribution. A row that cannot say where it comes from cannot
--      be inserted.
--   3. The `srd` layer is importer-owned. Any other writer is refused.
--
-- Nothing in this file records a timestamp or any other value that changes
-- between two runs. That is deliberate: `sqlite3 srd.sqlite .dump` must be
-- byte-identical across replays, and a clock would break that.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Layers — fixed vocabulary, never extended at import time
-- ---------------------------------------------------------------------------
CREATE TABLE layer (
  id          TEXT PRIMARY KEY,
  rank        INTEGER NOT NULL UNIQUE,   -- resolution order, low = base
  label       TEXT NOT NULL,
  origin      TEXT NOT NULL,             -- who authored the content
  license     TEXT NOT NULL,
  license_url TEXT,
  -- 1 = redistributable under the upstream CC-BY grant (i.e. the SRD subset).
  -- This is the column that answers "what may I publish?" in one query.
  cc_by_srd   INTEGER NOT NULL CHECK (cc_by_srd IN (0, 1)),
  notes       TEXT NOT NULL DEFAULT ''
);

INSERT INTO layer (id, rank, label, origin, license, license_url, cc_by_srd, notes) VALUES
  ('srd',        10, 'SRD 5.2.1',      'Wizards of the Coast LLC', 'CC-BY-4.0',
   'https://creativecommons.org/licenses/by/4.0/legalcode', 1,
   'Imported from the pinned official PDF. Importer-owned: no hand edits.'),
  ('phb_opt',    20, 'PHB optionnel',  'Wizards of the Coast LLC', 'proprietary', NULL, 0,
   'Rules present in the 2024 books but NOT in the SRD subset. Never publishable. Present so a home game keeps every word.'),
  ('fates_hand', 30, 'Fate''s Hand',   'Eric',                     'proprietary', NULL, 0,
   'Eric''s original content. His to license as he wishes — deliberately NOT tagged cc_by_srd, which means "covered by the WotC grant", not "publishable".'),
  ('manual',     40, 'Manuel',         'table',                    'proprietary', NULL, 0,
   'Hand entry at the table. Lowest trust, highest priority.');

-- ---------------------------------------------------------------------------
-- Sources — the pinned upstream artefacts. Determinism starts here.
-- ---------------------------------------------------------------------------
CREATE TABLE source (
  id            TEXT PRIMARY KEY,        -- 'srd-5.2.1-fr'
  title         TEXT NOT NULL,
  publisher     TEXT NOT NULL,
  version       TEXT NOT NULL,           -- '5.2.1'
  lang          TEXT NOT NULL,           -- 'fr' | 'en'
  url           TEXT NOT NULL,
  sha256        TEXT NOT NULL,           -- the pin. The importer refuses a mismatch.
  bytes         INTEGER NOT NULL,
  etag          TEXT,
  last_modified TEXT,                    -- upstream header, NOT our clock
  license       TEXT NOT NULL,
  license_url   TEXT NOT NULL,
  attribution   TEXT NOT NULL            -- verbatim statement required by the source
);

-- ---------------------------------------------------------------------------
-- Records — one row, one layer, provenance mandatory
-- ---------------------------------------------------------------------------
CREATE TABLE record (
  id             TEXT PRIMARY KEY,
  layer          TEXT NOT NULL REFERENCES layer(id),
  kind           TEXT NOT NULL,          -- 'spell' | 'class' | 'species' | 'feat' | ...
  lang           TEXT NOT NULL,
  slug           TEXT NOT NULL,
  name           TEXT NOT NULL,          -- display name, in `lang`
  data           TEXT NOT NULL,          -- canonical JSON payload
  content_hash   TEXT NOT NULL,          -- sha256 over the canonical payload

  -- Provenance / attribution — on the ROW, not in a README.
  source_id      TEXT REFERENCES source(id),
  source_locator TEXT NOT NULL DEFAULT '',  -- 'p.148' — where in the source
  srd_version    TEXT,
  license        TEXT NOT NULL,
  attribution    TEXT NOT NULL,

  -- The id spells out the layer, so a record can never be mistaken for another
  -- layer's once it has left the database.
  CHECK (id = layer || ':' || kind || ':' || lang || ':' || slug),

  -- An SRD row that cannot cite its source is not an SRD row.
  CHECK (layer <> 'srd' OR (source_id IS NOT NULL
                            AND license = 'CC-BY-4.0'
                            AND srd_version IS NOT NULL
                            AND length(attribution) > 0
                            AND length(source_locator) > 0)),

  UNIQUE (layer, kind, lang, slug)
);

CREATE INDEX record_by_kind  ON record (layer, kind, lang);
CREATE INDEX record_by_slug  ON record (slug);

-- ---------------------------------------------------------------------------
-- Cross-layer relations — the ONLY way a layer touches another
-- ---------------------------------------------------------------------------
-- A Fate's Hand rule that changes an SRD spell does NOT edit the SRD row.
-- It inserts an edge. Publishing the SRD layer alone is then:
--     SELECT * FROM record WHERE layer = 'srd';   -- and drop this table.
CREATE TABLE record_link (
  src_id TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
  dst_id TEXT NOT NULL REFERENCES record(id) ON DELETE CASCADE,
  rel    TEXT NOT NULL CHECK (rel IN
           ('translation_of','overrides','extends','replaces','see_also')),
  note   TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (src_id, dst_id, rel),
  CHECK (src_id <> dst_id)
);

-- ---------------------------------------------------------------------------
-- Exclusion register — "exclure et signaler", made queryable
-- ---------------------------------------------------------------------------
-- Everything the pipeline refused to include, and why. This table IS the audit
-- artefact; an empty one means the pipeline was not paying attention.
CREATE TABLE exclusion (
  id             TEXT PRIMARY KEY,
  kind           TEXT NOT NULL,
  name           TEXT NOT NULL,
  lang           TEXT NOT NULL DEFAULT '',
  reason         TEXT NOT NULL CHECK (reason IN (
                   'not-in-srd',        -- exists in the 2024 books, absent from the SRD subset
                   'trademark',         -- WotC mark: "D&D", "Player's Handbook", the logo
                   'product-identity',  -- named IP: Forgotten Realms, Dragonlance, Underdark
                   'unparsed',          -- extraction could not produce a trustworthy record
                   'extractor-conflict',-- PyMuPDF and pdftotext disagree on the text
                   'slug-collision',    -- two records claim the same identifier
                   'ambiguous')),       -- membership in the SRD is not certain -> excluded
  detail         TEXT NOT NULL,
  source_locator TEXT NOT NULL DEFAULT '',
  decided_by     TEXT NOT NULL          -- 'importer' | 'audit-2026-06-26' | 'eric'
);

CREATE INDEX exclusion_by_reason ON exclusion (reason);

-- ---------------------------------------------------------------------------
-- Import ledger — identity of the run, with no clock in it
-- ---------------------------------------------------------------------------
CREATE TABLE import_run (
  id                 TEXT PRIMARY KEY,  -- sha256(pipeline_version | lock hash | extractor)
  pipeline_version   TEXT NOT NULL,
  sources_lock_sha256 TEXT NOT NULL,
  extractor          TEXT NOT NULL,     -- 'pymupdf 1.26.5 / mupdf 1.26.10'
  cross_checker      TEXT NOT NULL,     -- 'poppler pdftotext 26.03.0'
  record_count       INTEGER NOT NULL,
  exclusion_count    INTEGER NOT NULL
);

-- ---------------------------------------------------------------------------
-- Write guard on the SRD layer
-- ---------------------------------------------------------------------------
-- SQLite has no roles, so the guard is an explicit latch. The importer opens
-- it, writes, and closes it. Anything else touching layer='srd' aborts.
CREATE TABLE guard (
  k TEXT PRIMARY KEY,
  v INTEGER NOT NULL CHECK (v IN (0, 1))
);
INSERT INTO guard (k, v) VALUES ('srd_import_open', 0);

CREATE TRIGGER srd_guard_insert BEFORE INSERT ON record
WHEN NEW.layer = 'srd'
 AND (SELECT v FROM guard WHERE k = 'srd_import_open') = 0
BEGIN
  SELECT RAISE(ABORT, 'layer=srd is importer-owned: open the import guard');
END;

CREATE TRIGGER srd_guard_update BEFORE UPDATE ON record
WHEN (OLD.layer = 'srd' OR NEW.layer = 'srd')
 AND (SELECT v FROM guard WHERE k = 'srd_import_open') = 0
BEGIN
  SELECT RAISE(ABORT, 'layer=srd is importer-owned: open the import guard');
END;

CREATE TRIGGER srd_guard_delete BEFORE DELETE ON record
WHEN OLD.layer = 'srd'
 AND (SELECT v FROM guard WHERE k = 'srd_import_open') = 0
BEGIN
  SELECT RAISE(ABORT, 'layer=srd is importer-owned: open the import guard');
END;

-- The SRD is a base. It never modifies anything above it; higher layers point
-- down at it. An edge that would make the SRD amend another layer is a bug.
CREATE TRIGGER srd_never_overrides BEFORE INSERT ON record_link
WHEN NEW.rel IN ('overrides', 'extends', 'replaces')
 AND (SELECT layer FROM record WHERE id = NEW.src_id) = 'srd'
BEGIN
  SELECT RAISE(ABORT, 'the srd layer never overrides: invert the edge');
END;

-- ---------------------------------------------------------------------------
-- Views the exports and the audit read from
-- ---------------------------------------------------------------------------
-- Exactly what may ship under the WotC CC-BY grant. If this view is the whole
-- export, the export is compliant.
CREATE VIEW publishable_srd AS
  SELECT r.* FROM record r
  JOIN layer l ON l.id = r.layer
  WHERE l.cc_by_srd = 1;

-- Any record missing its provenance, in any layer. Must always be empty.
CREATE VIEW provenance_gaps AS
  SELECT id, layer, kind, name,
         CASE WHEN length(attribution) = 0 THEN 'no attribution'
              WHEN length(license) = 0     THEN 'no licence'
              WHEN layer = 'srd' AND source_id IS NULL THEN 'no source'
              ELSE 'ok' END AS gap
  FROM record
  WHERE length(attribution) = 0
     OR length(license) = 0
     OR (layer = 'srd' AND source_id IS NULL);
