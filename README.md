# Antonio Laface — academic website

Live site: https://alaface.github.io

A static, responsive website with daily updates of publications, preprints and all public GitHub repositories. The home photograph is the original `images/home.jpg` from the UdeC website, preserved without modification.

## Update and render

Python 3.9+; no packages, API keys or paid services required.

```sh
python scripts/update_site.py           # fetch metadata and render the site
python scripts/update_site.py --offline # render the last successful snapshots
python -m unittest discover -s tests -v
python -m http.server 8000              # preview at http://localhost:8000
```

The script generates the home, publications, preprints and software pages. Edit their templates in `scripts/update_site.py`; shared styles live in `assets/css/style.css`. Other research pages are independent.

## Sources and classification

- **Publications:** the [zbMATH Open REST API](https://api.zbmath.org/v1/) using the disambiguated author ID `laface.antonio`. Includes published articles, chapters and the book; excludes records classified as arXiv preprints. Bibliographic metadata are selected and reformatted under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); the page attributes zbMATH Open / FIZ Karlsruhe. Reviews are not copied. Source license fields are retained in the saved metadata.
- **Preprints:** the [arXiv Atom API](https://info.arxiv.org/help/api/user-manual.html). The surname search is filtered to Antonio Laface / A. Laface to exclude unrelated authors. All result pages and historical identifiers are supported. Matching arXiv identifiers, DOI, normalized title or an arXiv journal reference moves a manuscript into the published archive. Classification can lag if neither source has the publication record; all arXiv entries remain accessible on the page.
- **Software:** the public GitHub user repositories API, with pagination. Includes forks, archived repositories and this website. Private repositories are never exposed. GitHub's language detection is deliberately omitted because it often mistakes Magma files for MATLAB.
- **MathSciNet:** DOI-based lookup links are supplied where a DOI exists. The site does not scrape MathSciNet: its [terms](https://mathscinet.ams.org/mathscinet/help/mathscinet_terms_of_use.html) restrict automated searching/downloading. zbMATH Open is the automatic bibliography source selected by the site owner.

Each source is refreshed separately with retries and a timeout. Errors never erase a good snapshot or change its synchronization date. Successful sources still update; failures are reported in GitHub Actions. HTML is generated before publication, so visitors do not depend on live third-party requests, browser CORS support or JavaScript for the lists. JavaScript adds filtering and MathJax notation rendering.

## Deployment

The `Update and publish website` GitHub Actions workflow runs on changes to `main`, daily at 06:23 UTC and via **Run workflow**. GitHub schedules may be delayed and can be suspended after 60 days of repository inactivity. This is daily synchronization, not instantaneous streaming.

The workflow preserves the existing Pages source configuration. For branch-based Pages it saves the metadata and explicitly requests a Pages build; for a custom Actions source it deploys a public-site artifact. This matters because a commit made with `GITHUB_TOKEN` does not itself trigger a second Pages build. No manual change to Pages settings is required.

Lecture notes have been removed from the site and navigation; previous versions remain in Git history.
