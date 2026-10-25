# AI Governance Tracker

A dark-themed Streamlit dashboard for monitoring international AI standards,
policy frameworks, safety initiatives, regulation trackers, and legal
intelligence in one place.

## Features

- Five category windows arranged two per row on the overview.
- Separate views for each category, all updates, and the source directory.
- 15-minute cached update discovery, with a manual refresh control.
- Search and publication-date filters.
- Dark Streamlit theme with a responsive layout.
- Local startup and shutdown script with a confirmed stop button in the app.

## Monitored categories

| Category | Sources |
| --- | --- |
| Technical Standards & Certification Bodies | ISO/IEC JTC 1/SC 42; IEEE Standards Association |
| Intergovernmental & Policy Frameworks | OECD.AI; Council of Europe; UNESCO; GPAI |
| Frontier Safety & Technical Consensus | International Network of AI Safety Institutes |
| Dedicated Policy & Regulation Trackers | IAPP; Stanford HAI; TechieRay; AI Governance Directory |
| Legal Intelligence & Law Firm Hubs | White & Case; Covington & Burling; Gibson Dunn; Latham & Watkins |

Each source has an official-site link in the app's source directory.

## Requirements

- Python 3.10 or later
- Streamlit (installed from `requirements.txt`)
- Internet access to retrieve Google News RSS search results

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
chmod +x start.sh
./start.sh
```

Open the localhost URL printed by the script (by default
`http://127.0.0.1:8501`).

```bash
./start.sh status  # Check whether the server is running
./start.sh stop    # Stop the server from a terminal
```

The sidebar also offers a confirmation-gated **Stop application** button when
the app is launched through `start.sh`. It stops the Streamlit server and
disconnects all connected users; it cannot close their browser tabs.

The launcher binds to `127.0.0.1` by default. Only change the bind address
when the app is behind appropriate network access controls:

```bash
AI_GOVERNANCE_HOST=0.0.0.0 AI_GOVERNANCE_PORT=8501 ./start.sh
```

Anyone who can access the dashboard can use its stop button. Do not expose the
app publicly without authentication and access controls.

## Tests

Run the source directory and RSS/Atom feed parser tests with:

```bash
python -m unittest
```

## Update discovery and limitations

The tracker searches Google News RSS with domain-restricted queries for each
monitored source. These results are discovery leads, not a complete or
authoritative register of legal changes. Confirm a publication, its status,
and its effective date with the linked organization. Feeds are checked while
the app is in use; this version does not run scheduled background jobs, retain
an audit history, or send alerts.

## Design references

- [Streamlit app gallery](https://streamlit.io/gallery)
- [Streamlit Community Cloud Explore](https://share.streamlit.io/explore)
- [Streamlit theme customization guide](https://docs.streamlit.io/develop/concepts/configuration/theming)
- [ContainerHub dark Streamlit dashboard](https://github.com/ronnie-1205/ContainerHub)
- [ReturnIQ analytics dashboard](https://github.com/amriiiita07-ui/returniq-fashion-analytics)
