# OpenSearch database for theorem discovery

This directory contains the assets required to spin up an OpenSearch instance
that indexes the example theorems and proofs shipped with the project.  The
setup is designed so that a large language model can query the existing corpus
and fetch focused context windows around interesting proof steps.

## Running OpenSearch

```bash
# From the repository root
cd database
docker build -t metamath-opensearch .
docker run --rm --name metamath-opensearch -p 9200:9200 -e "discovery.type=single-node" -e "plugins.security.disabled=true" -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" -v "$(pwd)/data:/usr/share/opensearch/data:Z" metamath-opensearch
```

Once the container is online you can run the integration tests:

```bash
pip install -r database/requirements.txt
pytest database/tests/test_opensearch_wrapper.py
```

## Dataset layout

All searchable files are expected under `database/data`.  By default the client
uses the `Examples` dataset that mirrors the repository's `examples` directory.
If you drop a larger collection inside `database/data/origin`, the wrapper will
prioritise that directory automatically.

The index state is cached in `.index_state.json` next to the datasets to avoid
re-ingesting all files for every query.  Delete this file or call
`TheoremSearchClient.ensure_index(force=True)` to trigger a rebuild.
