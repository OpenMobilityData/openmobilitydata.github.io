# openmobilitydata.github.io

The umbrella site of the [OpenMobilityData](https://github.com/OpenMobilityData) repositories: public records and open data on mobility and road safety in Montréal, organized by topic, with one entry per document, analysis, dataset or application.

It is served at https://openmobilitydata.ca/ (GitHub Pages; the older `openmobilitydata.github.io` addresses, including those of the other repositories' web copies, redirect there).

The site is a map. It holds no document of its own: every entry links to a file or a folder in one of the organization's repositories, whose README gives the provenance.

## How it is built

- `catalogue.toml` is the single source: the topics, their sections and every entry (title, one-sentence description, status, date, repository, folder, document links).
- `content/about.md` is the text of the About page.
- `build.py` (Python 3.11 or later, standard library only) writes the HTML pages at the root of the repository. `assets/` holds the style sheet and the script of the « All documents » filter.

```
python3 build.py --check-links
```

`--check-links` verifies that every linked file exists, in the sibling clones of the repositories when they are present and through `gh` otherwise. The build stops on a missing file, an unknown section or a duplicate identifier.

To add a document: add an `[[entry]]` block to `catalogue.toml`, run the build, commit the catalogue and the regenerated pages together.

## Rules

- Entries describe; they do not evaluate, recommend or impute motives. The wording follows the README of the folder an entry points to.
- Every entry carries a status: a record as issued, a checked transcript, a machine draft, an analysis, preliminary results, a draft. A draft or a machine draft is always labelled.
- No file is copied here from another repository, and nothing is linked that is not already public.
- The pages set no cookies and load nothing from other servers.

## Use of AI

The catalogue, the build script and the pages were produced with an AI assistant, Anthropic's Claude, in sessions directed by the author, who reviewed them and is alone responsible for the content. Commits to which the assistant contributed name it as co-author.
