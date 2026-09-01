# Roadmap

Direction of record for `epy_reports`, kept beside `CHANGELOG.md`: this file
records what the application is expected to become, the changelog records
what it already is.

Author of record: Ing. Angel Navarro-Mora M.Sc.

## The document family

`epy_reports` produces reports. It is one of the editors `epy_studio` hosts,
alongside `epy_slides` and `epy_papers` and `epy_draft`, and they share the export
engines in `epy_export`. Anything recorded here that names the family
applies to the siblings too, and is recorded in their roadmaps as well.

## Pending

### Optional autosave (2026-09-01)

The editor must offer an **autosave that the user can turn on or off**.
Requested by the product owner; not scheduled.

Two things this has to get right, both of them the reason it is a
preference and not a default:

- **It is opt-in, and it stays where the user left it.** An editor that
  starts saving on its own is an editor that overwrote a draft somebody
  was still deciding about. The setting belongs with the other
  application preferences, not in a menu that resets between sessions.
- **A save must never land on top of an export or a render.** These
  applications write their output while the document is open; an
  autosave that fires mid-render is how a half-written file becomes the
  document of record.

Open, and to be answered when this is built rather than guessed at now:
what an autosave does with a document that has never been saved, and
whether the interval is a preference or fixed.
